"""Base class for all the step implemations."""
import abc
from typing import TYPE_CHECKING

from attrs import define

from treb.core.spec import Spec

if TYPE_CHECKING:
    from treb.core.context import Context


@define(frozen=True, kw_only=True)
class Step(Spec):
    """Base class to be used for all steps.

    Arguments:
        name: identify a step within a deploy file.
    """

    @abc.abstractmethod
    def run(self, ctx: "Context"):
        """Runs this step.

        Arguments:
            ctx: the context to use when executing the step.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self, ctx: "Context"):
        """Rolls back this step in case of a failure when running ``Step.run`.

        Arguments:
            ctx: the context to use when rolling back the step.
        """
        raise NotImplementedError
