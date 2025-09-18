"""Module for providing a subcommand for configuring IMS."""

import sys
from typing import Optional, Tuple, TypeVar

import typer
from rich.prompt import Prompt

from inventory_management_system_api.cli.core import (
    console,
    create_progress_bar,
    display_indexed_system_types,
    display_user_selection,
    display_warning_message,
)
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.setting import SettingService
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()


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

        display_user_selection("The current spares definition is", current_type_indices, current_type_values)


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
    console.print()

    # Display a warning message explaining the consequences of continuing and requesting that the user check no one else
    # is using the system to avoid issues
    display_warning_message(
        [
            "This operation will recalculate the 'number_of_spares' field of all existing catalogue items!",
            "Please ensure no one else is using ims-api to avoid any miscalculations.",
            "Should an error occur at any point during this process no changes will be made.",
        ]
    )

    # Output the new selected spares definition and request confirmation before setting it
    display_user_selection(
        "You have selected", selected_type_indices, [system_type.value for system_type in selected_types]
    )

    cont = typer.confirm("Are you sure you want to select this as your new spares definition?")
    console.print()

    if not cont:
        sys.exit("Cancelled")

    # Now set the spares definition with a progress bar
    console.print("Updating catalogue items...")
    with create_progress_bar() as progress:
        setting_service.set_spares_definition(
            SparesDefinitionIn(system_type_ids=[selected_type.id for selected_type in selected_types]),
            tracker=progress.track,
        )

    console.print("Success! :party_popper:")
