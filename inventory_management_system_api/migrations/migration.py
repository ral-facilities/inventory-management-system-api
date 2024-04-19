import argparse
import importlib
from abc import ABC, abstractmethod

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database, mongodb_client


class BaseMigration(ABC):
    @abstractmethod
    def __init__(self, database: Database):
        pass

    @abstractmethod
    def forward(self, session: ClientSession):
        pass

    @abstractmethod
    def backward(self, session: ClientSession):
        pass


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("migration")
    parser.add_argument("--backward", action="store_false")
    args = parser.parse_args()

    migration_module = importlib.import_module(f"inventory_management_system_api.migrations.scripts.{args.migration}")
    # path = Path(args.migration)
    # spec = importlib.util.spec_from_file_location(path.stem, path)
    # print(path.stem, path)
    # migration_module = importlib.util.module_from_spec(spec)
    # spec.loader.exec_module(migration_module)

    database = get_database()
    migration_class = getattr(migration_module, "Migration", None)
    migration_instance: BaseMigration = migration_class(database)

    with mongodb_client.start_session() as session:
        with session.start_transaction():
            if args.backward:
                migration_instance.forward(session)
            else:
                migration_instance.backward(session)
