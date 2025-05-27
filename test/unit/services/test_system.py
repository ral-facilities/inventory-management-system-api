"""
Unit tests for the `SystemService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import SYSTEM_POST_DATA_NO_PARENT_A, SYSTEM_POST_DATA_NO_PARENT_B
from test.unit.services.conftest import ServiceTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import ChildElementsExistError
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.system import SystemService


class SystemServiceDSL:
    """Base class for `SystemService` unit tests."""

    wrapped_utils: Mock
    mock_system_repository: Mock
    system_service: SystemService

    @pytest.fixture(autouse=True)
    def setup(
        self,
        system_repository_mock,
        system_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures."""

        self.mock_system_repository = system_repository_mock
        self.system_service = system_service

        with patch("inventory_management_system_api.services.system.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield


class CreateDSL(SystemServiceDSL):
    """Base class for `create` tests."""

    _system_post: SystemPostSchema
    _expected_system_in: SystemIn
    _expected_system_out: SystemOut
    _created_system: SystemOut

    def mock_create(self, system_post_data: dict) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param system_post_data: Dictionary containing the basic system data as would be required for a
                                 `SystemPostSchema` (i.e. no ID, code or created and modified times required).
        """

        self._system_post = SystemPostSchema(**system_post_data)

        self._expected_system_in = SystemIn(
            **system_post_data, code=utils.generate_code(system_post_data["name"], "system")
        )
        self._expected_system_out = SystemOut(**self._expected_system_in.model_dump(), id=ObjectId())

        ServiceTestHelpers.mock_create(self.mock_system_repository, self._expected_system_out)

    def call_create(self) -> None:
        """Calls the `SystemService` `create` method with the appropriate data from a prior call to `mock_create`."""

        self._created_system = self.system_service.create(self._system_post)

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        self.wrapped_utils.generate_code.assert_called_once_with(self._expected_system_out.name, "system")
        self.mock_system_repository.create.assert_called_once_with(self._expected_system_in)

        assert self._created_system == self._expected_system_out


class TestCreate(CreateDSL):
    """Tests for creating a system."""

    def test_create(self):
        """Test creating a system."""

        self.mock_create(SYSTEM_POST_DATA_NO_PARENT_A)
        self.call_create()
        self.check_create_success()

    def test_create_with_parent_id(self):
        """Test creating a system with a parent ID."""

        self.mock_create({**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())})
        self.call_create()
        self.check_create_success()


class GetDSL(SystemServiceDSL):
    """Base class for `get` tests."""

    _obtained_system_id: str
    _expected_system: MagicMock
    _obtained_system: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_system = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_system_repository, self._expected_system)

    def call_get(self, system_id: str) -> None:
        """
        Calls the `SystemService` `get` method.

        :param system_id: ID of the system to be obtained.
        """

        self._obtained_system_id = system_id
        self._obtained_system = self.system_service.get(system_id)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.mock_system_repository.get.assert_called_once_with(self._obtained_system_id)
        assert self._obtained_system == self._expected_system


class TestGet(GetDSL):
    """Tests for getting a system."""

    def test_get(self):
        """Test getting a system."""

        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class GetBreadcrumbsDSL(SystemServiceDSL):
    """Base class for `get_breadcrumbs` tests."""

    _expected_breadcrumbs: MagicMock
    _obtained_breadcrumbs: MagicMock
    _obtained_system_id: str

    def mock_get_breadcrumbs(self) -> None:
        """Mocks repo methods appropriately to test the `get_breadcrumbs` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_breadcrumbs = MagicMock()
        ServiceTestHelpers.mock_get_breadcrumbs(self.mock_system_repository, self._expected_breadcrumbs)

    def call_get_breadcrumbs(self, system_id: str) -> None:
        """
        Calls the `SystemService` `get_breadcrumbs` method.

        :param system_id: ID of the system to obtain the breadcrumbs of.
        """

        self._obtained_system_id = system_id
        self._obtained_breadcrumbs = self.system_service.get_breadcrumbs(system_id)

    def check_get_breadcrumbs_success(self) -> None:
        """Checks that a prior call to `call_get_breadcrumbs` worked as expected."""

        self.mock_system_repository.get_breadcrumbs.assert_called_once_with(self._obtained_system_id)
        assert self._obtained_breadcrumbs == self._expected_breadcrumbs


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting the breadcrumbs of a system."""

    def test_get_breadcrumbs(self):
        """Test getting a system's breadcrumbs."""

        self.mock_get_breadcrumbs()
        self.call_get_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_success()


class ListDSL(SystemServiceDSL):
    """Base class for `list` tests."""

    _parent_id_filter: Optional[str]
    _expected_systems: MagicMock
    _obtained_systems: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_systems = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_system_repository, self._expected_systems)

    def call_list(self, parent_id: Optional[str]) -> None:
        """
        Calls the `SystemService` `list` method.

        :param parent_id: ID of the parent system to query by, or `None`.
        """

        self._parent_id_filter = parent_id
        self._obtained_systems = self.system_service.list(parent_id)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_system_repository.list.assert_called_once_with(self._parent_id_filter)
        assert self._obtained_systems == self._expected_systems


class TestList(ListDSL):
    """Tests for listing systems."""

    def test_list(self):
        """Test listing systems."""

        self.mock_list()
        self.call_list(str(ObjectId()))
        self.check_list_success()


class UpdateDSL(SystemServiceDSL):
    """Base class for `update` tests"""

    _stored_system: Optional[SystemOut]
    _system_patch: SystemPatchSchema
    _expected_system_in: SystemIn
    _expected_system_out: MagicMock
    _updated_system_id: str
    _updated_system: MagicMock
    _update_exception: pytest.ExceptionInfo

    def mock_update(self, system_id: str, system_patch_data: dict, stored_system_post_data: Optional[dict]) -> None:
        """
        Mocks repository methods appropriately to test the `update` service method.

        :param system_id: ID of the system that will be obtained.
        :param system_patch_data: Dictionary containing the patch data as would be required for a
                                  `SystemPatchSchema` (i.e. no ID, code, or created and modified times required).
        :param stored_system_post_data: Dictionary containing the system data for the existing stored system.
                                        as would be required for a `SystemPostSchema` (i.e. no ID, code or created and
                                        modified times required).
        """

        # Stored system
        self._stored_system = (
            SystemOut(
                **SystemIn(
                    **stored_system_post_data, code=utils.generate_code(stored_system_post_data["name"], "system")
                ).model_dump(),
                id=CustomObjectId(system_id),
            )
            if stored_system_post_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_system_repository, self._stored_system)

        # Patch schema
        self._system_patch = SystemPatchSchema(**system_patch_data)

        # Updated system
        self._expected_system_out = MagicMock()
        ServiceTestHelpers.mock_update(self.mock_system_repository, self._expected_system_out)

        # Construct the expected input for the repository
        merged_system_data = {**(stored_system_post_data or {}), **system_patch_data}
        self._expected_system_in = SystemIn(
            **merged_system_data,
            code=utils.generate_code(merged_system_data["name"], "system"),
        )

    def call_update(self, system_id: str) -> None:
        """
        Calls the `SystemService` `update` method with the appropriate data from a prior call to `mock_update`.

        :param system_id: ID of the system to be updated.
        """

        self._updated_system_id = system_id
        self._updated_system = self.system_service.update(system_id, self._system_patch)

    def call_update_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemService` `update` method with the appropriate data from a prior call to `mock_update`
        while expecting an error to be raised.

        :param system_id: ID of the system to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_service.update(system_id, self._system_patch)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        # Ensure obtained old system
        self.mock_system_repository.get.assert_called_once_with(self._updated_system_id)

        # Ensure new code was obtained if patching name
        if self._system_patch.name:
            self.wrapped_utils.generate_code.assert_called_once_with(self._system_patch.name, "system")
        else:
            self.wrapped_utils.generate_code.assert_not_called()

        # Ensure updated with expected data
        self.mock_system_repository.update.assert_called_once_with(self._updated_system_id, self._expected_system_in)

        assert self._updated_system == self._expected_system_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_system_repository.update.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a system."""

    def test_update_all_fields_except_parent_id(self):
        """Test updating all fields of a system except its parent ID."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data=SYSTEM_POST_DATA_NO_PARENT_B,
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_description_only(self):
        """Test updating system's description field only (code should not need regenerating as name doesn't change)."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"description": "A new description"},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
        )
        self.call_update(system_id)
        self.check_update_success()


class DeleteDSL(SystemServiceDSL):
    """Base class for `delete` tests."""

    _delete_system_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(self, has_child_elements: Optional[bool] = False) -> None:
        """
        Mocks repo methods appropriately to test the `delete` service method.

        :param has_child_elements: Whether the system being deleted has child elements or not.
        """

        self.mock_system_repository.has_child_elements.return_value = has_child_elements

    def call_delete(self, system_id: str) -> None:
        """
        Calls the `SystemService` `delete` method.

        :param system_id: ID of the system to be deleted.
        """

        self._delete_system_id = system_id
        self.system_service.delete(system_id)

    def call_delete_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemService` `delete` method while expecting an error to be raised.

        :param system_id: ID of the system to be deleted.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_service.delete(system_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.mock_system_repository.delete.assert_called_once_with(self._delete_system_id)

    def check_delete_failed_with_exception(self, message: str) -> None:
        """
        Check that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_system_repository.delete.assert_not_called()
        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting a system."""

    def test_delete(self):
        """Test deleting a system."""

        self.mock_delete(has_child_elements=False)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_child_elements(self):
        """Test deleting a system when it has child elements."""

        system_id = str(ObjectId())

        self.mock_delete(has_child_elements=True)
        self.call_delete_expecting_error(system_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(f"System with ID {system_id} has child elements and cannot be deleted")
