"""Functions and data structures to handle and represent a strategy plan
describing all the actions needed to complete a deployment."""
import enum
import json
from typing import Dict, List, Optional

from attrs import define
from cattrs import structure, unstructure

from treb.core.address import Address


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


def dump_plan(path: str, plan: Plan):
    """Stores the plan in a file.

    Arguments:
        path: path of the file where the plan will be stored.
        plan: plan to store.
    """
    with open(path, "w", encoding="utf-8") as plan_file:
        encoded = unstructure(plan)
        plan_file.write(json.dumps(encoded, indent=4, sort_keys=True))


def load_plan(path: str) -> Plan:
    """Loads a plan from a file.

    Arguments:
        path: path of the file where the plan is stored.
    """
    with open(path, encoding="utf-8") as plan_file:
        decoded = json.loads(plan_file.read())

        return structure(decoded, Plan)
