"""Base classes and functions used to define and handle artifacts supported by
treb."""
import abc
from typing import TypeVar

from attrs import define

from treb.core.spec import Spec, SpecResult


@define(frozen=True, kw_only=True)
class Artifact(SpecResult):
    """Base class for all artifact supported by treb."""


ArtType = TypeVar("ArtType", bound=Artifact)


@define(frozen=True, kw_only=True)
class ArtifactSpec(Spec):
    """Base class for all artifact supported by treb."""

    @abc.abstractmethod
    def exists(self, revision: str) -> bool:
        """Checks if the artifact for the given revision exists.

        Arguments:
            revsion: revision to check.

        Returns:
            True if an artifact for this revision exists. Otherwise, return false.
        """
        raise NotImplementedError
