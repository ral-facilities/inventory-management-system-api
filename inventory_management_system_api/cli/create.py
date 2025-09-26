"""Module for providing a subcommand for creating entities in IMS."""

import re
from typing import Annotated, Literal

import typer
from rich.prompt import Prompt
from rich.table import Table

from inventory_management_system_api.cli.core import (
    ask_user_for_index_selection,
    console,
    display_indexed_system_types,
    display_indexed_usage_statuses,
    exit_with_error,
)
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.services.system_type import SystemTypeService
from inventory_management_system_api.services.usage_status import UsageStatusService

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

    # Insert the new system type
    system_types_collection.insert_one({"value": new_system_type_value})
    console.print("Success! :party_popper:")


@app.command()
def rule(rule_type: Annotated[Literal["creation", "moving", "deletion"], typer.Argument()]):
    """Creates a rule."""

    # Acquire the required services
    database = get_database()
    system_type_service = SystemTypeService(SystemTypeRepo(database))
    usage_status_service = UsageStatusService(UsageStatusRepo(database))

    # Obtain a list of existing system types and usage statuses
    system_types = system_type_service.list()
    usage_statuses = usage_status_service.list()

    # Selected values
    src_system_type = None
    dst_system_type = None
    dst_usage_status = None

    # Customise the steps based on what kind of rule is being created
    if rule_type == "creation":
        # Output the existing types and obtain a user selected dst_system_type
        console.print("Below is a list of the current system types available:")
        display_indexed_system_types(system_types)
        _, dst_system_type = ask_user_for_index_selection(
            "Please enter the index of the [green]dst_system_type[/]", system_types
        )

        # Output the existing usage statuses and obtain a user selected dst_usage_status
        console.print("Below is a list of the current usage statuses available:")
        display_indexed_usage_statuses(usage_statuses)
        _, dst_usage_status = ask_user_for_index_selection(
            "Please enter the index of the [green]dst_usage_status[/]", usage_statuses
        )
    elif rule_type == "moving":
        # Output the existing types and obtain a user selected src_system_type and dst_system_type
        console.print("Below is a list of the current system types available:")
        display_indexed_system_types(system_types)
        _, src_system_type = ask_user_for_index_selection(
            "Please enter the index of the [green]src_system_type[/]", system_types
        )
        _, dst_system_type = ask_user_for_index_selection(
            "Please enter the index of the [green]dst_system_type[/]", system_types
        )

        # Output the existing usage statuses and obtain a user selected dst_usage_status
        console.print("Below is a list of the current usage statuses available:")
        display_indexed_usage_statuses(usage_statuses)
        _, dst_usage_status = ask_user_for_index_selection(
            "Please enter the index of the [green]dst_usage_status[/]", usage_statuses
        )
    elif rule_type == "deletion":
        # Output the existing types and obtain a user selected src_system_type
        console.print("Below is a list of the current system types available:")
        display_indexed_system_types(system_types)
        _, src_system_type = ask_user_for_index_selection(
            "Please enter the index of the [green]src_system_type[/]", system_types
        )

    # Output the selected rule and request confirmation before proceeding
    console.print(f"You are creating the following the following {rule_type} rule:")
    table = Table("src_system_type", "dst_system_type", "dst_usage_status")
    table.add_row(
        src_system_type.value if src_system_type else "None",
        dst_system_type.value if dst_system_type else "None",
        dst_usage_status.value if dst_usage_status else "None",
    )
    console.print(table)
    console.print()

    # Customise proper explanation based on the kind of rule
    if rule_type == "creation":
        console.print(
            f"This rule will allow new items to be created in systems of type '{dst_system_type.value}' provided they "
            f"have the usage status '{dst_usage_status.value}'"
        )
    elif rule_type == "moving":
        console.print(
            f"This rule will allow items to be moved between systems from type '{src_system_type.value}' to systems of "
            f"type '{dst_system_type.value}' provided they have the usage status '{dst_usage_status.value}'"
        )
    elif rule_type == "deletion":
        console.print(
            f"This rule will allow items to be deleted in systems of type '{src_system_type.value}' regardless of "
            "usage status."
        )
    console.print()

    cont = typer.confirm("Are you sure you want to create this new rule?")
    console.print()

    if not cont:
        exit_with_error("Cancelled")

    # TODO: Actually save the rule
    # TODO: Ensure the rule doesn't already exist before allowing it to be created (can use repo check_exists)
