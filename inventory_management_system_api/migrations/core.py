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


def get_previous_migration() -> Optional[str]:
    """
    Obtain the name of the last forward migration that gets the database to its current state.

    :return: Either the name of the last forward migration applied to the database or `None` if no migration has ever
             been applied.
    """

    migrations_collection = database.database_migrations
    previous_migration_document = migrations_collection.find_one({"_id": "previous_migration"})

    if not previous_migration_document:
        return None
    return previous_migration_document["name"]


def set_previous_migration(name: Optional[str]) -> None:
    """
    Assigns the name of the previous migration that got the database to its current state inside the database.

    :param name: The name of the previous migration applied to the database or `None` if being set back no migrations
                 having been applied.
    """

    migrations_collection = database.database_migrations
    migrations_collection.update_one({"_id": "previous_migration"}, {"$set": {"name": name}}, upsert=True)


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


def load_migrations_forward_to(name: str) -> dict[str, BaseMigration]:
    """
    Returns a list of migrations forward that need to be applied to get from the last migration applied to the database
    to the given one inclusive.

    :param name: Name of the last migration forward to apply. 'latest' will just use the latest one.
    :returns: List of dicts containing the names and instances of the migrations that need to be applied in the order
              they should be applied.
    """

    available_migrations = find_available_migrations()

    start_index = 0

    previous_migration = get_previous_migration()
    if previous_migration:
        try:
            start_index = find_migration_index(previous_migration, available_migrations) + 1
        except ValueError:
            logger.warning(
                "Previous migration applied '%s' not found in current migrations. Have you skipped a version?",
                previous_migration,
            )

    try:
        end_index = find_migration_index(name, available_migrations)
    except ValueError:
        sys.exit(f"Migration '{name}' was not found in the available list of migrations.")

    if start_index > end_index:
        sys.exit(
            f"Migration '{name}' is before the previous migration applied '{previous_migration}'. So there is nothing "
            "to migrate."
        )

    # Dicts are insertion ordered so will match the list order
    return {name: load_migration(name) for name in available_migrations[start_index : end_index + 1]}


def load_migrations_backward_to(name: str) -> tuple[dict[str, BaseMigration], Optional[str]]:
    """
    Returns a list of migrations backward that need to be applied to get from the last migration applied to the database
    to the given one inclusive.

    :param name: Name of the last migration backward to apply.
    :returns: Tuple containing:
              - List of dicts containing the names and instances of the migrations that need to be applied in the order
                they should be applied.
              - Either the name of the last migration before the one given or `None` if there aren't any.
    """

    available_migrations = find_available_migrations()

    start_index = 0

    previous_migration = get_previous_migration()
    if previous_migration is not None:
        try:
            start_index = find_migration_index(previous_migration, available_migrations)
        except ValueError:
            sys.exit(
                f"Previous migration applied '{previous_migration}' not found in current migrations. "
                "Have you skipped a version?"
            )
    else:
        sys.exit("No migrations to revert.")

    try:
        end_index = find_migration_index(name, available_migrations) - 1
    except ValueError:
        sys.exit(f"Migration '{name}' was not found in the available list of migrations.")

    if start_index <= end_index:
        sys.exit(
            f"Migration '{name}' is already reverted or after the previous migration applied '{previous_migration}'. "
            "So there is nothing to migrate."
        )

    final_previous_migration_name = available_migrations[end_index] if end_index >= 0 else None

    # Array split excludes the end
    if end_index < 0:
        end_index = None

    # Dicts are insertion ordered so will match the list order
    return {
        name: load_migration(name) for name in available_migrations[start_index:end_index:-1]
    }, final_previous_migration_name


def execute_migrations_forward(migrations: dict[str, BaseMigration]) -> None:
    """
    Executes a list of migrations forward in order.

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
            set_previous_migration(list(migrations.keys())[-1])
        # Run some things outside the transaction e.g. if needing to drop a collection
        for name, migration in migrations.items():
            logger.info("Finalising forward migration for '%s'...", name)
            migration.forward_after_transaction(session)


def execute_migrations_backward(migrations: dict[str, BaseMigration], final_previous_migration_name: Optional[str]):
    """
    Executes a list of migrations backward in order.

    All `backward_after_transaction`'s are executed AFTER the all of the `backward`'s are executed. This is so that the
    latter can be done at once in a transaction.

    :param migrations: List of dicts containing the names and instances of the migrations that need to be applied in the
                       order they should be applied.
    :param final_previous_migration_name: Either the name of the previous migration before the ones given or `None` if
                                          there aren't any.
    """
    # Run migration inside a session to lock writes and revert the changes if it fails
    with mongodb_client.start_session() as session:
        with session.start_transaction():
            for name, migration in migrations.items():
                logger.info("Performing backward migration for '%s'...", name)
                migration.backward(session)
            set_previous_migration(final_previous_migration_name)
        # Run some things outside the transaction e.g. if needing to drop a collection
        for name, migration in migrations.items():
            logger.info("Finalising backward migration for '%s'...", name)
            migration.backward_after_transaction(session)
