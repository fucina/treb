"""Helper functions used acrosse the codebase."""
import contextlib

from rich.console import Console
from rich.markup import escape

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
    CONSOLE.print(f"{escape(message)}")


@contextlib.contextmanager
def print_waiting(message: str):
    """Shows a spinner until the context is exited.

    Arguments:
        message: message to show while is context is still getting executed.
    """
    with CONSOLE.status(message):
        yield
