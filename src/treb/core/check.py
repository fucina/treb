"""Base class for all the step implemations."""
import abc
from typing import TYPE_CHECKING

from attrs import define

from treb.core.spec import Spec

if TYPE_CHECKING:
    from treb.core.context import Context


class FailedCheck(Exception):
    """Raised when a depoyment check failed."""

    def __init__(self, result):
        super().__init__(result)

        self.result = result


@define(frozen=True, kw_only=True)
class Check(Spec):
    """Base class to be used for all checks.

    Arguments:
        name: identify a step within a deploy file.
    """

    @abc.abstractmethod
    def check(self, ctx: "Context"):
        """Performs a check on a new deployment.

        Arguments:
            ctx: the context to use when performing the check.
        """
        raise NotImplementedError
