"""Module for providing a subcommand for creating entities in IMS."""

import re
from typing import Annotated, Optional

import typer
from rich.prompt import Prompt
from rich.table import Table

from inventory_management_system_api.cli.core import (
    RuleType,
    ask_user_for_index_selection,
    console,
    display_indexed_rules,
    display_indexed_system_types,
    display_indexed_usage_statuses,
    display_rule_explanation,
    exit_with_error,
)
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.models.usage_status import UsageStatusOut
from inventory_management_system_api.repositories.rule import RuleRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.services.rule import RuleService
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
        exit_with_error("A system type with the same value already exists!")

    # Obtain description of the new system type. If falsy, description is set to None
    new_system_type_description = Prompt.ask("Please enter the description of the new system type (optional)")
    if not new_system_type_description:
        new_system_type_description = None

    # Insert the new system type
    system_types_collection.insert_one({"value": new_system_type_value, "description": new_system_type_description})
    console.print("Success! :party_popper:")


def get_user_constructed_rule(
    rule_type: RuleType, system_types: list[SystemTypeOut], usage_statuses: list[UsageStatusOut]
) -> tuple[Optional[SystemTypeOut], Optional[SystemTypeOut], Optional[UsageStatusOut]]:
    """Guides the user through selecting a rule and returns the selected rule component parts.

    :param rule_type: Type of rule to construct.
    :param system_types: List of system types available.
    :param usage_statuses: List of usage statuses available:
    :return: Tuple containing (in the following order)
            - src_system_type: The source system type of the rule.
            - dst_system_type: The destination system type of the rule.
            - dst_usage_status: The destination usage status of the rule.
    """

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

        if src_system_type.id == dst_system_type.id:
            exit_with_error("A rule cannot have the same source and destination system types!")

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

    return src_system_type, dst_system_type, dst_usage_status


def display_user_constructed_rule(
    rule_type: RuleType,
    src_system_type: SystemTypeOut,
    dst_system_type: SystemTypeOut,
    dst_usage_status: UsageStatusOut,
):
    """Displays a user constructed rule obtained from `get_user_constructed_rule`."""

    # Output the selected rule
    console.print(f"You are creating the following {rule_type} rule:")
    table = Table("src_system_type_id", "dst_system_type_id", "dst_usage_status_id")
    table.add_row(
        (f"{src_system_type.id} [orange1]({src_system_type.value})[/]" if src_system_type else "None"),
        (f"{dst_system_type.id} [orange1]({dst_system_type.value})[/]" if dst_system_type else "None"),
        (f"{dst_usage_status.id} [orange1]({dst_usage_status.value})[/]" if dst_usage_status else "None"),
    )
    console.print(table)
    console.print()

    # Output an explanation of the rule
    display_rule_explanation(src_system_type, dst_system_type, dst_usage_status)


@app.command()
def rule(rule_type: Annotated[RuleType, typer.Argument()]):
    """Creates a rule."""

    # Acquire the required services
    database = get_database()
    rules_service = RuleService(RuleRepo(database))
    system_type_service = SystemTypeService(SystemTypeRepo(database))
    usage_status_service = UsageStatusService(UsageStatusRepo(database))
    rules_collection = database.rules

    # Obtain a list of all existing rules, system types and usage statuses
    rules = rules_service.list(None, None)
    system_types = system_type_service.list()
    usage_statuses = usage_status_service.list()

    # Display a table of existing rules for reference
    console.print("Below is the current list of the current rules available:")
    display_indexed_rules(rules)

    # Get the user constructed rule
    src_system_type, dst_system_type, dst_usage_status = get_user_constructed_rule(
        rule_type, system_types, usage_statuses
    )

    # Ensure the same rule doesn't already exist
    rule_data = {
        "src_system_type_id": CustomObjectId(src_system_type.id) if src_system_type else None,
        "dst_system_type_id": CustomObjectId(dst_system_type.id) if dst_system_type else None,
        "dst_usage_status_id": CustomObjectId(dst_usage_status.id) if dst_usage_status else None,
    }
    if rules_collection.find_one(rule_data):
        exit_with_error("The selected rule already exists!")

    # Output the user selected rule and request confirmation before adding it
    display_user_constructed_rule(rule_type, src_system_type, dst_system_type, dst_usage_status)
    cont = typer.confirm("Are you sure you want to create this new rule?")
    console.print()

    if not cont:
        exit_with_error("Cancelled")

    # Insert the new rule
    rules_collection.insert_one(rule_data)
    console.print("Success! :party_popper:")
