"""
Unit tests for functions inside the `core` module.
"""

from typing import Optional
from unittest.mock import MagicMock, call, patch

import pytest

from inventory_management_system_api.migrations.core import load_forward_migrations_to

AVAILABLE_MIGRATIONS = ["migration1", "migration2", "migration3"]


class MigrationsDSL:
    """Base class for migration tests."""

    _mock_load_migration: MagicMock
    _mock_find_available_migrations: MagicMock
    _mock_get_previous_migration: MagicMock

    _available_migrations: list[str]
    _obtained_forward_migrations: dict[str, MagicMock]
    _load_forward_migrations_to_error: pytest.ExceptionInfo

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

    def mock_load_forward_migrations_to(
        self, available_migrations: list[str], previous_migration: Optional[str]
    ) -> None:
        """
        Mocks appropriate methods to test the `load_forward_migrations_to` method.

        :param available_migrations: List of available migrations.
        :param previous_migration: Previous migration stored in the database.
        """

        self._available_migrations = available_migrations

        self._mock_find_available_migrations.return_value = self._available_migrations
        self._mock_get_previous_migration.return_value = previous_migration

    def call_load_forward_migrations_to(self, name: str) -> None:
        """
        Calls the `load_forward_migrations_to` method.

        :param name: Name of the last forward migration to apply.
        """

        self._obtained_forward_migrations = load_forward_migrations_to(name)

    def call_load_forward_migrations_to_expecting_error(self, name: str, error_type: type[BaseException]) -> None:
        """
        Calls the `load_forward_migrations_to` method while expecting an error to be raised.

        :param name: Name of the last forward migration to apply.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            load_forward_migrations_to(name)
        self._load_forward_migrations_to_error = exc

    def check_load_forward_migrations_to_success(self, expected_migration_names: list[str]) -> None:
        """
        Checks that a prior call to `load_forward_migrations_to` worked as expected.

        :param expected_migration_names: Names of the expected returned migrations to perform.
        """

        self._mock_load_migration.assert_has_calls(
            [call(migration_name) for migration_name in expected_migration_names]
        )
        assert self._obtained_forward_migrations == {
            migration_name: self._mock_load_migration.return_value for migration_name in expected_migration_names
        }

    def check_load_forward_migrations_to_success_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_load_forward_migrations_to_expecting_error` worked as expected, raising an
        exception with the correct message.

        :param message: Message of the raised exception.
        """

        self._mock_load_migration.assert_not_called()

        assert str(self._load_forward_migrations_to_error.value) == message


class TestMigrations(MigrationsDSL):
    """Tests for performing migrations."""

    def test_forward_migrations_to_latest_from_none(self):
        """Tests `forward_migrations_to` when going to the latest migration with no previous migrations."""

        self.mock_load_forward_migrations_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_forward_migrations_to("latest")
        self.check_load_forward_migrations_to_success(AVAILABLE_MIGRATIONS)

    def test_forward_migrations_to_latest_from_another(self):
        """Tests `forward_migrations_to` when going to the latest migration with a previous migration."""

        self.mock_load_forward_migrations_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[0]
        )
        self.call_load_forward_migrations_to("latest")
        self.check_load_forward_migrations_to_success(AVAILABLE_MIGRATIONS[1:])

    def test_forward_migrations_to_specific_from_none(self):
        """Tests `forward_migrations_to` when going to a specific migration with no previous migrations."""

        self.mock_load_forward_migrations_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_forward_migrations_to(AVAILABLE_MIGRATIONS[1])
        self.check_load_forward_migrations_to_success(AVAILABLE_MIGRATIONS[0:2])

    def test_forward_migrations_to_specific_from_another(self):
        """Tests `forward_migrations_to` when going to a specific migration with a previous migration."""

        self.mock_load_forward_migrations_to(
            available_migrations=AVAILABLE_MIGRATIONS, previous_migration=AVAILABLE_MIGRATIONS[1]
        )
        self.call_load_forward_migrations_to(AVAILABLE_MIGRATIONS[2])
        self.check_load_forward_migrations_to_success([AVAILABLE_MIGRATIONS[2]])

    def test_forward_migrations_to_from_unknown(self):
        """Tests `forward_migrations_to` when to a migration from an unknown one."""

        self.mock_load_forward_migrations_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration="unknown")
        self.call_load_forward_migrations_to("latest")
        self.check_load_forward_migrations_to_success(AVAILABLE_MIGRATIONS)

    def test_forward_migrations_to_invalid(self):
        """Tests `forward_migrations_to` when going to an invalid migration."""

        self.mock_load_forward_migrations_to(available_migrations=AVAILABLE_MIGRATIONS, previous_migration=None)
        self.call_load_forward_migrations_to_expecting_error("invalid", SystemExit)
        self.check_load_forward_migrations_to_success_failed_with_exception(
            "Migration 'invalid' was not found in the available list of migrations"
        )
