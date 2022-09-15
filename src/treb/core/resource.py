"""Base classes and functions used to define and handle resource supported by
treb."""
import abc
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from attrs import define

from treb.core.spec import Spec

if TYPE_CHECKING:
    from treb.core.context import Context


StateType = TypeVar("StateType")


@define(frozen=True, kw_only=True)
class Resource(Generic[StateType], Spec):
    """Base class for all resource specs supported by treb."""

    @abc.abstractmethod
    def state(self, ctx: "Context") -> Optional[StateType]:
        """Fetches the current state of the resource.

        Arguments:
            ctx: the context to use when fetching the resource's state.

        Returns:
            The current resource's state. None if the resource for the current
            revision does not exist.
        """
        raise NotImplementedError
