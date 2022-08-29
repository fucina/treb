"""Helpers used to track class definitions via callbacks."""


class Observable:
    """Allows clients to register callback class inheriting from it."""

    # tracks all the callbacks to run on a new step defintion.
    _callbacks = []

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

    def run_callbacks(self):
        """Executes all the resitered callbacks.

        If any of them raises an exception, it will stop immediately and
        propagate it to the caller.
        """
        for callback in self._callbacks:
            callback(self)
