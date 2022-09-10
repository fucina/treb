"""Functions and data structures to handle and represent a strategy plan
describing all the actions needed to complete a deployment."""
import enum
from typing import TYPE_CHECKING, Dict, List, Optional

from attrs import define

from treb.core.address import Address
from treb.core.spec import Spec

if TYPE_CHECKING:
    from treb.core.strategy import Strategy


@enum.unique
class ActionState(enum.Enum):
    """Represents the state of an action during the strategy execution.

    * `NOT_STARTED`: the action is ready or is waiting for other dependencies to be resolved.
    * `IN_PROGRESS`: the execution has started.
    * `ERRORED`: the execution failed with an error.
    * `ROLLING_BACK`: the roll back is in progress.
    * `DONE`: the execution completed successfully.
    * `FAILED`: the execution failed and the roll-back completed.
    """

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    ERRORED = "ERRORED"
    ROLLING_BACK = "ROLLING_BACK"
    DONE = "DONE"
    FAILED = "FAILED"


@define(frozen=True, kw_only=True)
class Action:
    """Represents an action in a strategy plan.

    Arguments:
        address: the step's address to execute.
        state: the current state of the action execution.
        result: the final result of a successful execution, if available.
        error: the error of a failed action, if available.
    """

    address: Address
    state: ActionState
    result: Optional[Dict[str, str]]
    error: Optional[Dict[str, str]]


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


def resolve_addresses(mapping, value):
    """Visits the dependency addresses in `addresses` and creates a dictionary
    with the same structure but replacing all the addresses with its
    corresponding artifact using the mapping `items`.

    If any of th addresses cannot be resolved, it will return `None`.

    Arguments:
        mapping: contains all the known artifact used for the address resolution.
        value: all the dependency addresses to resolve.

    Returns:
        A copy of the dictionary with the addresses replaced by the artifacts.
        `None` if any of the addresses cannot be resolved.
    """

    if isinstance(value, Address):
        try:
            return mapping[value]

        except KeyError as exc:
            raise UnresolvableAddress(value) from exc

    elif isinstance(value, dict):
        return {
            key: resolve_addresses(mapping, nested_value) for key, nested_value in value.items()
        }

    elif isinstance(value, list):
        return [resolve_addresses(mapping, nested_value) for nested_value in value]

    else:
        return value


def generate_plan(strategy: "Strategy", available_artifacts: List[Address]) -> Plan:
    """Generates a new plan for the deployment strategy.

    Arguments:
        strategy: the deployment strategy defined for the project.
        available_artifacts: all the artifacts built for the current revision.

    Returns:
        The plan with all the steps to deploy the available artifacts.
    """
    steps = strategy.steps()
    artifacts: Dict[Address, Spec] = {
        addr: art for addr, art in strategy.artifacts().items() if addr in available_artifacts
    }
    resources = strategy.resources()

    actions = []

    while steps:
        for step_addr, step in list(steps.items()):
            dep_addresses = strategy.dependencies(step_addr)

            res = resolve_addresses(
                artifacts | resources,
                dep_addresses,
            )

            if res is None:
                continue

            after = [Address.from_string(step_addr.base, address) for address in step.after]
            all_after_resolved = all(
                (address in artifacts or address in resources) for address in after
            )
            if not all_after_resolved:
                continue

            actions.append(
                Action(
                    address=step_addr,
                    state=ActionState.NOT_STARTED,
                    result=None,
                    error=None,
                )
            )

            del steps[step_addr]
            artifacts[step_addr] = step

    return Plan(
        actions=actions,
    )
