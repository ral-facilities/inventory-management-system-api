"""Module for providing a subcommand for updating entities in IMS."""

import re

import typer
from rich.prompt import IntPrompt, Prompt

from inventory_management_system_api.cli.core import (
    console,
    display_indexed_system_types,
    display_user_selection,
    exit_with_error,
)
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()


@app.command()
def system_type():
    """Updates a system type."""

    # pylint: disable=duplicate-code
    # Acquire the required services/collections
    database = get_database()
    system_type_service = SystemTypeService(SystemTypeRepo(database))
    system_types_collection = database.system_types

    # Display a table of existing system types for reference
    current_system_types = system_type_service.list()
    console.print("Below is the current list of system types available:")
    display_indexed_system_types(current_system_types)
    # pylint: enable=duplicate-code

    # Obtain the requested system type to edit
    selected_type_index = IntPrompt.ask(
        "Please enter the index of the system type to update",
        choices=[str(i) for i in range(1, len(current_system_types) + 1)],
        show_choices=False,
    )
    selected_type = current_system_types[selected_type_index - 1]
    selected_type_id = CustomObjectId(selected_type.id)

    new_type_value = Prompt.ask("Please enter the new value of the selected system type")

    # Ensure a system type with the same value doesn't already exist (but allow user to change the case of the current
    # type being edited)
    if system_types_collection.find_one(
        {"value": re.compile(new_type_value, re.IGNORECASE), "_id": {"$ne": selected_type_id}}
    ):
        exit_with_error("[red]A system type with the same value already exists![/]")

    # Output the selected system type and new value and request confirmation before editing it
    display_user_selection("You are updating", selected_type_index, f"{selected_type.value} -> {new_type_value}")
    cont = typer.confirm("Are you sure you want to apply this change?")
    console.print()

    if not cont:
        exit_with_error("Cancelled")

    # Now update the system type
    system_types_collection.update_one({"_id": selected_type_id}, {"$set": {"value": new_type_value}})
    console.print("Success! :party_popper:")
