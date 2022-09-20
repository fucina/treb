"""Base class for all the step implemations."""
import abc
from typing import TYPE_CHECKING, Generic, TypeVar

from attrs import define

from treb.core.spec import Spec

if TYPE_CHECKING:
    from treb.core.context import Context


ResultType = TypeVar("ResultType")
SnapshotType = TypeVar("SnapshotType")


@define(frozen=True, kw_only=True)
class Step(Generic[ResultType, SnapshotType], Spec):
    """Base class to be used for all steps.

    Arguments:
        name: identify a step within a deploy file.
    """

    def snapshot(self, ctx: "Context") -> SnapshotType:
        """Takes a snapshot of the state before running the step. This data is
        useful when rolling back a step to its previous state.

        Arguments:
            ctx: the context to use when executing the step.

        Returns:
            Data captured before running the step.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def run(self, ctx: "Context", snapshot: SnapshotType) -> ResultType:
        """Runs this step.

        Arguments:
            ctx: the context to use when executing the step.
            snapshot: data captured before running the step.

        Returns:
            The outcome of a step, potentially, used as input by other steps.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self, ctx: "Context", snapshot: SnapshotType):
        """Rolls back this step in case of a failure when running ``Step.run`.

        Arguments:
            ctx: the context to use when rolling back the step.
            snapshot: data captured before running the step.
        """
        raise NotImplementedError
