"""Module for providing a subcommand that manages database migrations within IMS."""

import datetime
from typing import Annotated, Optional

import typer

from inventory_management_system_api.cli.core import console, exit_with_error
from inventory_management_system_api.migrations.core import (
    MigrationError,
    execute_migrations_backward,
    execute_migrations_forward,
    find_available_migrations,
    find_migration_index,
    get_previous_migration,
    load_migration,
    load_migrations_backward_to,
    load_migrations_forward_to,
    set_previous_migration,
)

app = typer.Typer()


YesConfirmOption = Annotated[bool, typer.Option("--yes", "-y", help="Specify to skip all are you sure prompts.")]


def check_user_sure(message: Optional[str] = None, skip: bool = False) -> bool:
    """
    Asks user if they are sure action should proceed and exits if not.

    :param message: Message to accompany the check.
    :param skip: Whether to skip printing out the message and performing the check.
    :return: Whether user is sure.
    """

    if skip:
        return True

    if message:
        console.print(message)
        console.print()
    return typer.confirm("Are you sure you wish to proceed? ")


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Name of the migration to create.")],
    description: Annotated[str, typer.Argument(help="Description of the migration to create.")],
):
    """Creates a new migration file."""
    current_time = datetime.datetime.now(datetime.UTC)
    file_name = f"{f"{current_time:%Y%m%d%H%M%S}"}_{name}.py"
    with open(f"inventory_management_system_api/migrations/scripts/{file_name}", "w", encoding="utf-8") as file:
        file.write(
            f'''"""
Module providing a migration that {description}.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration


class Migration(BaseMigration):
    """Migration that {description}"""

    description = "{description.capitalize()}"

    def __init__(self, database: Database):
        pass

    def forward(self, session: ClientSession):
        """Applies database changes."""

    def backward(self, session: ClientSession):
        """Reverses database changes."""
'''
        )


@app.command()
def status():
    """Display the status of the current database and available migrations."""

    available_migrations = find_available_migrations()
    previous_migration = get_previous_migration()

    console.print(f"Previous migration: [green]{previous_migration}[/]")
    console.print()

    # Display unknown/new un-applied migrations in red, the rest in green
    reached_current_migration = not previous_migration

    for migration_name in available_migrations:
        migration = load_migration(migration_name)

        console.print(
            f"  [{"red" if reached_current_migration else "green"} bold]{migration_name}[/] - {migration.description}"
        )

        if previous_migration == migration_name:
            reached_current_migration = True
            console.print("[orange1 bold]> Database[/]")


@app.command()
def list():  # pylint:disable=redefined-builtin
    """List all available database migrations."""

    available_migrations = find_available_migrations()
    for migration_name in available_migrations:
        migration = load_migration(migration_name)

        console.print(f"[green bold]{migration_name}[/] - {migration.description}")


@app.command()
def forward(
    name: Annotated[
        str,
        typer.Argument(
            help="Name of the migration to migrate forwards to (inclusive). Use 'latest' to update to whatever the "
            "current latest is."
        ),
    ],
):
    """Performs forward database migration."""

    try:
        migrations = load_migrations_forward_to(name)
    except MigrationError as exc:
        exit_with_error(str(exc))

    console.print("This operation will apply the following migrations:")
    for key in migrations.keys():
        console.print(f"[red bold]{key}[/]")

    console.print()
    if check_user_sure():
        execute_migrations_forward(migrations)
        console.print("Success! :party_popper:")


@app.command()
def backward(
    name: Annotated[
        str,
        typer.Argument(help="Name of the migration to migrate backwards to (inclusive)."),
    ],
):
    """Performs a backward database migration."""

    try:
        migrations, final_previous_migration_name = load_migrations_backward_to(name)
    except MigrationError as exc:
        exit_with_error(str(exc))

    console.print("This operation will revert the following migrations:")
    for key in migrations.keys():
        console.print(f"[red bold]{key}[/]")
    console.print()

    if check_user_sure():
        execute_migrations_backward(migrations, final_previous_migration_name)
        console.print("Success! :party_popper:")


@app.command()
def set(
    name: Annotated[str, typer.Argument(help="Name of the last migration the database currently matches.")],
    yes: YesConfirmOption = False,
):  # pylint:disable=redefined-builtin
    """Sets the last migration of the database to a specific migration."""

    available_migrations = find_available_migrations()

    try:
        end_index = find_migration_index(name, available_migrations)
    except ValueError:
        exit_with_error(f"Migration '{name}' was not found in the available list of migrations")

    if check_user_sure(
        message=f"This operation will forcibly set the latest migration to '{available_migrations[end_index]}'",
        skip=yes,
    ):
        set_previous_migration(available_migrations[end_index])
