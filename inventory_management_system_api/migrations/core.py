"""Module for providing the core functionality for database migrations."""

import importlib
import logging
import sys
from typing import Optional

from inventory_management_system_api.core.database import get_database, mongodb_client
from inventory_management_system_api.migrations.base import BaseMigration

database = get_database()
logger = logging.getLogger()


def load_migration(name: str) -> BaseMigration:
    """
    Loads a migration script from the scripts module.

    :param name: Name of the migration script to load.
    """

    migration_module = importlib.import_module(f"inventory_management_system_api.migrations.scripts.{name}")
    migration_class = getattr(migration_module, "Migration", None)

    return migration_class(database)


def find_available_migrations() -> list[str]:
    """
    Find and returns a sorted list of names of the available migrations.

    :returns: Sorted list of the names of the available migrations found (in chronological order).
    """

    with importlib.resources.path("inventory_management_system_api.migrations.scripts", "") as scripts_path:
        files_in_scripts = list(scripts_path.iterdir())
        available_migrations = list(
            filter(lambda name: not name.startswith("_"), [file.name.replace(".py", "") for file in files_in_scripts])
        )
    return sorted(available_migrations)


def get_last_migration_applied() -> Optional[str]:
    """
    Obtain the name of the last migration applied to the database.

    :return: Either the name of the last migration applied to the database or `None` if no migration has ever been
             applied.
    """

    migrations_collection = database.database_migrations
    last_migration_document = migrations_collection.find_one({"_id": "last_migration"})

    if not last_migration_document:
        return None
    return last_migration_document["name"]


def set_last_migration_applied(name: str) -> None:
    """
    Assigns the name of the of the last migration applied to the database.

    :param name: The name of the last migration applied to the database.
    """

    migrations_collection = database.database_migrations
    migrations_collection.update_one({"_id": "last_migration"}, {"$set": {"name": name}}, upsert=True)


def find_migration_index(name: str, migration_names: list[str]) -> int:
    """
    Returns the index of a specific migration name in a list of sorted migration names.

    :param name: Name of the migration to look for. A value of 'latest' indicates the last available one should be used
                 instead.
    :param migration_names: List of migration names.
    :return: Index of the found migration in the `migration_names` list.
    :raises: ValueError if the `name` does not appear in `migration_names`.
    """

    if name == "latest":
        return len(migration_names) - 1
    return migration_names.index(name)


def load_forward_migrations_to(name: str) -> dict[str, BaseMigration]:
    """
    Returns a list of forward migrations that need to be applied to get from the last migration applied to the database
    to the given one.

    :param name: Name of the last forward migration to apply. 'latest' will just use the latest one.
    :returns: List of dicts containing the names and instances of the migrations that need to be applied in the order
              they should be applied.
    """

    available_migrations = find_available_migrations()

    start_index = 0

    last_migration = get_last_migration_applied()
    if last_migration:
        try:
            start_index = find_migration_index(last_migration, available_migrations)
        except ValueError:
            logger.warning(
                "Last migration applied '%s' not found in current migrations. Have you skipped a version?",
                last_migration,
            )

    try:
        end_index = find_migration_index(name, available_migrations)
    except ValueError:
        sys.exit(f"Migration '{name}' was not found in the available list of migrations")

    if start_index >= end_index:
        sys.exit(
            f"Migration '{name}' is either the same or before the last migration applied '{last_migration}. "
            "So there is nothing to migrate.'"
        )

    # Dicts are insertion ordered so will match the list order
    return {name: load_migration(name) for name in available_migrations[start_index : end_index + 1]}


def load_backward_migrations_to(name: str) -> dict[str, BaseMigration]:
    """
    Returns a list of forward migrations that need to be applied to get from the last migration applied to the database
    to the given one.

    :param name: Name of the last backward migration to apply.
    :returns: List of dicts containing the names and instances of the migrations that need to be applied in the order
              they should be applied.
    """

    available_migrations = find_available_migrations()

    start_index = 0

    last_migration = get_last_migration_applied()
    if last_migration:
        try:
            start_index = find_migration_index(last_migration, available_migrations)
        except ValueError:
            sys.exit(
                f"Last migration '{last_migration}' applied not found in current migrations. "
                "Have you skipped a version?"
            )
    else:
        sys.exit("No migrations to revert.")

    try:
        end_index = find_migration_index(name, available_migrations)
    except ValueError:
        sys.exit(f"Migration '{name}' was not found in the available list of migrations")

    if start_index <= end_index:
        sys.exit(
            f"Migration '{name}' is either the same or after the last migration applied '{last_migration}. "
            "So there is nothing to migrate.'"
        )

    # Dicts are insertion ordered so will match the list order
    return {name: load_migration(name) for name in available_migrations[start_index : end_index - 1 : -1]}


def execute_forward_migrations(migrations: dict[str, BaseMigration]) -> None:
    """
    Executes a list of forward migrations in order.

    All `forward_after_transaction`'s are executed AFTER the all of the `forward`'s are executed. This is so that the
    latter can be done at once in a transaction.

    :param migrations: List of dicts containing the names and instances of the migrations that need to be applied in the
                       order they should be applied.
    """

    # Run migration inside a session to lock writes and revert the changes if it fails
    with mongodb_client.start_session() as session:
        with session.start_transaction():
            for name, migration in migrations.items():
                logger.info("Performing forward migration for '%s'...", name)
                migration.forward(session)
            set_last_migration_applied(list(migrations.keys())[-1])
        # Run some things outside the transaction e.g. if needing to drop a collection
        for name, migration in migrations.items():
            logger.info("Finalising forward migration for '%s'...", name)
            migration.forward_after_transaction(session)


def execute_backward_migrations(migrations: dict[str, BaseMigration]):
    """
    Executes a list of backward migrations in order.

    All `backward_after_transaction`'s are executed AFTER the all of the `backward`'s are executed. This is so that the
    latter can be done at once in a transaction.

    :param migrations: List of dicts containing the names and instances of the migrations that need to be applied in the
                       order they should be applied.
    """
    # Run migration inside a session to lock writes and revert the changes if it fails
    with mongodb_client.start_session() as session:
        with session.start_transaction():
            for name, migration in migrations.items():
                logger.info("Performing backward migration for '%s'...", name)
                migration.backward(session)
            set_last_migration_applied(list(migrations.keys())[-1])
        # Run some things outside the transaction e.g. if needing to drop a collection
        for name, migration in migrations.items():
            logger.info("Finalising backward migration for '%s'...", name)
            migration.backward_after_transaction(session)
