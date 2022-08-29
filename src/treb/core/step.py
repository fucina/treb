"""Base class for all the step implemations."""
import abc

from attrs import define

from treb.core.observable import Observable
from treb.core.spec import Spec


@define(frozen=True, kw_only=True)
class Step(Spec, Observable):
    """Base class to be used for all steps.

    Arguments:
        name: identify a step within a deploy file.
    """

    def __attrs_post_init__(self):
        self.run_callbacks()

    @abc.abstractmethod
    def run(self, ctx):
        """Runs this step.

        Arguments:
            ctx: the context to use when executing the step.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self, ctx):
        """Rolls back this step in case of a failure when running ``Step.run`.

        Arguments:
            ctx: the context to use when rolling back the step.
        """
        raise NotImplementedError
