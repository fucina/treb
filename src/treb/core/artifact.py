"""Base classes and functions used to define and handle artifacts supported by
treb."""
from typing import TypeVar

from attrs import define

from treb.core.spec import Spec


@define(frozen=True, kw_only=True)
class Artifact:
    """Base class for all artifact supported by treb."""


ArtType = TypeVar("ArtType", bound=Artifact)


@define(frozen=True, kw_only=True)
class ArtifactSpec(Spec):
    """Base class for all artifact supported by treb."""
