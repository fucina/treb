"""Base classes and functions used to define and handle artifacts supported by
treb."""
from attrs import define

from treb.core.observable import Observable


@define(frozen=True, kw_only=True)
class ArtifactSpec(Observable):
    """Base class for all artifact supported by treb."""

    name: str

    _callbacks = []

    def __attrs_post_init__(self):
        self.run_callbacks()

    def _run_callbacks(self):
        for callback in self._callbacks:
            callback(self)


@define(frozen=True, kw_only=True)
class Artifact:
    """Base class for all artifact supported by treb."""
