"""
Unit tests for functions inside the `core` module.
"""

from typing import Optional
from unittest.mock import MagicMock, call, patch

import pytest

from inventory_management_system_api.migrations.core import (
    execute_migrations_backward,
    execute_migrations_forward,
    find_available_migrations,
    get_previous_migration,
    load_migration,
    load_migrations_backward_to,
    load_migrations_forward_to,
    set_previous_migration,
)

AVAILABLE_MIGRATIONS = ["migration1", "migration2", "migration3"]


class BaseMigrationDSL:
    """Base class for migration tests."""

    _mock_load_migration: MagicMock
    _mock_find_available_migrations: MagicMock
    _mock_get_previous_migration: MagicMock

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup fixtures."""

        with patch("inventory_management_system_api.migrations.core.load_migration") as mock_load_migration:
            self._mock_load_migration = mock_load_migration
            with patch(
                "inventory_management_system_api.migrations.core.find_available_migrations"
            ) as mock_find_available_migrations:
                self._mock_find_available_migrations = mock_find_available_migrations
                with patch(
                    "inventory_management_system_api.migrations.core.get_previous_migration"
                ) as mock_get_previous_migration:
                    self._mock_get_previous_migration = mock_get_previous_migration
                    yield


class LoadMigrationsForwardToDSL(BaseMigrationDSL):
    """Base class for `load_migrations_forward_to` tests."""

    _available_migrations: list[str]
    _obtained_migrations_forward: dict[str, MagicMock]
    _load_migrations_forward_to_error: pytest.ExceptionInfo

    def mock_load_migrations_forward_to(
        self, available_migrations: list[str], previous_migration: Optional[str]
    ) -> None:
        """
        Mocks appropriate methods to test the `load_migrations_forward_to` method.

        :param available_migrations: List of available migrations.
        :param previous_migration: Previous migration stored in the database.
        """

        self._available_migrations = available_migrations

        self._mock_find_available_migrations.return_value = self._available_migrations
        self._mock_get_previous_migration.return_value = previous_migration

    def call_load_migrations_forward_to(self, name: str) -> None:
        """
        Calls the `load_migrations_forward_to` method.

        :param name: Name of the last forward migration to apply.
        """

        self._obtained_migrations_forward = load_migrations_forward_to(name)

    def call_load_migrations_forward_to_expecting_error(self, name: str, error_type: type[BaseException]) -> None:
        """
        Calls the `load_migrations_forward_to` method while expecting an error to be raised.

        :param name: Name of the last forward migration to apply.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            load_migrations_forward_to(name)
        self._load_migrations_forward_to_error = exc

    def check_load_migrations_forward_to_success(self, expected_migration_names: list[str]) -> None:
        """
        Checks that a prior call to `load_migrations_forward_to` worked as expected.

        :param expected_migration_names: Names of the expected returned migrations to perform.
        """

        self._mock_load_migration.assert_has_calls(
            [call(migration_name) for migration_name in expected_migration_names]
        )
        assert self._obtained_migrations_forward == {
            migration_name: self._mock_load_migration.return_value for migration_name in expected_migration_names
        }

    def check_load_migrations_forward_to_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_load_migrations_forward_to_expecting_error` worked as expected, raising an
        exception with the correct message.

        :param message: Message of the raised exception.
        """

        self._mock_load_migration.assert_not_called()

        assert str(self._load_migrations_forward_to_error.value) == message


class TestLoadMigrationsForwardToDSL(LoadMigrationsForwardToDSL):
    """Tests for loading migrations forward to migrate to a point."""

    def test_load_migrations_forward_to_latest_from_none(self):
        """Tests loading migrations forward to the latest migration from no previous migrations."""

        self.mock_load_migrations_forward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_migrations_forward_to("latest")
        self.check_load_migrations_forward_to_success(AVAILABLE_MIGRATIONS)

    def test_load_migrations_forward_to_latest_from_another(self):
        """Tests loading migrations forward to the latest migration from a previous migration."""

        self.mock_load_migrations_forward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[0]
        )
        self.call_load_migrations_forward_to("latest")
        self.check_load_migrations_forward_to_success(AVAILABLE_MIGRATIONS[1:])

    def test_load_migrations_forward_to_specific_from_none(self):
        """Tests loading migrations forward to a specific migration from no previous migrations."""

        self.mock_load_migrations_forward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_migrations_forward_to(AVAILABLE_MIGRATIONS[1])
        self.check_load_migrations_forward_to_success(AVAILABLE_MIGRATIONS[0:2])

    def test_load_migrations_forward_to_specific_from_another(self):
        """Tests loading migrations forward to a specific migration from a previous migration."""

        self.mock_load_migrations_forward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[1]
        )
        self.call_load_migrations_forward_to(AVAILABLE_MIGRATIONS[2])
        self.check_load_migrations_forward_to_success([AVAILABLE_MIGRATIONS[2]])

    def test_load_migrations_forward_to_from_unknown(self):
        """Tests loading migrations forward to a migration from a previous unknown one."""

        self.mock_load_migrations_forward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration="unknown")
        self.call_load_migrations_forward_to("latest")
        self.check_load_migrations_forward_to_success(AVAILABLE_MIGRATIONS)

    def test_load_migrations_forward_to_invalid(self):
        """Tests loading migrations forward to an invalid migration."""

        self.mock_load_migrations_forward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_migrations_forward_to_expecting_error("invalid", SystemExit)
        self.check_load_migrations_forward_to_failed_with_exception(
            "Migration 'invalid' was not found in the available list of migrations."
        )

    def test_load_migrations_forward_to_older(self):
        """Tests loading migrations forward to an older migration."""

        self.mock_load_migrations_forward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_forward_to_expecting_error(AVAILABLE_MIGRATIONS[1], SystemExit)
        self.check_load_migrations_forward_to_failed_with_exception(
            f"Migration '{AVAILABLE_MIGRATIONS[1]}' is before the previous migration applied "
            f"'{AVAILABLE_MIGRATIONS[-1]}'. So there is nothing to migrate."
        )


class LoadMigrationsBackwardToDSL(BaseMigrationDSL):
    """Base class for `load_migrations_backward_to` tests."""

    _available_migrations: list[str]
    _obtained_migrations_backward: dict[str, MagicMock]
    _load_migrations_backward_to_error: pytest.ExceptionInfo

    def mock_load_migrations_backward_to(
        self, available_migrations: list[str], previous_migration: Optional[str]
    ) -> None:
        """
        Mocks appropriate methods to test the `load_migrations_backward_to` method.

        :param available_migrations: List of available migrations.
        :param previous_migration: Previous migration stored in the database.
        """

        self._available_migrations = available_migrations

        self._mock_find_available_migrations.return_value = self._available_migrations
        self._mock_get_previous_migration.return_value = previous_migration

    def call_load_migrations_backward_to(self, name: str) -> None:
        """
        Calls the `load_migrations_backward_to` method.

        :param name: Name of the last backward migration to apply.
        """

        self._obtained_migrations_backward = load_migrations_backward_to(name)

    def call_load_migrations_backward_to_expecting_error(self, name: str, error_type: type[BaseException]) -> None:
        """
        Calls the `load_migrations_backward_to` method while expecting an error to be raised.

        :param name: Name of the last backward migration to apply.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            load_migrations_backward_to(name)
        self._load_migrations_backward_to_error = exc

    def check_load_migrations_backward_to_success(
        self, expected_migration_names: list[str], expected_final_previous_migration_name: Optional[str]
    ) -> None:
        """
        Checks that a prior call to `load_migrations_backward_to` worked as expected.

        :param expected_migration_names: Names of the expected returned migrations to perform.
        :param expected_final_previous_migration_name: Expected final previous migration name returned.
        """

        self._mock_load_migration.assert_has_calls(
            [call(migration_name) for migration_name in expected_migration_names]
        )
        assert self._obtained_migrations_backward == (
            {migration_name: self._mock_load_migration.return_value for migration_name in expected_migration_names},
            expected_final_previous_migration_name,
        )

    def check_load_migrations_backward_to_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_load_migrations_backward_to_expecting_error` worked as expected, raising an
        exception with the correct message.

        :param message: Message of the raised exception.
        """

        self._mock_load_migration.assert_not_called()

        assert str(self._load_migrations_backward_to_error.value) == message


class TestLoadMigrationsBackwardToDSL(LoadMigrationsBackwardToDSL):
    """Tests for loading migrations backward to migrate to a point."""

    def test_load_migrations_backward_to_oldest_from_latest(self):
        """Tests loading migrations backward to the oldest available migration from the latest one."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_backward_to(AVAILABLE_MIGRATIONS[0])
        self.check_load_migrations_backward_to_success(AVAILABLE_MIGRATIONS[::-1], None)

    def test_load_migrations_backward_to_oldest_from_another(self):
        """Tests loading migrations backward to the oldest available migration from a previous migration."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[1]
        )
        self.call_load_migrations_backward_to(AVAILABLE_MIGRATIONS[0])
        self.check_load_migrations_backward_to_success(AVAILABLE_MIGRATIONS[1::-1], None)

    def test_load_migrations_backward_to_specific_from_latest(self):
        """Tests loading migrations backward to a specific migration from the latest one."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_backward_to(AVAILABLE_MIGRATIONS[1])
        self.check_load_migrations_backward_to_success(AVAILABLE_MIGRATIONS[-1:0:-1], AVAILABLE_MIGRATIONS[0])

    def test_load_migrations_backward_to_specific_from_another(self):
        """Tests loading migrations backward to a specific migration from the latest one."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_backward_to(AVAILABLE_MIGRATIONS[1])
        self.check_load_migrations_backward_to_success(AVAILABLE_MIGRATIONS[-1:0:-1], AVAILABLE_MIGRATIONS[0])

    def test_load_migrations_backward_to_specific_from_none(self):
        """Tests loading migrations backward to a specific migration from no previous migrations."""

        self.mock_load_migrations_backward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_migrations_backward_to_expecting_error(AVAILABLE_MIGRATIONS[1], SystemExit)
        self.check_load_migrations_backward_to_failed_with_exception("No migrations to revert.")

    def test_load_migrations_backward_to_from_unknown(self):
        """Tests loading migrations backward to a migration from a previous unknown one."""

        self.mock_load_migrations_backward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration="unknown")
        self.call_load_migrations_backward_to_expecting_error(AVAILABLE_MIGRATIONS[0], SystemExit)
        self.check_load_migrations_backward_to_failed_with_exception(
            "Previous migration applied 'unknown' not found in current migrations. Have you skipped a version?"
        )

    def test_load_migrations_backward_to_invalid(self):
        """Tests loading migrations backward to an invalid migration."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_backward_to_expecting_error("invalid", SystemExit)
        self.check_load_migrations_backward_to_failed_with_exception(
            "Migration 'invalid' was not found in the available list of migrations."
        )

    def test_load_migrations_backward_to_newer(self):
        """Tests loading migrations backward to an newer migration."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[0]
        )
        self.call_load_migrations_backward_to_expecting_error(AVAILABLE_MIGRATIONS[-1], SystemExit)
        self.check_load_migrations_backward_to_failed_with_exception(
            f"Migration '{AVAILABLE_MIGRATIONS[-1]}' is already reverted or after the previous migration applied "
            f"'{AVAILABLE_MIGRATIONS[0]}'. So there is nothing to migrate."
        )


# The following are some basic tests that did not warrant their own classes
def test_load_migration():
    """Tests that `load_migration` functions without erroring."""

    load_migration("_example_migration")


def test_load_migration_non_existent():
    """Tests that `load_migration` produces an error if the migration named is non-existent."""

    with pytest.raises(ModuleNotFoundError):
        load_migration("_example_migration2")


def test_find_available_migrations():
    """Tests that `find_available_migrations` functions without erroring."""

    assert isinstance(find_available_migrations(), list)


@patch("inventory_management_system_api.migrations.core.database")
def test_get_previous_migration(mock_database):
    """Tests that `get_previous_migration` functions as expected when there is a previous migrations."""

    mock_database.database_migrations.find_one.return_value = {"name": "migration_name"}

    previous_migration = get_previous_migration()

    mock_database.database_migrations.find_one.assert_called_once_with({"_id": "previous_migration"})
    assert previous_migration == "migration_name"


@patch("inventory_management_system_api.migrations.core.database")
def test_set_previous_migration(mock_database):
    """Tests that `set_previous_migration` functions as expected when there is a previous migrations."""

    set_previous_migration("migration_name")

    mock_database.database_migrations.update_one.assert_called_once_with(
        {"_id": "previous_migration"}, {"$set": {"name": "migration_name"}}, upsert=True
    )


@patch("inventory_management_system_api.migrations.core.database")
def test_get_previous_migration_when_none(mock_database):
    """Tests that `get_previous_migration` functions as expected when there are no previous migrations."""

    mock_database.database_migrations.find_one.return_value = None

    previous_migration = get_previous_migration()

    mock_database.database_migrations.find_one.assert_called_with({"_id": "previous_migration"})
    assert previous_migration is None


@patch("inventory_management_system_api.migrations.core.set_previous_migration")
@patch("inventory_management_system_api.migrations.core.start_session_transaction")
def test_execute_migrations_forward(mock_start_session_transaction, mock_set_previous_migration):
    """Tests that `execute_migrations_forward` functions as expected."""

    migrations = {"migration1": MagicMock(), "migration2": MagicMock()}
    expected_session = mock_start_session_transaction.return_value.__enter__.return_value

    execute_migrations_forward(migrations)

    mock_start_session_transaction.assert_called_once_with("forward migration")
    for migration in migrations.values():
        migration.forward.assert_called_once_with(expected_session)
        migration.forward_after_transaction.assert_called_once()

    mock_set_previous_migration.assert_called_once_with(list(migrations.keys())[-1])


@patch("inventory_management_system_api.migrations.core.set_previous_migration")
@patch("inventory_management_system_api.migrations.core.start_session_transaction")
def test_execute_migrations_backward(mock_start_session_transaction, mock_set_previous_migration):
    """Tests that `execute_migrations_backward` functions as expected."""

    migrations = {"migration1": MagicMock(), "migration2": MagicMock()}
    final_previous_migration_name = "final_migration_name"
    expected_session = mock_start_session_transaction.return_value.__enter__.return_value

    execute_migrations_backward(migrations, final_previous_migration_name)

    mock_start_session_transaction.assert_called_once_with("backward migration")
    for migration in migrations.values():
        migration.backward.assert_called_once_with(expected_session)
        migration.backward_after_transaction.assert_called_once()

    mock_set_previous_migration.assert_called_once_with(final_previous_migration_name)
