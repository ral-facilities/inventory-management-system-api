"""Module for providing a subcommand for creating entities in IMS."""

import re

import typer
from rich.prompt import Prompt

from inventory_management_system_api.cli.core import console, display_indexed_system_types, exit_with_error
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()


@app.command()
def system_type():
    """Creates a system type."""

    # Acquire the required services/collections
    database = get_database()
    system_type_service = SystemTypeService(SystemTypeRepo(database))
    system_types_collection = database.system_types

    # Display a table of existing system types for reference
    current_system_types = system_type_service.list()
    console.print("Below is the current list of system types available:")
    display_indexed_system_types(current_system_types)

    # Obtain name of the new system type and ensure it doesn't already exist (case insensitive)
    new_system_type_value = Prompt.ask("Please enter the value of the new system type")
    if system_types_collection.find_one({"value": re.compile(new_system_type_value, re.IGNORECASE)}):
        exit_with_error("[red]A system type with the same value already exists![/]")

    # Obtain description of the new system type
    new_system_type_description = Prompt.ask("Please enter the description of the new system type")

    # Insert the new system type
    system_types_collection.insert_one({"value": new_system_type_value, "description": new_system_type_description})
    console.print("Success! :party_popper:")
