"""
Unit tests for the `SystemTypeService` service.
"""

from test.unit.services.conftest import ServiceTestHelpers
from unittest.mock import MagicMock, Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.services.system_type import SystemTypeService


class SystemTypeServiceDSL:
    """Base class for `SystemTypeService` unit tests."""

    mock_system_type_repository: Mock
    system_type_service: SystemTypeService

    @pytest.fixture(autouse=True)
    def setup(self, system_type_repository_mock, system_type_service):
        """Setup fixtures."""

        self.mock_system_type_repository = system_type_repository_mock
        self.system_type_service = system_type_service


class ListDSL(SystemTypeServiceDSL):
    """Base class for `list` tests."""

    _expected_system_types: MagicMock
    _obtained_system_types: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_system_types = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_system_type_repository, self._expected_system_types)

    def call_list(self) -> None:
        """Calls the `SystemTypeService` `list` method."""

        self._obtained_system_types = self.system_type_service.list()

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_system_type_repository.list.assert_called_once_with()
        assert self._obtained_system_types == self._expected_system_types


class TestList(ListDSL):
    """Tests for listing system types."""

    def test_list(self):
        """Test listing system types."""

        self.mock_list()
        self.call_list()
        self.check_list_success()


class GetDSL(SystemTypeServiceDSL):
    """Base class for 'get' tests."""

    _obtained_system_type_id: str
    _expected_system_type: MagicMock
    _obtained_system_type: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the 'get' service method."""

        self._expected_system_type = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_system_type_repository, self._expected_system_type)

    def call_get(self, system_type_id: str) -> None:
        """
        Calls the 'SystemTypeService' 'get' method.

        :param system_type_id: ID of the system type to be obtained.
        """

        self._obtained_system_type_id = system_type_id
        self._obtained_system_type = self.system_type_service.get(system_type_id)

    def check_get_success(self) -> None:
        """Checks that a prior call to 'call_get' worked as expected."""

        self.mock_system_type_repository.get.assert_called_once_with(self._obtained_system_type_id)
        assert self._obtained_system_type == self._expected_system_type


class TestGet(GetDSL):
    """Tests for getting a system type."""

    def test_get(self):
        """Test getting a system type."""

        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()
