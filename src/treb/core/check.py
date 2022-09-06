"""Base class for all the step implemations."""
import abc

from attrs import define

from treb.core.spec import Spec


class FailedCheck(Exception):
    """Raised when a depoyment check failed."""


@define(frozen=True, kw_only=True)
class Check(Spec):
    """Base class to be used for all checks.

    Arguments:
        name: identify a step within a deploy file.
    """

    @abc.abstractmethod
    def check(self, ctx):
        """Performs a check on a new deployment.

        Arguments:
            ctx: the context to use when performing the check.
        """
        raise NotImplementedError
