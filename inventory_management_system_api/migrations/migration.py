"""Module for providing a migration script"""

import argparse
import importlib
import logging
from abc import ABC, abstractmethod

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

    database = get_database()
    return migration_class(database)


class CommandList(SubCommand):
    """Command that lists available database migrations"""

    def __init__(self):
        super().__init__(help_message="List all available database migrations")

    def setup(self, parser: argparse.ArgumentParser):
        pass

    def run(self, args: argparse.Namespace):
        # Find a list of all available migration scripts
        with importlib.resources.path("inventory_management_system_api.migrations.scripts", "") as scripts_path:
            files_in_scripts = list(scripts_path.iterdir())
            available_migrations = list(
                filter(lambda name: "__" not in name, [file.name.replace(".py", "") for file in files_in_scripts])
            )
        for migration_name in available_migrations:
            migration = load_migration(migration_name)

            print(f"{migration_name} - {migration.description}")


class CommandForward(SubCommand):
    """Command that performs a forward database migration"""

    def __init__(self):
        super().__init__(help_message="Performs a forward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("migration", help="Name of the migration to perform")

    def run(self, args: argparse.Namespace):
        migration_instance: BaseMigration = load_migration(args.migration)

        # Run migration inside a session to lock writes and revert the changes if it fails
        with mongodb_client.start_session() as session:
            with session.start_transaction():
                logger.info("Performing forward migration...")
                migration_instance.forward(session)
            # Run some things outside the transaction e.g. if needing to drop a collection
            migration_instance.forward_after_transaction(session)
            logger.info("Done!")


class CommandBackward(SubCommand):
    """Command that performs a backward database migration"""

    def __init__(self):
        super().__init__(help_message="Performs a backward database migration")

    def setup(self, parser: argparse.ArgumentParser):
        parser.add_argument("migration", help="Name of the migration to revert")

    def run(self, args: argparse.Namespace):
        migration_instance: BaseMigration = load_migration(args.migration)

        # Run migration inside a session to lock writes and revert the changes if it fails
        with mongodb_client.start_session() as session:
            with session.start_transaction():
                logger.info("Performing backward migration...")
                migration_instance.backward(session)
            # Run some things outside the transaction e.g. if needing to drop a collection
            migration_instance.backward_after_transaction(session)
            logger.info("Done!")


# List of subcommands
commands: dict[str, SubCommand] = {
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
