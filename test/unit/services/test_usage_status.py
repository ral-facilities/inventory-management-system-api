"""
Unit tests for the `UsageStatusService` service.
"""

from test.mock_data import USAGE_STATUS_POST_DATA_NEW
from test.unit.services.conftest import ServiceTestHelpers
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.schemas.usage_status import UsageStatusPostSchema
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.usage_status import UsageStatusService


class UsageStatusServiceDSL:
    """Base class for `UsageStatusService` unit tests."""

    wrapped_utils: Mock
    mock_usage_status_repository: Mock
    usage_status_service: UsageStatusService

    @pytest.fixture(autouse=True)
    def setup(
        self,
        usage_status_repository_mock,
        usage_status_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""
        self.mock_usage_status_repository = usage_status_repository_mock
        self.usage_status_service = usage_status_service

        with patch("inventory_management_system_api.services.usage_status.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield


class CreateDSL(UsageStatusServiceDSL):
    """Base class for `create` tests."""

    _usage_status_post: UsageStatusPostSchema
    _expected_usage_status_in: UsageStatusIn
    _expected_usage_status_out: UsageStatusOut
    _created_usage_status: UsageStatusOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(self, usage_status_post_data: dict) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param usage_status_post_data: Dictionary containing the basic usage status data as would be required for a
            `UsageStatusPostSchema` (i.e. no ID, code or created and modified times required).
        """
        self._usage_status_post = UsageStatusPostSchema(**usage_status_post_data)

        self._expected_usage_status_in = UsageStatusIn(
            **usage_status_post_data, code=utils.generate_code(usage_status_post_data["value"], "usage status")
        )
        self._expected_usage_status_out = UsageStatusOut(**self._expected_usage_status_in.model_dump(), id=ObjectId())

        ServiceTestHelpers.mock_create(self.mock_usage_status_repository, self._expected_usage_status_out)

    def call_create(self) -> None:
        """
        Calls the `UsageStatusService` `create` method with the appropriate data from a prior call to `mock_create`.
        """
        self._created_usage_status = self.usage_status_service.create(self._usage_status_post)

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""
        self.wrapped_utils.generate_code.assert_called_once_with(self._expected_usage_status_out.value, "usage status")
        self.mock_usage_status_repository.create.assert_called_once_with(self._expected_usage_status_in)
        assert self._created_usage_status == self._expected_usage_status_out


class TestCreate(CreateDSL):
    """Tests for creating a usage status."""

    def test_create(self):
        """Test creating a usage status."""
        self.mock_create(USAGE_STATUS_POST_DATA_NEW)
        self.call_create()
        self.check_create_success()


class GetDSL(UsageStatusServiceDSL):
    """Base class for `get` tests."""

    _obtained_usage_status_id: str
    _expected_usage_status: MagicMock
    _obtained_usage_status: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""
        # Simply a return currently, so no need to use actual data
        self._expected_usage_status = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_usage_status_repository, self._expected_usage_status)

    def call_get(self, usage_status_id: str) -> None:
        """
        Calls the `UsageStatusService` `get` method.

        :param usage_status_id: ID of the usage status to be obtained.
        """
        self._obtained_usage_status_id = usage_status_id
        self._obtained_usage_status = self.usage_status_service.get(usage_status_id)

    def check_get_success(self):
        """Checks that a prior call to `call_get` worked as expected."""
        self.mock_usage_status_repository.get.assert_called_once_with(self._obtained_usage_status_id)
        assert self._obtained_usage_status == self._expected_usage_status


class TestGet(GetDSL):
    """Tests for getting a usage status."""

    def test_get(self):
        """Test getting a usage status."""
        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class ListDSL(UsageStatusServiceDSL):
    """Base class for `list` tests."""

    _expected_usage_statuses: MagicMock
    _obtained_usage_statuses: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        self._expected_usage_statuses = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_usage_status_repository, self._expected_usage_statuses)

    def call_list(self) -> None:
        """Calls the `UsageStatusService` `list` method."""
        self._expected_usage_statuses = self.usage_status_service.list()

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""
        self.mock_usage_status_repository.list.assert_called_once()
        assert self._expected_usage_statuses == self._expected_usage_statuses


class TestList(ListDSL):
    """Tests for listing usage statuses."""

    def test_list(self):
        """Test listing usage statuses."""
        self.mock_list()
        self.call_list()
        self.check_list_success()


class DeleteDSL(UsageStatusServiceDSL):
    """Base class for `delete` tests."""

    _delete_usage_status_id: str

    def call_delete(self, usage_status_id: str) -> None:
        """
        Calls the `UsageStatusService` `delete` method.

        :param usage_status_id: ID of the usage status to be deleted.
        """
        self._delete_usage_status_id = usage_status_id
        self.usage_status_service.delete(usage_status_id)

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""
        self.mock_usage_status_repository.delete.assert_called_once_with(self._delete_usage_status_id)


class TestDelete(DeleteDSL):
    """Tests for deleting a usage status."""

    def test_delete(self):
        """Test deleting a usage status."""
        self.call_delete(str(ObjectId()))
        self.check_delete_success()
