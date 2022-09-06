"""Rules for planning and executing a treb deploy strategy."""
import copy
import inspect
import os
import types
from collections import defaultdict
from typing import Any, Dict, Generic, Iterable, Mapping, Type, TypeVar, get_args, get_origin

from attrs import define, evolve, fields
from cattrs import structure, unstructure

from treb.core.address import Address
from treb.core.artifact import Artifact, ArtifactSpec
from treb.core.check import Check
from treb.core.context import Context
from treb.core.deploy import Vars, discover_deploy_files
from treb.core.plan import Action, ActionState, Plan
from treb.core.step import Step
from treb.utils import log

ItemType = TypeVar("ItemType", ArtifactSpec, Step, Check)


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
    return istype(type_, (Artifact, ArtifactSpec, Step))


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

        if istype(origin, types.UnionType):
            if any(True for arg in args if is_addressable_type(arg)):
                return make_address(value, base_path)  #

        if istype(origin, dict):
            _, value_type = args

            return {
                nested_key: extract_addresses(value_type, nested_value, base_path)
                for nested_key, nested_value in value.items()
            }

    if is_addressable_type(arg_type):
        return make_address(value, base_path)

    return None


def resolve_addresses(artifacts: Mapping[str, Artifact], dep_addresses):
    """Visits the dependency addresses in `dep_address` and creates a
    dictionary with the same structure but replacing all the addresses with its
    corresponding artifact using the mapping `artifacts`.

    If any of th addresses cannot be resolved, it will return `None`.

    Arguments:
        artifacts: contains all the known artifact used for the address resolution.
        dep_addresses: all the dependency addresses to resolve.

    Returns:
        A copy of the dictionary with the addresses replaced by the artifacts.
        `None` if any of the addresses cannot be resolved.
    """
    dep_artifacts: Dict[str, Artifact | Dict[str, Artifact]] = {}

    for name, addr in dep_addresses.items():
        if isinstance(addr, dict):
            nested_artifacts = {}

            for key, nested_addr in addr.items():
                if nested_addr in artifacts:
                    nested_artifacts[key] = artifacts[nested_addr]
                else:
                    return None

            dep_artifacts[name] = nested_artifacts

        elif addr in artifacts:
            dep_artifacts[name] = artifacts[addr]

        else:
            return None

    return dep_artifacts


class Strategy:
    """Describes the deploy strategy for a project.

    Arguments:
        ctx: the context where to execute the deploy strategy.
    """

    def __init__(self, ctx):
        self._ctx = ctx
        self._steps = {}
        self._artifacts = {}
        self._rev_graph = defaultdict(dict)

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

    def plan(self) -> Plan:
        """Generates a new plan for the deployment strategy."""
        steps = copy.deepcopy(self._steps)
        artifacts = copy.deepcopy(self._artifacts)

        if not artifacts:
            raise ValueError("no artifacts defined")

        actions = []

        while steps:
            for step_node in list(steps.values()):
                dep_addresses = self._rev_graph[step_node.address]

                res = resolve_addresses(
                    {addr: art.item for addr, art in artifacts.items()},
                    dep_addresses,
                )

                if res is None:
                    continue

                actions.append(
                    Action(
                        address=step_node.address,
                        state=ActionState.NOT_STARTED,
                        result=None,
                        error=None,
                    )
                )

                del steps[step_node.address]
                artifacts[step_node.address] = step_node

        return Plan(
            actions=actions,
        )

    def _run_action(self, node: Node[Step] | Node[Check], results):
        dep_artifacts = resolve_addresses(
            {addr: art.item for addr, art in self._artifacts.items()} | results,
            self._rev_graph[node.address],
        )

        item = evolve(node.item, **dep_artifacts)

        if isinstance(item, Step):
            res = item.run(self._ctx)

        elif isinstance(item, Check):
            res = item.check(self._ctx)

        else:
            raise TypeError(f"invalid node type {item.__class__.__name__}")

        return res

    def _rollback_action(self, step_node: Node[Step]):
        log(f"rolling back action {step_node.address}")
        step_node.item.rollback(self._ctx)

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

        for idx, action in enumerate(plan.actions):
            step_node = self._steps[action.address]

            match action.state:
                case ActionState.NOT_STARTED | ActionState.IN_PROGRESS:
                    res = self._run_action(step_node, results)

                    results[step_node.address] = res

                    new_actions = copy.deepcopy(plan.actions)
                    new_actions[idx] = evolve(
                        action, state=ActionState.DONE, result=unstructure(res)
                    )

                    plan = evolve(plan, actions=new_actions)

                    yield plan

                case ActionState.ERRORED | ActionState.ROLLING_BACK:
                    self._rollback_action(step_node)

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
