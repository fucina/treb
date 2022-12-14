"""Helper functions used acrosse the codebase."""
import contextlib

from rich.console import Console
from rich.markup import escape
from rich.style import Style

CONSOLE = Console()


def print_exception(message: str):
    """Prints an exception to console including its traceback.

    Arguments:
        message: error message to print.
    """
    CONSOLE.print(f"[bold red]ERROR[/] [red]{escape(message)}[/]")
    CONSOLE.print_exception()


def print_info(message: str):
    """Prints an informational message.

    Arguments:
        message: informational message to print.
    """
    CONSOLE.print(escape(message))


def log(message):
    """Prints a message with contextual information (i.e. timestamp).

    Arguments:
        message: informational message to print.
    """
    CONSOLE.log(escape(message))


def error(message):
    """Prints an error message with contextual information similarly to
    `log()`.

    Arguments:
        message: error message to print.
    """
    CONSOLE.log(
        f":x: {escape(message)}",
        style=Style(
            color="red",
        ),
    )


def rollback(message):
    """Prints a rollbaack message with contextual information similarly to
    `log()`.

    Arguments:
        message: rollback message to print.
    """
    CONSOLE.log(
        f":rewind: {escape(message)}",
        style=Style(
            color="blue",
        ),
    )


def success(message):
    """Prints a success message with contextual information similarly to
    `log()`.

    Arguments:
        message: success message to print.
    """
    CONSOLE.log(
        f":white_check_mark: {escape(message)}",
        style=Style(
            color="green",
        ),
    )


_STATUS = None
_STATUS_MESSAGE = None


@contextlib.contextmanager
def print_waiting(message: str, sep: str = " → "):
    """Shows a spinner until the context is exited.

    This context manager can be nested and it will concatenate the messages using
    the given separator.

    Arguments:
        message: message to show while is context is still getting executed.
    """
    global _STATUS, _STATUS_MESSAGE  # pylint: disable=global-statement

    if _STATUS is None:
        with CONSOLE.status(escape(message)) as status:
            _STATUS = status
            _STATUS_MESSAGE = [message]

            try:
                yield

            finally:
                _STATUS = None
                _STATUS_MESSAGE = None

    else:
        _STATUS_MESSAGE.append(message)
        _STATUS.update(sep.join(_STATUS_MESSAGE))

        try:
            yield

        finally:
            _STATUS.update(escape(sep.join(_STATUS_MESSAGE)))
            _STATUS_MESSAGE.pop()
