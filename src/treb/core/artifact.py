"""Base classes and functions used to define and handle artifacts supported by
treb."""
from attrs import define


@define(frozen=True, kw_only=True)
class ArtifactSpec:
    """Base class for all artifact supported by treb."""

    name: str

    _callbacks = []

    def __attrs_post_init__(self):
        self._run_callbacks()

    def _run_callbacks(self):
        for callback in self._callbacks:
            callback(self)

    @classmethod
    def register_callback(cls, callback):
        """Registers a new callback that will be executed when a new artifact
        spec gets created.

        Arguments:
            callback: the callable to register.
        """
        cls._callbacks.append(callback)

    @classmethod
    def unregister_callback(cls, callback):
        """Drops a callback from the list of callbacks.

        Arguments:
            callback: the callable to unregister.
        """
        cls._callbacks.remove(callback)


@define(frozen=True, kw_only=True)
class Artifact:
    """Base class for all artifact supported by treb."""
