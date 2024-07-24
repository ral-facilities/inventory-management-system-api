"""
Unit tests for the `ManufacturerService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from typing import Optional
from unittest.mock import MagicMock, Mock, patch

from test.mock_data import MANUFACTURER_POST_DATA_A, MANUFACTURER_POST_DATA_B
from test.unit.services.conftest import ServiceTestHelpers

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.schemas.manufacturer import ManufacturerPatchSchema, ManufacturerPostSchema
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.manufacturer import ManufacturerService


class ManufacturerServiceDSL:
    """Base class for `ManufacturerService` unit tests."""

    wrapped_utils: Mock
    mock_manufacturer_repository: Mock
    manufacturer_service: ManufacturerService

    @pytest.fixture(autouse=True)
    def setup(
        self,
        manufacturer_repository_mock,
        manufacturer_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""
        self.mock_manufacturer_repository = manufacturer_repository_mock
        self.manufacturer_service = manufacturer_service

        with patch("inventory_management_system_api.services.manufacturer.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield


class CreateDSL(ManufacturerServiceDSL):
    """Base class for `create` tests."""

    _manufacturer_post: ManufacturerPostSchema
    _expected_manufacturer_in: ManufacturerIn
    _expected_manufacturer_out: ManufacturerOut
    _created_manufacturer: ManufacturerOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(self, manufacturer_post_data: dict) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param manufacturer_post_data: Dictionary containing the basic manufacturer data as would be required for a
            `ManufacturerPostSchema` (i.e. no ID, code or created and modified times required).
        """
        self._manufacturer_post = ManufacturerPostSchema(**manufacturer_post_data)

        self._expected_manufacturer_in = ManufacturerIn(
            **manufacturer_post_data, code=utils.generate_code(manufacturer_post_data["name"], "manufacturer")
        )
        self._expected_manufacturer_out = ManufacturerOut(**self._expected_manufacturer_in.model_dump(), id=ObjectId())

        ServiceTestHelpers.mock_create(self.mock_manufacturer_repository, self._expected_manufacturer_out)

    def call_create(self) -> None:
        """Calls the `ManufacturerService` `create` method with the appropriate data from a prior call to
        `mock_create`."""
        self._created_manufacturer = self.manufacturer_service.create(self._manufacturer_post)

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""
        self.wrapped_utils.generate_code.assert_called_once_with(self._expected_manufacturer_out.name, "manufacturer")
        self.mock_manufacturer_repository.create.assert_called_once_with(self._expected_manufacturer_in)
        assert self._created_manufacturer == self._expected_manufacturer_out


class TestCreate(CreateDSL):
    """Tests for creating a manufacturer."""

    def test_create(self):
        """Test creating a manufacturer."""
        self.mock_create(MANUFACTURER_POST_DATA_A)
        self.call_create()
        self.check_create_success()


class GetDSL(ManufacturerServiceDSL):
    """Base class for `get` tests."""

    _obtained_manufacturer_id: str
    _expected_manufacturer: MagicMock
    _obtained_manufacturer: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""
        # Simply a return currently, so no need to use actual data
        self._expected_manufacturer = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_manufacturer_repository, self._expected_manufacturer)

    def call_get(self, manufacturer_id: str) -> None:
        """
        Calls the `ManufacturerService` `get` method.

        :param manufacturer_id: ID of the manufacturer to be obtained.
        """
        self._obtained_manufacturer_id = manufacturer_id
        self._obtained_manufacturer = self.manufacturer_service.get(manufacturer_id)

    def check_get_success(self):
        """Checks that a prior call to `call_get` worked as expected."""
        self.mock_manufacturer_repository.get.assert_called_once_with(self._obtained_manufacturer_id)
        assert self._obtained_manufacturer == self._expected_manufacturer


class TestGet(GetDSL):
    """Tests for getting a manufacturer."""

    def test_get(self):
        """Test getting a manufacturer."""
        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class ListDSL(ManufacturerServiceDSL):
    """Base class for `list` tests."""

    _expected_manufacturers: MagicMock
    _obtained_manufacturers: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""
        # Simply a return currently, so no need to use actual data
        self._expected_manufacturers = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_manufacturer_repository, self._expected_manufacturers)

    def call_list(self) -> None:
        """Calls the `ManufacturerService` `list` method."""
        self._obtained_manufacturers = self.manufacturer_service.list()

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""
        self.mock_manufacturer_repository.list.assert_called_once()
        assert self._obtained_manufacturers == self._expected_manufacturers


class TestList(ListDSL):
    """Tests for listing manufacturers."""

    def test_list(self):
        """Test listing manufacturers."""
        self.mock_list()
        self.call_list()
        self.check_list_success()


class UpdateDSL(ManufacturerServiceDSL):
    """Base class for `update` tests."""

    _stored_manufacturer: Optional[ManufacturerOut]
    _manufacturer_patch: ManufacturerPatchSchema
    _expected_manufacturer_in: ManufacturerIn
    _expected_manufacturer_out: MagicMock
    _updated_manufacturer_id: str
    _updated_manufacturer: MagicMock
    _update_exception: pytest.ExceptionInfo

    def mock_update(
        self, manufacturer_id: str, manufacturer_patch_data: dict, stored_manufacturer_post_data: Optional[dict]
    ) -> None:
        """
        Mocks the repository methods appropriately to test the `update` service method.

        :param manufacturer_id: ID of the manufacturer to be updated.
        :param manufacturer_patch_data: Dictionary containing the patch data as would be required for a
            `ManufacturerPatchSchema` (i.e. no ID, code, or created and modified times required).
        :param stored_manufacturer_post_data: Dictionary containing the manufacturer data for the existing stored
            manufacturer as would be required for `ManufacturerPostSchema` (i.e. no ID, code or created and modified
            times required).
        """
        # Stored manufacturer
        self._stored_manufacturer = (
            ManufacturerOut(
                **ManufacturerIn(
                    **stored_manufacturer_post_data,
                    code=utils.generate_code(stored_manufacturer_post_data["name"], "manufacturer"),
                ).model_dump(),
                id=CustomObjectId(manufacturer_id),
            )
            if stored_manufacturer_post_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_manufacturer_repository, self._stored_manufacturer)

        # Patch schema
        self._manufacturer_patch = ManufacturerPatchSchema(**manufacturer_patch_data)

        # Updated manufacturer
        self._expected_manufacturer_out = MagicMock()
        ServiceTestHelpers.mock_update(self.mock_manufacturer_repository, self._expected_manufacturer_out)

        # Construct the expected input for the repository
        merged_manufacturer_data = {**(stored_manufacturer_post_data or {}), **manufacturer_patch_data}
        self._expected_manufacturer_in = ManufacturerIn(
            **merged_manufacturer_data, code=utils.generate_code(merged_manufacturer_data["name"], "manufacturer")
        )

    def call_update(self, manufacturer_id: str) -> None:
        """
        Class the `ManufacturerService` `update` method with the appropriate data from a prior call to `mock_update`.

        :param manufacturer_id: ID of the manufacturer to be updated.
        """
        self._updated_manufacturer_id = manufacturer_id
        self._updated_manufacturer = self.manufacturer_service.update(manufacturer_id, self._manufacturer_patch)

    def call_update_expecting_error(self, manufacturer_id: str, error_type: type[BaseException]) -> None:
        """
        Class the `ManufacturerService` `update` method with the appropriate data from a prior call to `mock_update`
        while expecting an error to be raised.

        :param manufacturer_id: ID of the manufacturer to be updated.
        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.manufacturer_service.update(manufacturer_id, self._manufacturer_patch)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as updated."""
        # Ensure obtained old manufacturer
        self.mock_manufacturer_repository.get.assert_called_once_with(self._updated_manufacturer_id)

        # Ensure new code was obtained if patching name
        if self._manufacturer_patch.name:
            self.wrapped_utils.generate_code.assert_called_once_with(self._manufacturer_patch.name, "manufacturer")
        else:
            self.wrapped_utils.generate_code.assert_not_called()

        # Ensure updated with expected data
        self.mock_manufacturer_repository.update.assert_called_once_with(
            self._updated_manufacturer_id, self._expected_manufacturer_in
        )

        assert self._updated_manufacturer == self._expected_manufacturer_out

    def check_update_failed_with_exception(self, message: str):
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """
        self.mock_manufacturer_repository.update.assert_not_called()
        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a manufacturer."""

    def test_update(self):
        """Test updating all fields of a manufacturer."""
        manufacturer_id = str(ObjectId())

        self.mock_update(
            manufacturer_id,
            manufacturer_patch_data=MANUFACTURER_POST_DATA_B,
            stored_manufacturer_post_data=MANUFACTURER_POST_DATA_A,
        )
        self.call_update(manufacturer_id)
        self.check_update_success()

    def test_update_address_only(self) -> None:
        """Test updating manufacturer's address only (code should not need regenerating as name doesn't change)."""
        manufacturer_id = str(ObjectId())

        self.mock_update(
            manufacturer_id,
            manufacturer_patch_data=MANUFACTURER_POST_DATA_B["address"],
            stored_manufacturer_post_data=MANUFACTURER_POST_DATA_A,
        )
        self.call_update(manufacturer_id)
        self.check_update_success()

    def test_update_with_non_existent_id(self):
        """Test updating a manufacturer with a non-existent ID."""
        manufacturer_id = str(ObjectId())

        self.mock_update(
            manufacturer_id, manufacturer_patch_data=MANUFACTURER_POST_DATA_A, stored_manufacturer_post_data=None
        )
        self.call_update_expecting_error(manufacturer_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No manufacturer found with ID: {manufacturer_id}")


class DeleteDSL(ManufacturerServiceDSL):
    """Base class for `delete` tests."""

    _delete_manufacturer_id: str

    def call_delete(self, manufacturer_id: str) -> None:
        """
        Calls the `ManufacturerService` `delete` method.

        :param manufacturer_id: ID of the manufacturer to be deleted.
        """
        self._delete_manufacturer_id = manufacturer_id
        self.manufacturer_service.delete(manufacturer_id)

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""
        self.mock_manufacturer_repository.delete.assert_called_once_with(self._delete_manufacturer_id)


class TestDelete(DeleteDSL):
    """Tests for deleting a manufacturer."""

    def test_delete(self):
        """Test deleting a manufacturer."""
        self.call_delete(str(ObjectId()))
        self.check_delete_success()
