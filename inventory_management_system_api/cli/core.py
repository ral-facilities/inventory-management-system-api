"""Module providing common functions used by the CLI."""

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
