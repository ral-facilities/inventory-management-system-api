"""Module for providing a subcommand for adding entities to IMS."""

import re
import sys

import typer
from rich.prompt import Prompt

from inventory_management_system_api.cli.core import console, display_indexed_system_types
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()


@app.command()
def system_type():
    """Adds a system type."""

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
        sys.exit("Already exists!")

    # Insert the new system type
    system_types_collection.insert_one({"value": new_system_type_value})
    console.print("Success! :party_popper:")
