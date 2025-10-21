"""Module for providing a subcommand for deleting entities from IMS."""

import typer
from rich.table import Table

from inventory_management_system_api.cli.core import (
    ask_user_for_index_selection,
    console,
    display_indexed_rules,
    display_indexed_system_types,
    display_rule_explanation,
    display_user_selection,
    display_warning_message,
    exit_with_error,
    get_rule_type,
)
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.rule import RuleOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.rule import RuleRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.rule import RuleService
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


def display_user_selected_rule(selected_rule: RuleOut):
    """Displays a user selected rule."""

    # Output the selected rule
    table = Table("ID", "Type", "src_system_type_id", "dst_system_type_id", "dst_usage_status_id")
    table.add_row(
        selected_rule.id,
        get_rule_type(selected_rule.src_system_type, selected_rule.dst_system_type),
        (
            f"{selected_rule.src_system_type.id} [orange1]({selected_rule.src_system_type.value})[/]"
            if selected_rule.src_system_type
            else "None"
        ),
        (
            f"{selected_rule.dst_system_type.id} [orange1]({selected_rule.dst_system_type.value})[/]"
            if selected_rule.dst_system_type
            else "None"
        ),
        (
            f"{selected_rule.dst_usage_status.id} [orange1]({selected_rule.dst_usage_status.value})[/]"
            if selected_rule.dst_usage_status
            else "None"
        ),
    )
    console.print(table)
    console.print()

    # Output an explanation of the rule
    display_rule_explanation(
        selected_rule.src_system_type, selected_rule.dst_system_type, selected_rule.dst_usage_status
    )


@app.command()
def rule():
    """Deletes a rule."""

    # Acquire the required services/collections
    database = get_database()
    rule_service = RuleService(RuleRepo(database))
    rules_collection = database.rules

    # Display a table of existing rules for reference
    current_rules = rule_service.list(None, None)
    console.print("Below is the current list of rules available:")
    display_indexed_rules(current_rules)

    # Obtain the requested rule to delete
    selected_rule_index, selected_rule = ask_user_for_index_selection(
        "Please enter the index of the rule to delete", current_rules
    )
    selected_rule_id = CustomObjectId(selected_rule.id)

    # Output the selected rule and request confirmation before deleting it
    display_user_selection("You have selected", selected_rule_index, selected_rule.id)
    display_user_selected_rule(selected_rule)
    cont = typer.confirm("Are you sure you want to delete this?")
    console.print()

    if not cont:
        exit_with_error("Cancelled")

    # Now delete the rule
    result = rules_collection.delete_one({"_id": selected_rule_id})
    if result.deleted_count == 0:
        exit_with_error("Failed to delete")
    console.print("Success! :party_popper:")
