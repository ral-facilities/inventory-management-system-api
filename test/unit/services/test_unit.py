"""
Unit tests for the `UnitService` service
"""

from unittest.mock import MagicMock, Mock, patch

from test.mock_data import UNIT_POST_DATA_MM


from test.unit.services.conftest import ServiceTestHelpers
import pytest
from bson import ObjectId
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.unit import UnitService


from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.schemas.unit import UnitPostSchema


class UnitServiceDSL:
    """Base class for `UnitService` unit tests."""

    wrapped_utils: Mock
    mock_unit_repository: Mock
    unit_service: UnitService

    @pytest.fixture(autouse=True)
    def setup(
        self,
        unit_repository_mock,
        unit_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""
        self.mock_unit_repository = unit_repository_mock
        self.unit_service = unit_service

        with patch("inventory_management_system_api.services.unit.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield


class CreateDSL(UnitServiceDSL):
    """Base class for `create` tests."""

    _unit_post: UnitPostSchema
    _expected_unit_in: UnitIn
    _expected_unit_out: UnitOut
    _created_unit: UnitOut

    def mock_create(self, unit_post_data: dict) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param unit_post_data: Dictionary containing the basic unit data as would be required for a
            `UnitPostSchema` (i.e. no ID, code or created and modified times required).
        """
        self._unit_post = UnitPostSchema(**unit_post_data)

        self._expected_unit_in = UnitIn(**unit_post_data, code=utils.generate_code(unit_post_data["value"], "unit"))
        self._expected_unit_out = UnitOut(**self._expected_unit_in.model_dump(), id=ObjectId())

        ServiceTestHelpers.mock_create(self.mock_unit_repository, self._expected_unit_out)

    def call_create(self) -> None:
        """
        Calls the `UnitService` `create` method with the appropriate data from a prior call to
        `mock_create`.
        """
        self._created_unit = self.unit_service.create(self._unit_post)

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""
        self.wrapped_utils.generate_code.assert_called_once_with(self._expected_unit_out.value, "unit")
        self.mock_unit_repository.create.assert_called_once_with(self._expected_unit_in)
        assert self._created_unit == self._expected_unit_out


class TestCreate(CreateDSL):
    """Tests for creating a unit."""

    def test_create(self):
        """Test creating a unit."""
        self.mock_create(UNIT_POST_DATA_MM)
        self.call_create()
        self.check_create_success()


class GetDSL(UnitServiceDSL):
    """Base class for `get` tests."""

    _obtained_unit_id: str
    _expected_unit: MagicMock
    _obtained_unit: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""
        # Simply a return currently, so no need to use actual data
        self._expected_unit = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_unit_repository, self._expected_unit)

    def call_get(self, unit_id: str) -> None:
        """
        Calls the `UnitService` `get` method.

        :param unit_id: ID of the unit to be obtained.
        """
        self._obtained_unit_id = unit_id
        self._obtained_unit = self.unit_service.get(unit_id)

    def check_get_success(self):
        """Checks that a prior call to `call_get` worked as expected."""
        self.mock_unit_repository.get.assert_called_once_with(self._obtained_unit_id)
        assert self._obtained_unit == self._expected_unit


class TestGet(GetDSL):
    """Tests for getting a unit."""

    def test_get(self):
        """Test getting a unit."""
        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class ListDSL(UnitServiceDSL):
    """Base class for `list` tests."""

    _expected_units: MagicMock
    _obtained_units: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_units = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_unit_repository, self._expected_units)

    def call_list(self) -> None:
        """Calls the `UnitService` `list` method."""
        self._obtained_units = self.unit_service.list()

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""
        self.mock_unit_repository.list.assert_called_once()
        assert self._obtained_units == self._expected_units


class TestList(ListDSL):
    """Tests for listing units."""

    def test_list(self):
        """Test listing units."""
        self.mock_list()
        self.call_list()
        self.check_list_success()


class DeleteDSL(UnitServiceDSL):
    """Base class for `delete` tests."""

    _delete_unit_id: str

    def call_delete(self, unit_id: str) -> None:
        """
        Calls the `UnitService` `delete` method.

        :param unit_id: ID of the unit to be deleted.
        """
        self._delete_unit_id = unit_id
        self.unit_service.delete(unit_id)

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""
        self.mock_unit_repository.delete.assert_called_once_with(self._delete_unit_id)


class TestDelete(DeleteDSL):
    """Tests for deleting a unit."""

    def test_delete(self):
        """Test deleting a unit."""
        self.call_delete(str(ObjectId()))
        self.check_delete_success()
