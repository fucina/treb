"""Functions and data structures to handle and represent a strategy plan
describing all the actions needed to complete a deployment."""
import enum
import operator
from functools import singledispatch
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from attrs import define, evolve, fields
from attrs import has as has_attrs

from treb.core.address import Address
from treb.core.check import Check
from treb.core.spec import Spec
from treb.core.step import Step

if TYPE_CHECKING:
    from treb.core.strategy import Strategy


@enum.unique
class ActionState(enum.Enum):
    """Represents the state of an action during the strategy execution.

    Attributes:

    * `PLANNED`: the action is ready to be executed once the other dependencies are resolved.
    * `IN_PROGRESS`: the execution has started.
    * `DONE`: the execution completed successfully.
    * `FAILED`: the execution failed.
    * `CANCELLED`: the action has been cancelled and won't be exectued anymore.
    """

    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


@enum.unique
class ActionType(enum.Enum):
    """Describes what type of operation will be performed by an action.

    Attributes:

    * `CHECK`: performs a deployment check.
    * `RUN`: performs a step run.
    * `ROLLBACK`: performs a step rollback.
    """

    CHECK = "CHECK"
    RUN = "RUN"
    ROLLBACK = "ROLLBACK"


@define(frozen=True, kw_only=True)
class Action:
    """Represents an action in a strategy plan.

    Arguments:
        address: the step's address to execute.
        state: the current state of the action execution.
        result: the final result of a successful execution, if available.
        error: the error of a failed action, if available.
    """

    type: ActionType
    address: Address
    state: ActionState = ActionState.PLANNED
    snapshot: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


@define(frozen=True, kw_only=True)
class Plan:
    """Describes all the steps to perform in order to execute a deploy
    strategy."""

    actions: List[Action]


class UnresolvableAddress(Exception):
    """Raised when an address cannot be reolved into its actual value."""

    def __init__(self, address) -> None:
        super().__init__(address)

        self.address = address


@singledispatch
def resolve_addresses(value, mapping):  # pylint: disable=unused-argument
    """Visits the dependency addresses in `addresses` and creates a dictionary
    with the same structure but replacing all the addresses with its
    corresponding artifact using the mapping `items`.

    If any of th addresses cannot be resolved, it will return `None`.

    Arguments:
        value: all the dependency addresses to resolve.
        mapping: contains all the known artifact used for the address resolution.

    Returns:
        A copy of the dictionary with the addresses replaced by the artifacts.
        `None` if any of the addresses cannot be resolved.
    """
    if has_attrs(value):
        return resolve_addresses_attrs(value, mapping)

    return value


def resolve_addresses_attrs(value: Address, mapping) -> Any:
    """See `resolve_addresses`."""
    return evolve(
        value,
        **{
            field.name: resolve_addresses(getattr(value, field.name), mapping)
            for field in fields(type(value))
        },
    )


@resolve_addresses.register
def resolve_addresses_address(value: Address, mapping) -> Any:
    """See `resolve_addresses`."""
    try:
        resolved = mapping[value]

        if value.attr is None:
            return resolved

        return operator.attrgetter(value.attr)(resolved)

    except KeyError as exc:
        raise UnresolvableAddress(value) from exc


@resolve_addresses.register
def resolve_addresses_dict(value: dict, mapping) -> dict:
    """See `resolve_addresses`."""
    return {key: resolve_addresses(nested_value, mapping) for key, nested_value in value.items()}


@resolve_addresses.register
def resolve_addresses_list(value: list, mapping) -> list:
    """See `resolve_addresses`."""
    return [resolve_addresses(nested_value, mapping) for nested_value in value]


@resolve_addresses.register
def resolve_addresses_tuple(value: tuple, mapping) -> tuple:
    """See `resolve_addresses`."""
    return tuple(resolve_addresses(nested_value, mapping) for nested_value in value)


@resolve_addresses.register
def resolve_addresses_set(value: set, mapping) -> set:
    """See `resolve_addresses`."""
    return {resolve_addresses(nested_value, mapping) for nested_value in value}


_DUMMY = object()


class _ResultPlaceholder:
    def __getattr__(self, name):
        return _DUMMY


_RESULT_PLACEHOLDER = _ResultPlaceholder()


class UnknownAddresses(Exception):
    """Raised when a strategy contains nodes refering to unknown addresses.

    Arguments:
        addresses: unknown addresses used in the strategy.
    """

    def __init__(self, addresses: List[Address]) -> None:
        super().__init__(addresses)

        self.addresses = addresses

    def __str__(self):
        addresses_str = ", ".join(str(addr) for addr in self.addresses)
        return f"cannot find addresses: {addresses_str}"


def _get_action_type(spec: Spec) -> ActionType:
    if isinstance(spec, Step):
        return ActionType.RUN

    if isinstance(spec, Check):
        return ActionType.CHECK

    raise TypeError(f"spec of type {type(spec).__name__} cannot create an action")


def generate_plan(  # pylint: disable=too-many-locals
    strategy: "Strategy",
    available_artifacts: List[Address],
) -> Plan:
    """Generates a new plan for the deployment strategy.

    Arguments:
        strategy: the deployment strategy defined for the project.
        available_artifacts: all the artifacts built for the current revision.

    Returns:
        The plan with all the steps to deploy the available artifacts.
    """
    steps = strategy.steps()

    artifacts: Dict[Address, Any] = {addr: _RESULT_PLACEHOLDER for addr in available_artifacts}
    resources = strategy.resources()

    actions = []
    results: Dict[Address, Any] = artifacts | resources

    prev_steps = None
    unresolvable_addresses: List[Address] = []
    skip_addresses: Set[Address] = set(
        addr for addr in strategy.artifacts() if addr not in available_artifacts
    )

    while steps:
        if list(sorted(steps.items())) == prev_steps:
            raise UnknownAddresses(addresses=unresolvable_addresses)

        prev_steps = list(sorted(steps.items()))

        unresolvable_addresses = []

        for step_addr, step in list(sorted(steps.items())):
            if step_addr in skip_addresses:
                continue

            dep_addresses = strategy.dependencies(step_addr)

            try:
                resolve_addresses(dep_addresses, results)

            except UnresolvableAddress as exc:
                unresolvable_addresses.append(exc.address)
                if exc.address in skip_addresses:
                    skip_addresses.add(step_addr)
                    del steps[step_addr]

                continue

            after = [Address.from_string(step_addr.base, address) for address in step.after]
            all_after_resolved = all(address in results for address in after)
            if not all_after_resolved:
                continue

            actions.append(
                Action(
                    type=_get_action_type(step),
                    address=step_addr,
                    state=ActionState.PLANNED,
                    result=None,
                    error=None,
                )
            )

            del steps[step_addr]
            results[step_addr] = _RESULT_PLACEHOLDER

    return Plan(
        actions=actions,
    )
