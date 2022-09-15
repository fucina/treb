"""Base classes and functions used to define and handle artifacts supported by
treb."""
import abc
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from attrs import define

from treb.core.spec import Spec

if TYPE_CHECKING:
    from treb.core.context import Context


ArtifactType = TypeVar("ArtifactType")


@define(frozen=True, kw_only=True)
class Artifact(Generic[ArtifactType], Spec):
    """Base class for all artifact supported by treb."""

    def exists(self, ctx: "Context") -> bool:
        """Checks if the artifact for the given revision exists.

        Its default implementation uses the method `resolve()` to check
        if the artifact exists, but if there's a better way to check if
        an artifact exists, this method should be overriden.

        Arguments:
            ctx: the context to use when checking if the artifact exists.

        Returns:
            True if an artifact for this revision exists. Otherwise, return false.
        """
        return self.resolve(ctx) is not None

    @abc.abstractmethod
    def resolve(self, ctx: "Context") -> Optional[ArtifactType]:
        """Fetches all the data related to this artifact.

        Argument:
            ctx: the context to use when checking if the artifact exists.

        Returns:
            The object representing the artifact. None if the artifact for the
            current revision does not exist.
        """
        raise NotImplementedError
