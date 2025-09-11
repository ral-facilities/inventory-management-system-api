"""Module for providing a subcommand for configuring IMS."""

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.services.setting import SettingService
from inventory_management_system_api.services.system_type import SystemTypeService

app = typer.Typer()
console = Console()


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

    table = Table("Index", "Value")
    for i, system_type in enumerate(system_types, start=1):
        table.add_row(str(i), system_type.value)

    console.print(table)
    console.print()

    # Obtain and output the current spares definition
    # pylint:disable=fixme
    # TODO: Obtain from the setting service directly rather than via the repo
    # pylint:disable=protected-access
    current_spares_definition = setting_service._setting_repository.get(SparesDefinitionOut)

    system_type_ids = [system_type.id for system_type in system_types]
    current_type_values = [system_type.value for system_type in current_spares_definition.system_types]
    current_type_indices = []
    for system_type in current_spares_definition.system_types:
        current_type_indices.append(str(system_type_ids.index(system_type.id) + 1))

    console.print(
        f"The current spares definition is: [green]{",".join(current_type_indices)}[/green]"
        f" [orange1]({",".join(current_type_values)})[/orange1]"
    )

    # Obtain new requested spares definition
    selected_type_indices = Prompt.ask(
        "Please enter a new list of system types separated by commas e.g. [green]1,2,3[/green]"
    )
    selected_type_indices = selected_type_indices.split(",")
    selected_types = [system_types[int(selected_type_index) - 1] for selected_type_index in selected_type_indices]
    selected_type_values = [system_type.value for system_type in selected_types]

    # Display a warning message explaining the consequences of continuing
    console.print()
    console.print(f"[red]{":warning: " * 48}[/red]")
    console.print()
    console.print(
        "[red] This operation will recalculate the 'number_of_spares' field of all existing catalogue items![/red]"
    )
    console.print("[red] Should an error occur at any point during this process no changes will be made.[/red]")
    console.print()
    console.print(f"[red]{":warning: " * 48}[/red]")
    console.print()

    # Output the new selected spares definition and request confirmation before setting it
    console.print("")
    console.print(
        f"You have selected [green]{",".join(selected_type_indices)}[/green]"
        f" [orange1]({",".join(selected_type_values)})[/orange1]"
    )

    cont = typer.confirm("Are you sure you want to select this as your new spares definition?")

    if cont:
        # Now set the spares definition
        setting_service.set_spares_definition(
            SparesDefinitionIn(system_type_ids=[selected_type.id for selected_type in selected_types])
        )

        console.print("Success! :party_popper:")
    else:
        console.print("Cancelled")
