"""Base class for all the step implemations."""
from abc import ABC, abstractmethod

from attrs import define


@define(frozen=True, kw_only=True)
class Step(ABC):
    """Base class to be used for all steps.

    Arguments:
        name: identify a step within a deploy file.
    """

    name: str

    # tracks all the callbacks to run on a new step defintion.
    _callbacks = []

    def __attrs_post_init__(self):
        self._run_callbacks()

    def _run_callbacks(self):
        for callback in self._callbacks:
            callback(self)

    @classmethod
    def register_callback(cls, callback):
        """Registers a new callback that will be executed when a new step gets
        created.

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

    @abstractmethod
    def run(self, ctx):
        """Runs this step.

        Arguments:
            ctx: the context to use when executing the step.
        """
        raise NotImplementedError

    @abstractmethod
    def rollback(self, ctx):
        """Rolls back this step in case of a failure when running ``Step.run`.

        Arguments:
            ctx: the context to use when rolling back the step.
        """
        raise NotImplementedError
