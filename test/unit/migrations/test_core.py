"""
Unit tests for functions inside the `core` module.
"""

from typing import Optional
from unittest.mock import MagicMock, call, patch

import pytest

from inventory_management_system_api.migrations.core import load_migrations_backward_to, load_migrations_forward_to

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

    def check_load_migrations_forward_to_success_failed_with_exception(self, message: str) -> None:
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
        self.check_load_migrations_forward_to_success_failed_with_exception(
            "Migration 'invalid' was not found in the available list of migrations."
        )

    def test_load_migrations_forward_to_older(self):
        """Tests loading migrations forward to an older migration."""

        self.mock_load_migrations_forward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_forward_to_expecting_error(AVAILABLE_MIGRATIONS[1], SystemExit)
        self.check_load_migrations_forward_to_success_failed_with_exception(
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

        print(expected_migration_names)
        print(self._obtained_migrations_backward)
        self._mock_load_migration.assert_has_calls(
            [call(migration_name) for migration_name in expected_migration_names]
        )
        assert self._obtained_migrations_backward == (
            {migration_name: self._mock_load_migration.return_value for migration_name in expected_migration_names},
            expected_final_previous_migration_name,
        )

    def check_load_migrations_backward_to_success_failed_with_exception(self, message: str) -> None:
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

    def test_load_migrations_backward_to_from_unknown(self):
        """Tests loading migrations backward to a migration from a previous unknown one."""

        self.mock_load_migrations_backward_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration="unknown")
        self.call_load_migrations_backward_to_expecting_error(AVAILABLE_MIGRATIONS[0], SystemExit)
        self.check_load_migrations_backward_to_success_failed_with_exception(
            "Previous migration applied 'unknown' not found in current migrations. Have you skipped a version?"
        )

    def test_load_migrations_backward_to_invalid(self):
        """Tests loading migrations backward to an invalid migration."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[-1]
        )
        self.call_load_migrations_backward_to_expecting_error("invalid", SystemExit)
        self.check_load_migrations_backward_to_success_failed_with_exception(
            "Migration 'invalid' was not found in the available list of migrations."
        )

    def test_load_migrations_backward_to_newer(self):
        """Tests loading migrations backward to an newer migration."""

        self.mock_load_migrations_backward_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[0]
        )
        self.call_load_migrations_backward_to_expecting_error(AVAILABLE_MIGRATIONS[-1], SystemExit)
        self.check_load_migrations_backward_to_success_failed_with_exception(
            f"Migration '{AVAILABLE_MIGRATIONS[-1]}' is already reverted or after the previous migration applied "
            f"'{AVAILABLE_MIGRATIONS[0]}'. So there is nothing to migrate."
        )
