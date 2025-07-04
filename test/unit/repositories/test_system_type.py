"""
Unit tests for the `SystemTypeRepo` repository.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import SYSTEM_TYPES_OUT_DATA
from test.unit.repositories.conftest import RepositoryTestHelpers
from unittest.mock import MagicMock, Mock

import pytest

from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.repositories.system_type import SystemTypeRepo


class SystemTypeRepoDSL:
    """Base class for `SystemTypeRepo` unit tests."""

    mock_database: Mock
    system_type_repository: SystemTypeRepo
    system_types_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures."""

        self.mock_database = database_mock
        self.system_type_repository = SystemTypeRepo(database_mock)
        self.system_types_collection = database_mock.system_types


class ListDSL(SystemTypeRepoDSL):
    """Base class for `list` tests."""

    _expected_systems_types_out: list[SystemTypeOut]
    _obtained_system_types_out: list[SystemTypeOut]

    def mock_list(self, system_types_out_data: list[dict]):
        """
        Mocks database methods appropriately to test the `list` repo method.

        :param system_types_out_data: List of dictionaries containing the system type data as would be required for a
                                      `SystemTypeOut` database model.
        """

        self._expected_systems_types_out = [
            SystemTypeOut(**system_type_out_data) for system_type_out_data in system_types_out_data
        ]
        RepositoryTestHelpers.mock_find(self.system_types_collection, system_types_out_data)

    def call_list(self):
        """Calls the `SystemTypeRepo` `list` method."""

        self._obtained_system_types_out = self.system_type_repository.list(session=self.mock_session)

    def check_list_success(self):
        """Checks that a prior call to `call_list` worked as expected."""

        self.system_types_collection.find.assert_called_once_with(session=self.mock_session)
        assert self._obtained_system_types_out == self._expected_systems_types_out


class TestList(ListDSL):
    """Tests for listing system types."""

    def test_list(self):
        """Test listing all system types."""

        self.mock_list(SYSTEM_TYPES_OUT_DATA)
        self.call_list()
        self.check_list_success()

    def test_list_with_no_results(self):
        """Test listing all system types returning no results."""

        self.mock_list([])
        self.call_list()
        self.check_list_success()
