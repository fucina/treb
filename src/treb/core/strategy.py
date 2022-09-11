"""Rules for planning and executing a treb deploy strategy."""
import copy
import inspect
import os
import types
import typing
from collections import defaultdict
from typing import Any, Dict, Generic, Iterable, Type, TypeVar, get_args, get_origin

from attrs import define, evolve, fields
from cattrs import structure, unstructure

from treb.core.address import Address
from treb.core.artifact import ArtifactSpec
from treb.core.check import Check, FailedCheck
from treb.core.context import Context
from treb.core.deploy import Vars, discover_deploy_files
from treb.core.plan import ActionState, Plan, resolve_addresses
from treb.core.resource import ResourceSpec
from treb.core.spec import Spec
from treb.core.step import Step
from treb.utils import error, print_exception, print_waiting, rollback, success

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
        f"value of type {type(value).__name__} cannot be assign to tyoe {arg_type.__name__}"
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
        return copy.deepcopy(self._rev_graph[address])

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

    def _run_action(self, node: Node[Step] | Node[Check], results):
        dep_artifacts = resolve_addresses(
            {addr: art.item for addr, art in self._artifacts.items()}
            | {addr: resource.item for addr, resource in self._resources.items()}
            | results,
            self._rev_graph[node.address],
        )

        item = evolve(node.item, **dep_artifacts)

        res = None

        if isinstance(item, Step):
            with print_waiting(f"step {node.address}"):
                res = item.run(self._ctx)
                success(f"step completed address={node.address}")

        elif isinstance(item, Check):
            try:
                with print_waiting(f"check {node.address}"):
                    res = item.check(self._ctx)

            except FailedCheck:
                error(f"check failed address={node.address}")
                raise

            else:
                success(f"check passed address={node.address}")

        else:
            raise TypeError(f"invalid node type {item.__class__.__name__}")

        return res

    def _rollback_action(self, node: Node[Step], results):
        with print_waiting(f"rollback {node.address}"):
            if isinstance(node.item, Step):
                dep_artifacts = resolve_addresses(
                    {addr: art.item for addr, art in self._artifacts.items()} | results,
                    self._rev_graph[node.address],
                )

                item = evolve(node.item, **dep_artifacts)
                item.rollback(self._ctx)

            rollback(
                f"rolled back address={node.address}",
            )

    def execute(self, plan: Plan) -> Iterable[Plan]:
        """Executes a plan performing each action sequentially and yielding a
        new version of the plan for each state change.

        The yielded plan is a copy of the original plan.

        Arguments:
            plan: the plan to execute.

        Yields:
            A new state of the after each action state change.
        """
        results: Dict[str, Any] = {}

        idx = 0

        while True:
            if idx >= len(plan.actions):
                break

            action = plan.actions[idx]
            step_node = self._steps[action.address]

            match action.state:
                case ActionState.NOT_STARTED | ActionState.IN_PROGRESS:
                    new_actions = copy.deepcopy(plan.actions)

                    start_rollback = False

                    try:
                        res = self._run_action(step_node, results)

                        results[step_node.address] = res

                        new_action = evolve(action, state=ActionState.DONE, result=unstructure(res))

                    except FailedCheck:
                        new_action = evolve(action, state=ActionState.FAILED, result=None)
                        start_rollback = True

                    except Exception:  # pylint: disable=broad-except
                        new_action = evolve(action, state=ActionState.ERRORED, result=None)
                        start_rollback = True
                        print_exception(
                            f"exception raise when running the action {step_node.address}"
                        )

                    new_actions[idx] = new_action
                    plan = evolve(plan, actions=new_actions)

                    yield plan

                    if start_rollback:
                        done_actions = copy.deepcopy(plan.actions)[: idx + 1]
                        rollback_actions = []
                        for rollback_action in reversed(done_actions):
                            rollback_action = evolve(
                                rollback_action,
                                state=ActionState.ROLLING_BACK,
                            )
                            rollback_actions.append(rollback_action)

                        plan = evolve(plan, actions=done_actions + rollback_actions)

                        yield plan

                case ActionState.ERRORED | ActionState.ROLLING_BACK:
                    self._rollback_action(step_node, results)

                    new_actions = copy.deepcopy(plan.actions)
                    new_actions[idx] = evolve(action, state=ActionState.FAILED)

                    plan = evolve(plan, actions=new_actions)

                    yield plan

                case ActionState.DONE:
                    signature = inspect.signature(step_node.item.run)
                    results[step_node.address] = structure(
                        action.result, signature.return_annotation
                    )

                case ActionState.FAILED:
                    pass

                case _:
                    raise ValueError("invalid plan")

            idx += 1


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
        base = os.path.normpath(os.path.dirname(deploy_file.path))

        specs = {key: _register(base, value) for key, value in ctx.specs.items()}

        exec_globals: Dict[str, Any] = {"var": Vars(ctx.config.vars), **specs}

        exec(  # nosec[B102:exec_used] pylint: disable=exec-used
            deploy_file.code,
            exec_globals,
        )

    return strategy
