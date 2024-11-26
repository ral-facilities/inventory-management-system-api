"""Module for providing migration commands in a script."""

import argparse
import datetime
import logging
import sys
from abc import ABC, abstractmethod

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.migrations.core import (
    execute_backward_migrations,
    execute_forward_migrations,
    find_available_migrations,
    find_migration_index,
    get_last_migration_applied,
    load_backward_migrations_to,
    load_forward_migrations_to,
    load_migration,
    set_last_migration_applied,
)

logger = logging.getLogger()
database = get_database()


def check_user_sure() -> bool:
    """
    Asks user if they are sure action should proceed and exits if not.

    :return: Whether user is sure.
    """

    answer = input("Are you sure you wish to proceed? ")
    return answer in ("y", "yes")


class SubCommand(ABC):
    """Base class for a sub command."""

    def __init__(self, help_message: str):
        self.help_message = help_message

    @abstractmethod
    def setup(self, parser: argparse.ArgumentParser):
        """Setup the parser by adding any parameters here."""

    @abstractmethod
    def run(self, args: argparse.Namespace):
        """Run the command with the given parameters as added by 'setup'."""


class CommandCreate(SubCommand):
    """Command that creates a new migration file."""

    def __init__(self):
        super().__init__(help_message="Creates a new migration file")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name of the migration to create")
        parser.add_argument("description", help="Description of the migration to create")

    def run(self, args: argparse.Namespace):
        current_time = datetime.datetime.now(datetime.UTC)
        file_name = f"{f"{current_time:%Y%m%d%H%M%S}"}_{args.name}.py"
        with open(f"inventory_management_system_api/migrations/scripts/{file_name}", "w", encoding="utf-8") as file:
            file.write(
                f'''"""
Module providing a migration that {args.description}
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

import logging

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration

logger = logging.getLogger()


class Migration(BaseMigration):
    """Migration that {args.description}"""

    description = "{args.description}"

    def __init__(self, database: Database):
        pass

    def forward(self, session: ClientSession):
        """Applies database changes."""

    def backward(self, session: ClientSession):
        """Reverses database changes."""
'''
            )


class CommandList(SubCommand):
    """Command that lists available database migrations."""

    def __init__(self):
        super().__init__(help_message="List all available database migrations")

    def setup(self, parser: argparse.ArgumentParser):
        pass

    def run(self, args: argparse.Namespace):
        available_migrations = find_available_migrations()
        for migration_name in available_migrations:
            migration = load_migration(migration_name)

            print(f"{migration_name} - {migration.description}")


class CommandStatus(SubCommand):
    """Command displays the current database migration status."""

    def __init__(self):
        super().__init__(help_message="Display the status of the current database and available migrations")

    def setup(self, parser: argparse.ArgumentParser):
        pass

    def run(self, args: argparse.Namespace):
        available_migrations = find_available_migrations()
        last_migration_applied = get_last_migration_applied()

        print(f"Last migration applied: {last_migration_applied}")
        print()

        for migration_name in available_migrations:
            migration = load_migration(migration_name)

            if last_migration_applied == migration_name:
                print(f"> {migration_name} - {migration.description}")
            else:
                print(f"  {migration_name} - {migration.description}")


class CommandForward(SubCommand):
    """Command that performs a forward database migration."""

    def __init__(self):
        super().__init__(help_message="Performs a forward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "name",
            help="Name of the migration to migrate forwards to (inclusive). Use 'latest' to "
            "update to whatever the current latest is.",
        )

    def run(self, args: argparse.Namespace):
        migrations = load_forward_migrations_to(args.name)

        print("This operation will apply the following migrations:")
        for name in migrations.keys():
            print(name)

        print()
        if check_user_sure():
            execute_forward_migrations(migrations)
            logger.info("Done!")


class CommandBackward(SubCommand):
    """Command that performs a backward database migration."""

    def __init__(self):
        super().__init__(help_message="Performs a backward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name migration to migrate backwards to (inclusive).")

    def run(self, args: argparse.Namespace):
        migrations = load_backward_migrations_to(args.name)

        print("This operation will apply the following migrations:")
        for name in migrations.keys():
            print(name)
        print()

        if check_user_sure():
            execute_backward_migrations(migrations)
            logger.info("Done!")


class CommandSet(SubCommand):
    """Command that sets the last migration of the database to a specific migration."""

    def __init__(self):
        super().__init__(help_message="Sets the last migration of the database to a specific migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name of the last migration the database currently matches.")

    def run(self, args: argparse.Namespace):
        available_migrations = find_available_migrations()

        try:
            end_index = find_migration_index(args.name, available_migrations)
        except ValueError:
            sys.exit(f"Migration '{args.name}' was not found in the available list of migrations")

        print(f"This operation will forcibly set the latest migration to '{available_migrations[end_index]}'")
        print()

        if check_user_sure():
            set_last_migration_applied(available_migrations[end_index])


# List of subcommands
commands: dict[str, SubCommand] = {
    "create": CommandCreate(),
    "status": CommandStatus(),
    "list": CommandList(),
    "forward": CommandForward(),
    "backward": CommandBackward(),
    "set": CommandSet(),
}


def main():
    """Entrypoint for the ims-migrate script."""

    parser = argparse.ArgumentParser()

    subparser = parser.add_subparsers(dest="command")

    for command_name, command in commands.items():
        command_parser = subparser.add_parser(command_name, help=command.help_message)
        command.setup(command_parser)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    commands[args.command].run(args)
