"""
Unit tests for the `SystemTypeService` service.
"""

from test.unit.services.conftest import ServiceTestHelpers
from unittest.mock import MagicMock, Mock

import pytest

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
