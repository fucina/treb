"""Rules for planning and executing a treb deploy strategy."""
import copy
import os
import types
import typing
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Generic, Type, TypeVar, get_args, get_origin

from attrs import define, fields

from treb.core.address import Address
from treb.core.artifact import ArtifactSpec
from treb.core.check import Check
from treb.core.context import Context
from treb.core.deploy import Vars, discover_deploy_files
from treb.core.resource import ResourceSpec
from treb.core.spec import Spec
from treb.core.step import Step

ItemType = TypeVar("ItemType", ArtifactSpec, Step, Check, ResourceSpec)


@define(frozen=True, kw_only=True)
class Node(Generic[ItemType]):
    """Represents a node in the strategy graph.

    Arguments:
        address: the node address.
        item: the actual node that can be wither a step or an artifact.
    """

    address: Address
    item: ItemType


def is_addressable_type(type_) -> bool:
    """Checks if the type can be used as node of the deployment graph.

    Arguments:
        type_: node's type.

    Returns:
        True if it can be used to instantiate a node. Otherwise false.
    """
    return istype(type_, Spec)


def make_address(value: object, base_path: str) -> Address:
    """Transforms the given object into an address if possible.

    Arguments:
        value: the object to parse into an address.
        base_path: path to use when building from a relative address.

    Returns:
        The address described vy `value`.

    Raises:
        TypeError: if the object cannot be transformed into an Address.
    """
    if isinstance(value, str):
        return Address.from_string(base_path, value)

    if isinstance(value, Address):
        return value

    raise TypeError("reference to steps or artifacts must be a valid address")


def istype(cls, type_):
    """Returns whether 'cls' is derived from another class or is the same
    class.

    This behaves exactly as the built-in function `issubclass` but it
    returns `False` if `cls` is not a supported class. This is useful
    when checking types that are not actuall classes such as `Union`,
    `Optional`.
    """
    try:
        return issubclass(cls, type_)

    except TypeError:
        return False


ArgType = TypeVar("ArgType")


def extract_addresses(arg_type: Type[ArgType], value: Any, base_path: str):
    """Inspects the type and value of a field to find all its dependency
    addresses.

    Arguemnts:
        arg_type: the expected field type.
        value: the value assigned to the field.
        base_path: the path of the deploy file where the field's step was defined.

    Returns:
        The addresses extracted from the value in the same for as they were provided.
    """
    origin = get_origin(arg_type)
    if origin is not None:
        args = get_args(arg_type)

        if origin is typing.Union or issubclass(origin, types.UnionType):
            for arg in args:
                if is_addressable_type(arg):
                    try:
                        return make_address(value, base_path)

                    except TypeError:
                        pass

                else:
                    try:
                        return extract_addresses(arg, value, base_path)
                    except TypeError:
                        pass

        if istype(origin, dict):
            _, value_type = args

            return {
                nested_key: extract_addresses(value_type, nested_value, base_path)
                for nested_key, nested_value in value.items()
            }

        if istype(origin, list):
            return [extract_addresses(args[0], nested_value, base_path) for nested_value in value]

    if is_addressable_type(arg_type):
        return make_address(value, base_path)

    if isinstance(value, arg_type):
        return value

    raise TypeError(
        f"value of type {type(value).__name__} cannot be assign to type {arg_type.__name__}"
    )


class Strategy:
    """Describes the deploy strategy for a project.

    Arguments:
        ctx: the context where to execute the deploy strategy.
    """

    def __init__(self, ctx):
        self._ctx = ctx
        self._steps = {}
        self._artifacts = {}
        self._resources = {}
        self._rev_graph = defaultdict(dict)

    def ctx(self) -> Context:
        """Gets the context where to execute the deploy strategy."""
        return self._ctx

    def specs(self) -> Dict[Address, Spec]:
        """Returns a mapping of addresses to all specs defined in the
        deployment strategy."""
        return self.steps() | self.artifacts() | self.resources()

    def steps(self) -> Dict[Address, Step]:
        """Returns a mapping of addresses to all steps defined in the
        deployment strategy."""
        return {addr: node.item for addr, node in self._steps.items()}

    def artifacts(self) -> Dict[Address, ArtifactSpec]:
        """Returns a mapping of addresses to all artifacts defined in the
        deployment strategy."""
        return {addr: node.item for addr, node in self._artifacts.items()}

    def resources(self) -> Dict[Address, ResourceSpec]:
        """Returns a mapping of addresses to all resources defined in the
        deployment strategy."""
        return {addr: node.item for addr, node in self._resources.items()}

    def dependencies(self, address):
        """Returns all the dependencies of the given address."""
        deps = copy.deepcopy(self._rev_graph[address])

        try:
            deps.pop("name")
        except KeyError:
            pass

        return deps

    def register_artifact(self, path: str, artifact: ArtifactSpec):
        """Adds an artifact to the deploy strategy.

        Arguments:
            path: the base path to the artifact definition.
            artifact: the artifact spec to add.
        """
        node = Node[ArtifactSpec](
            address=Address(base=path, name=artifact.name),
            item=artifact,
        )
        self._artifacts[node.address] = node

    def register_resource(self, path: str, resource: ResourceSpec):
        """Adds a resource to the deploy strategy.

        Arguments:
            path: the base path to the resource definition.
            resource: the resource spec to add.
        """
        node = Node[ResourceSpec](
            address=Address(base=path, name=resource.name),
            item=resource,
        )
        self._resources[node.address] = node

    def register_step(self, path: str, step: Step):
        """Adds a step to the deploy strategy.

        Arguments:
            path: the base path to the step definition.
            artifact: the artifact spec to add.
        """
        address = Address(base=path, name=step.name)

        node = Node[Step](
            address=address,
            item=step,
        )

        self._steps[address] = node

        for field in fields(type(step)):
            value = getattr(step, field.name)

            addresses = extract_addresses(field.type, value, path)
            if addresses is not None:
                self._rev_graph[node.address][field.name] = addresses

    def register_check(self, path: str, check: Check):
        """Adds a check to the deploy strategy.

        Arguments:
            path: the base path to the check definition.
            check: the check spec to add.
        """
        address = Address(base=path, name=check.name)

        node = Node[Check](
            address=address,
            item=check,
        )

        self._steps[address] = node

        for field in fields(type(check)):
            value = getattr(check, field.name)

            addresses = extract_addresses(field.type, value, path)
            if addresses is not None:
                self._rev_graph[node.address][field.name] = addresses


def prepare_strategy(ctx: Context) -> Strategy:
    """Generates the strategy from the defintions found in the deploy files.

    Arguments:
        ctx: the context used to generate the strategy.

    Returns:
        The strategy for the given repo.
    """
    strategy = Strategy(ctx)

    def _register(base, cls):
        def _wrapper(*args, **kwargs):
            item = cls(*args, **kwargs)

            if issubclass(cls, Step):
                strategy.register_step(base, item)

            elif issubclass(cls, ArtifactSpec):
                strategy.register_artifact(base, item)

            elif issubclass(cls, Check):
                strategy.register_check(base, item)

            elif issubclass(cls, ResourceSpec):
                strategy.register_resource(base, item)

            else:
                raise TypeError(f"cannot register item of type {cls.__name__}")

            return item

        return _wrapper

    for deploy_file in discover_deploy_files(
        root=ctx.config.project.repo_path, deploy_filename=ctx.config.deploy_filename
    ):
        base_path = Path(os.path.normpath(os.path.dirname(deploy_file.path))).relative_to(
            ctx.config.project.repo_path
        )

        base = "" if base_path == Path() else str(base_path)
        specs = {key: _register(str(base), value) for key, value in ctx.specs.items()}

        exec_globals: Dict[str, Any] = {"var": Vars(ctx.config.vars), **specs}

        exec(  # nosec[B102:exec_used] pylint: disable=exec-used
            deploy_file.code,
            exec_globals,
        )

    return strategy
