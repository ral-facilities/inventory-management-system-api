"""Module for providing migration commands in a script."""

import argparse
import datetime
import logging
import sys
from abc import ABC, abstractmethod
from typing import Optional

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.migrations.core import (
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

logger = logging.getLogger()
database = get_database()


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
        print(message)
        print()
    answer = input("Are you sure you wish to proceed? ")
    return answer in ("y", "yes")


def add_skip_args(parser: argparse.ArgumentParser):
    """Adds common arguments for skipping user prompts."""

    parser.add_argument("--yes", "-y", help="Specify to skip all are you sure prompts", action="store_true")


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
Module providing a migration that {args.description}.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration


class Migration(BaseMigration):
    """Migration that {args.description}"""

    description = "{args.description.capitalize()}"

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
        previous_migration = get_previous_migration()

        print(f"Previous migration: {previous_migration}")
        print()

        for migration_name in available_migrations:
            migration = load_migration(migration_name)

            print(f"  {migration_name} - {migration.description}")

            if previous_migration == migration_name:
                print("> Database")


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
        migrations = load_migrations_forward_to(args.name)

        print("This operation will apply the following migrations:")
        for name in migrations.keys():
            print(name)

        print()
        if check_user_sure():
            execute_migrations_forward(migrations)
            logger.info("Done!")


class CommandBackward(SubCommand):
    """Command that performs a backward database migration."""

    def __init__(self):
        super().__init__(help_message="Performs a backward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name migration to migrate backwards to (inclusive).")

    def run(self, args: argparse.Namespace):
        migrations, final_previous_migration_name = load_migrations_backward_to(args.name)

        print("This operation will revert the following migrations:")
        for name in migrations.keys():
            print(name)
        print()

        if check_user_sure():
            execute_migrations_backward(migrations, final_previous_migration_name)
            logger.info("Done!")


class CommandSet(SubCommand):
    """Command that sets the last migration of the database to a specific migration."""

    def __init__(self):
        super().__init__(help_message="Sets the last migration of the database to a specific migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name of the last migration the database currently matches.")

        add_skip_args(parser)

    def run(self, args: argparse.Namespace):
        available_migrations = find_available_migrations()

        try:
            end_index = find_migration_index(args.name, available_migrations)
        except ValueError:
            sys.exit(f"Migration '{args.name}' was not found in the available list of migrations")

        if check_user_sure(
            message=f"This operation will forcibly set the latest migration to '{available_migrations[end_index]}'",
            skip=args.yes,
        ):
            set_previous_migration(available_migrations[end_index])


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
