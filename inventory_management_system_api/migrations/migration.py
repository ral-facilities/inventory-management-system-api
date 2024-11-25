"""Module for providing a migration script"""

import argparse
import datetime
import importlib
import logging
import sys
from abc import ABC, abstractmethod
from typing import Optional

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database, mongodb_client

logger = logging.getLogger()


class BaseMigration(ABC):
    """Base class for a migration with a forward and backward step"""

    @abstractmethod
    def __init__(self, database: Database):
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of this migration"""
        return ""

    @abstractmethod
    def forward(self, session: ClientSession):
        """Method for executing the migration"""

    def forward_after_transaction(self, session: ClientSession):
        """Method called after the forward function is called to do anything that can't be done inside a transaction
        (ONLY USE IF NECESSARY e.g. dropping a collection)"""

    @abstractmethod
    def backward(self, session: ClientSession):
        """Method for reversing the migration"""

    def backward_after_transaction(self, session: ClientSession):
        """Method called after the backward function is called to do anything that can't be done inside a transaction
        (ONLY USE IF NECESSARY e.g. dropping a collection)"""


class SubCommand(ABC):
    """Base class for a sub command"""

    def __init__(self, help_message: str):
        self.help_message = help_message

    @abstractmethod
    def setup(self, parser: argparse.ArgumentParser):
        """Setup the parser by adding any parameters here"""

    @abstractmethod
    def run(self, args: argparse.Namespace):
        """Run the command with the given parameters as added by 'setup'"""


def load_migration(name: str) -> BaseMigration:
    """Loads a migration script from the scripts module"""

    migration_module = importlib.import_module(f"inventory_management_system_api.migrations.scripts.{name}")
    migration_class = getattr(migration_module, "Migration", None)

    return migration_class(get_database())


def find_available_migrations() -> list[str]:
    """Find and returns a sorted list of names of the available migrations"""

    with importlib.resources.path("inventory_management_system_api.migrations.scripts", "") as scripts_path:
        files_in_scripts = list(scripts_path.iterdir())
        available_migrations = list(
            filter(lambda name: not name.startswith("_"), [file.name.replace(".py", "") for file in files_in_scripts])
        )
    return sorted(available_migrations)


def load_available_migrations() -> list[BaseMigration]:
    """Find and returns a sorted list of the available migrations"""

    return [load_migration(name) for name in find_available_migrations()]


def find_last_migration_applied() -> Optional[str]:
    """Returns the name of the last migration applied to the database (or None if no migration has ever been applied)"""

    database = get_database()
    migrations_collection = database.schema_migrations
    last_migration_document = migrations_collection.find_one({"_id": "last_migration"})

    if not last_migration_document:
        return None
    return last_migration_document["name"]


def set_last_migration_applied(name: str) -> None:
    """Assigns the value of the last migration applied"""

    database = get_database()
    migrations_collection = database.schema_migrations
    migrations_collection.update_one({"_id": "last_migration"}, {"$set": {"name": name}}, upsert=True)


def load_forward_migrations_to(name: str) -> dict[str, BaseMigration]:
    """
    Returns a list of forward migrations that need to be applied to get from the existing database version to the
    given one

    :param name: Name of the last forward migration to apply. 'latest' is used to indicate just use the latest one.
    :returns: List of dicts containing the names and instances of the migrations that need to be applied in the order
              they should be applied.
    """

    available_migrations = find_available_migrations()

    start_index = 0

    last_migration = find_last_migration_applied()
    if last_migration:
        try:
            start_index = available_migrations.index(last_migration)
        except ValueError:
            logger.warning(
                "Last migration applied '%s' not found in current migrations. Have you skipped a version?",
                last_migration,
            )

    end_index = len(available_migrations) - 1
    if name != "latest":
        try:
            end_index = available_migrations.index(name)
        except ValueError:
            sys.exit(f"Migration '{name}' was not found in the available list of migrations")

    if start_index >= end_index:
        sys.exit(
            f"Migration '{name}' is either the same or before the last migration applied '{last_migration}. "
            "So there is nothing to migrate.'"
        )

    return {name: load_migration(name) for name in available_migrations[start_index : end_index + 1]}


def load_backward_migrations_to(name: str) -> dict[str, BaseMigration]:
    """Returns a list of backward migrations that need to be applied to get from the existing database version to the
    given one

    :param name: Name of the last backward migration to apply.
    :returns: List of dicts containing the names and instances of the migrations that need to be applied in the order
              they should be applied.
    """

    available_migrations = find_available_migrations()

    start_index = 0

    last_migration = find_last_migration_applied()
    if last_migration:
        try:
            start_index = available_migrations.index(last_migration)
        except ValueError:
            sys.exit(
                f"Last migration '{last_migration}' applied not found in current migrations. "
                "Have you skipped a version?"
            )
    else:
        sys.exit("No migrations to revert.")

    try:
        end_index = available_migrations.index(name)
    except ValueError:
        sys.exit(f"Migration '{name}' was not found in the available list of migrations")

    if start_index <= end_index:
        sys.exit(
            f"Migration '{name}' is either the same or after the last migration applied '{last_migration}. "
            "So there is nothing to migrate.'"
        )

    return {name: load_migration(name) for name in available_migrations[start_index : end_index - 1 : -1]}


class CommandGenerate(SubCommand):
    """Command that generates a new migration file"""

    def __init__(self):
        super().__init__(help_message="Generates a new migration file")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name of the migration to add")
        parser.add_argument("description", help="Description of the migration to add")

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
from typing import Collection

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration

logger = logging.getLogger()


class Migration(BaseMigration):
    """Migration that {args.description}"""

    description = "{args.description}"

    def __init__(self, database: Database):
        pass

    def forward(self, session: ClientSession):
        """Applies database changes."""

        logger.info("{args.name} forward migration")

    def backward(self, session: ClientSession):
        """Reverses database changes."""
        
        logger.info("{args.name} backward migration")
'''
            )


class CommandList(SubCommand):
    """Command that lists available database migrations"""

    def __init__(self):
        super().__init__(help_message="List all available database migrations")

    def setup(self, parser: argparse.ArgumentParser):
        pass

    def run(self, args: argparse.Namespace):
        available_migrations = find_available_migrations()
        for migration_name in available_migrations:
            migration = load_migration(migration_name)

            print(f"{migration_name} - {migration.description}")


class CommandForward(SubCommand):
    """Command that performs a forward database migration"""

    def __init__(self):
        super().__init__(help_message="Performs a forward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name of the migration to migrate forwards to (inclusive)")

    def run(self, args: argparse.Namespace):
        forward_migrations = load_forward_migrations_to(args.name)

        print("This operation will apply the following migrations:")
        for name in forward_migrations.keys():
            print(name)

        print()
        answer = input("Are you sure you wish to proceed? ")
        if answer in ("y", "yes"):
            # Run migration inside a session to lock writes and revert the changes if it fails
            with mongodb_client.start_session() as session:
                with session.start_transaction():
                    for name, migration in forward_migrations.items():
                        logger.info("Performing forward migration for '%s'...", name)
                        migration.forward(session)
                    set_last_migration_applied(list(forward_migrations.keys())[-1])
                # Run some things outside the transaction e.g. if needing to drop a collection
                for name, migration in forward_migrations.items():
                    logger.info("Finalising forward migration for '%s'...", name)
                    migration.forward_after_transaction(session)

                logger.info("Done!")


class CommandBackward(SubCommand):
    """Command that performs a backward database migration"""

    def __init__(self):
        super().__init__(help_message="Performs a backward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("name", help="Name migration to migrate backwards to (inclusive).")

    def run(self, args: argparse.Namespace):
        backward_migrations = load_backward_migrations_to(args.name)

        print("This operation will apply the following migrations:")
        for name in backward_migrations.keys():
            print(name)

        print()
        answer = input("Are you sure you wish to proceed? ")
        if answer in ("y", "yes"):
            # Run migration inside a session to lock writes and revert the changes if it fails
            with mongodb_client.start_session() as session:
                with session.start_transaction():
                    for name, migration in backward_migrations.items():
                        logger.info("Performing backward migration for '%s'...", name)
                        migration.backward(session)
                    set_last_migration_applied(list(backward_migrations.keys())[-1])
                # Run some things outside the transaction e.g. if needing to drop a collection
                for name, migration in backward_migrations.items():
                    logger.info("Finalising backward migration for '%s'...", name)
                    migration.backward_after_transaction(session)

                logger.info("Done!")


# List of subcommands
commands: dict[str, SubCommand] = {
    "generate": CommandGenerate(),
    "list": CommandList(),
    "forward": CommandForward(),
    "backward": CommandBackward(),
}


def main():
    """Entrypoint for the ims-migrate script"""

    parser = argparse.ArgumentParser()

    subparser = parser.add_subparsers(dest="command")

    for command_name, command in commands.items():
        command_parser = subparser.add_parser(command_name, help=command.help_message)
        command.setup(command_parser)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    commands[args.command].run(args)
