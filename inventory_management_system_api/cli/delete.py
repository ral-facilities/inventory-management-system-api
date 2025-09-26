"""Module for providing a subcommand for deleting entities from IMS."""

import typer

from inventory_management_system_api.cli.core import (
    ask_user_for_index_selection,
    console,
    display_indexed_system_types,
    display_user_selection,
    display_warning_message,
    exit_with_error,
)
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.setting import SettingService
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()


@app.command()
def system_type():
    """Deletes a system type."""

    # Acquire the required services/collections
    database = get_database()
    system_type_service = SystemTypeService(SystemTypeRepo(database))
    setting_service = SettingService(
        SettingRepo(database), SystemTypeRepo(database), CatalogueItemRepo(database), ItemRepo(database)
    )
    system_types_collection = database.system_types
    systems_collection = database.systems
    rules_collection = database.rules

    # Display a table of existing system types for reference
    current_system_types = system_type_service.list()
    console.print("Below is the current list of system types available:")
    display_indexed_system_types(current_system_types)

    # Obtain the requested system type to delete
    selected_type_index, selected_type = ask_user_for_index_selection(
        "Please enter the index of the system type to delete", current_system_types
    )
    selected_type_id = CustomObjectId(selected_type.id)

    # Obtain the current spares definition
    # pylint:disable=fixme
    # TODO: Obtain from the setting service directly rather than via the repo once implemented in #549
    # pylint:disable=protected-access
    current_spares_definition = setting_service._setting_repository.get(SparesDefinitionOut)

    # Ensure the system type is not used in any system, rule or the spares definition
    if (
        systems_collection.find_one({"type_id": selected_type_id})
        or rules_collection.find_one({"src_system_type_id": selected_type_id})
        or rules_collection.find_one({"dst_system_type_id": selected_type_id})
        or any(system_type.id == selected_type.id for system_type in current_spares_definition.system_types)
    ):
        exit_with_error(
            "[red]This system type is currently in use in a system, rule or the spares definition, please remove all "
            "usage first before deleting.[/]"
        )

    # Display a warning message requesting that the user check no one else is using the system to avoid issues
    display_warning_message(
        "Please ensure no one else is using ims-api to avoid deleting a system type that is currently not in use but "
        "will be at the time of deletion."
    )

    # Output the selected system type and request confirmation before deleting it
    display_user_selection("You have selected", selected_type_index, selected_type.value)
    cont = typer.confirm("Are you sure you want to delete this?")
    console.print()

    if not cont:
        exit_with_error("Cancelled")

    # Now delete the system type
    result = system_types_collection.delete_one({"_id": selected_type_id})
    if result.deleted_count == 0:
        exit_with_error("Failed to delete")
    console.print("Success! :party_popper:")
