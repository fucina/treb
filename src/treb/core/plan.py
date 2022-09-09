"""Functions and data structures to handle and represent a strategy plan
describing all the actions needed to complete a deployment."""
import enum
from typing import TYPE_CHECKING, Dict, List, Optional

from attrs import define

from treb.core.address import Address
from treb.core.artifact import Artifact
from treb.core.resource import Resource
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


def resolve_addresses(items, addresses):
    """Visits the dependency addresses in `dep_address` and creates a
    dictionary with the same structure but replacing all the addresses with its
    corresponding artifact using the mapping `artifacts`.

    If any of th addresses cannot be resolved, it will return `None`.

    Arguments:
        items: contains all the known artifact used for the address resolution.
        addresses: all the dependency addresses to resolve.

    Returns:
        A copy of the dictionary with the addresses replaced by the artifacts.
        `None` if any of the addresses cannot be resolved.
    """
    dependencies: Dict[str, Artifact | Resource | Dict[str, Artifact | Resource]] = {}

    for name, addr in addresses.items():
        if isinstance(addr, dict):
            nested_artifacts = {}

            for key, nested_addr in addr.items():
                if nested_addr in items:
                    nested_artifacts[key] = items[nested_addr]
                else:
                    return None

            dependencies[name] = nested_artifacts

        elif addr in items:
            dependencies[name] = items[addr]

        else:
            return None

    return dependencies


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
