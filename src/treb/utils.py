from rich.console import Console
from rich.markup import escape

CONSOLE = Console()


def print_exception(message: str):
    CONSOLE.print(f"[bold red]error[/] [red]{escape(message)}[/]")
    CONSOLE.print_exception()
