"""Module for providing a migration script"""

import argparse
import importlib
from abc import ABC, abstractmethod

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database, mongodb_client


class BaseMigration(ABC):
    """Base class for a migration with a forward and backward step"""

    @abstractmethod
    def __init__(self, database: Database):
        pass

    @abstractmethod
    def forward(self, session: ClientSession):
        """Method for executing the migration"""

    @abstractmethod
    def backward(self, session: ClientSession):
        """Method for reversing the migration"""

    def backward_after_transaction(self, session: ClientSession):
        """Method called after the backward function is called to do anything that can't be done inside a transaction
        (ONLY USE IF NECESSARY e.g. dropping a collection)"""


def main():
    """Entrypoint for the ims-migrate script"""
    parser = argparse.ArgumentParser()

    parser.add_argument("migration")
    parser.add_argument("--backward", action="store_true")
    args = parser.parse_args()

    migration_module = importlib.import_module(f"inventory_management_system_api.migrations.scripts.{args.migration}")
    migration_class = getattr(migration_module, "Migration", None)

    database = get_database()
    migration_instance: BaseMigration = migration_class(database)

    # Run migration inside a session to lock writes and revert the changes if it fails
    with mongodb_client.start_session() as session:
        with session.start_transaction():
            if not args.backward:
                migration_instance.forward(session)
            else:
                migration_instance.backward(session)
        if args.backward:
            migration_instance.backward_after_transaction(session)
