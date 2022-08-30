"""Functions and data structures to handle and represent a strategy plan
describing all the actions needed to complete a deployment."""
import enum
from typing import Dict, List, Optional

from attrs import define

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
