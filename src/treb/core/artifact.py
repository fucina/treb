"""Base classes and functions used to define and handle artifacts supported by
treb."""
from typing import Iterator, Type

from attrs import define

from treb.core.context import Context


@define(frozen=True, kw_only=True)
class ArtifactSpec:
    """Base class for all artifact supported by treb."""

    name: str

    callbacks = []

    def __attrs_post_init__(self):
        self._run_callbacks()

    def _run_callbacks(self):
        for cb in self.callbacks:
            cb(self)

    @classmethod
    def register_callback(cls, callback):
        cls.callbacks.append(callback)

    @classmethod
    def unregister_callback(cls, callback):
        cls.callbacks.remove(callback)


@define(frozen=True, kw_only=True)
class Artifact:
    """Base class for all artifact supported by treb."""
