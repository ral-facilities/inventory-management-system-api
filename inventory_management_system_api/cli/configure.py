"""Module for providing a subcommand for configuring IMS."""

from typing import Optional, Tuple, TypeVar

import typer
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.table import Table

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.setting import SettingService
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()
console = Console()


def display_indexed_system_types(system_types: list[SystemTypeOut]):
    """Displays a list of system types in an indexed table."""

    table = Table("Index", "Value")
    for i, system_type in enumerate(system_types, start=1):
        table.add_row(str(i), system_type.value)

    console.print(table)
    console.print()


def display_indices_selection(message: str, indices: list[int], values: list[str]):
    """Displays a list of indices and their corresponding values after a message."""

    console.print(f"{message}: [green]{",".join(str(index) for index in indices)}[/] [orange1]({",".join(values)})")
    console.print()


def display_current_spares_definition(
    definition: Optional[SparesDefinitionOut], system_type_ids: list[StringObjectIdField]
):
    """Displays the current spares definition."""

    if definition is None:
        console.print("There is no spares definition currently")
    else:
        current_type_values = [system_type.value for system_type in definition.system_types]
        current_type_indices = []
        for system_type in definition.system_types:
            current_type_indices.append(system_type_ids.index(system_type.id) + 1)

        display_indices_selection("The current spares definition is", current_type_indices, current_type_values)


T = TypeVar("T")


def ask_user_for_indices_selection(message: str, options: list[T]) -> Tuple[list[int], list[T]]:
    """Asks the user for a selection of indices and returns the resulting selected indices and the options they
    represent."""

    selected_indices = [int(index) for index in Prompt.ask(message).split(",")]
    selected_options = [options[selected_index - 1] for selected_index in selected_indices]

    return selected_indices, selected_options


@app.command()
def spares_definition():
    """Configures the spares definition used by IMS."""

    # Acquire the required services
    database = get_database()
    system_type_service = SystemTypeService(SystemTypeRepo(database))
    setting_service = SettingService(
        SettingRepo(database), SystemTypeRepo(database), CatalogueItemRepo(database), ItemRepo(database)
    )

    # Output a table of existing system types
    system_types = system_type_service.list()

    console.print("Below is a list of the current system types available:")
    display_indexed_system_types(system_types)

    # Obtain and output the current spares definition
    # pylint:disable=fixme
    # TODO: Obtain from the setting service directly rather than via the repo once implemented in #549
    # pylint:disable=protected-access
    current_spares_definition = setting_service._setting_repository.get(SparesDefinitionOut)

    system_type_ids = [system_type.id for system_type in system_types]
    display_current_spares_definition(current_spares_definition, system_type_ids)

    # Obtain new requested spares definition
    selected_type_indices, selected_types = ask_user_for_indices_selection(
        "Please enter a new list of system types separated by commas e.g. [green]1,2,3[/]", system_types
    )

    # Display a warning message explaining the consequences of continuing
    console.print()
    console.print(f"[red bold]{":warning: " * 48}[/]")
    console.print()
    console.print(
        "[red bold] This operation will recalculate the 'number_of_spares' field of all existing catalogue items![/]"
    )
    console.print("[red bold] Please ensure no one else is using ims-api to avoid any miscalculations.[/]")
    console.print("[red bold] Should an error occur at any point during this process no changes will be made.[/]")
    console.print()
    console.print(f"[red bold]{":warning: " * 48}[/]")
    console.print()

    # Output the new selected spares definition and request confirmation before setting it
    display_indices_selection(
        "You have selected", selected_type_indices, [system_type.value for system_type in selected_types]
    )

    cont = typer.confirm("Are you sure you want to select this as your new spares definition?")
    console.print()

    if cont:
        # Now set the spares definition with a progress bar
        console.print("Updating catalogue items...")
        progress_bar = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
        )
        with progress_bar as p:
            setting_service.set_spares_definition(
                SparesDefinitionIn(system_type_ids=[selected_type.id for selected_type in selected_types]),
                tracker=p.track,
            )

        console.print("Success! :party_popper:")
    else:
        console.print("Cancelled")
