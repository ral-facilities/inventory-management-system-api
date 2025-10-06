"""Module providing common functions used by the CLI."""

import textwrap

import typer
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from inventory_management_system_api.models.system_type import SystemTypeOut

console = Console()


def create_progress_bar() -> Progress:
    """Creates and returns a Rich progress bar with a custom layout to use in the CLI."""
    return Progress(
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )


def display_indexed_system_types(system_types: list[SystemTypeOut]):
    """Displays a list of system types in an indexed table."""

    table = Table("Index", "ID", "Value")
    for i, system_type in enumerate(system_types, start=1):
        table.add_row(str(i), system_type.id, system_type.value)

    console.print(table)
    console.print()


def display_warning_message(message: str | list[str]):
    """Displays a warning message. When multiple messages given, ensures they are put on new lines."""

    console.print(f"[red bold]{":warning: " * 48}[/]")
    console.print()
    messages = message if isinstance(message, list) else [message]
    for current_message in messages:
        for line in textwrap.wrap(current_message, 94):
            console.print(f"[red bold] {line} [/]")
    console.print()
    console.print(f"[red bold]{":warning: " * 48}[/]")
    console.print()


def display_user_selection(message: str, selection: str | int | list[str | int], value: str | list[str]):
    """Display a users selection and values (in brackets)."""

    selections = selection if isinstance(selection, list) else [selection]
    selections = [str(selec) for selec in selections]
    values = value if isinstance(value, list) else [value]

    console.print(f"{message}: [green]{",".join(selections)}[/] [orange1]({",".join(values)})[/]")
    console.print()


def exit_with_error(message: str):
    """Displays an error message in red and then exits."""

    console.print(f"[red bold]{message}[/]")
    raise typer.Exit(1)
