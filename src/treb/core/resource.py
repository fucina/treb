"""Base classes and functions used to define and handle resource supported by
treb."""
from attrs import define

from treb.core.spec import Spec


@define(frozen=True, kw_only=True)
class ResourceSpec(Spec):
    """Base class for all resource specs supported by treb."""


@define(frozen=True, kw_only=True)
class Resource:
    """Base class for all resources supported by treb."""
