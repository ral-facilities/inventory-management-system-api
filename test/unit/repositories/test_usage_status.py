"""
Unit tests for the `UsageStatusRepo` repository.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import ITEM_DATA_REQUIRED_VALUES_ONLY, USAGE_STATUS_IN_DATA_NEW, USAGE_STATUS_IN_DATA_USED
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfItemError,
)
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo


class UsageStatusRepoDSL:
    """Base class for `UsageStatusRepo` unit tests."""

    mock_database: Mock
    usage_status_repository: UsageStatusRepo
    usage_statuses_collection: Mock
    items_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures"""
        self.mock_database = database_mock
        self.usage_status_repository = UsageStatusRepo(database_mock)
        self.usage_statuses_collection = database_mock.usage_statuses
        self.items_collection = database_mock.items

        self.mock_session = MagicMock()
        yield

    def mock_is_duplicate_usage_status(self, duplicate_usage_status_in_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `_is_duplicate_usage_status` repo method will be called.

        :param duplicate_usage_status_in_data: Either `None` or a dictionary containing usage status data for a
            duplicate usage status.
        """
        RepositoryTestHelpers.mock_find_one(
            self.usage_statuses_collection,
            (
                {**UsageStatusIn(**duplicate_usage_status_in_data).model_dump(), "_id": ObjectId()}
                if duplicate_usage_status_in_data
                else None
            ),
        )

    def get_is_duplicate_usage_status_expected_find_one_call(
        self, usage_status_in: UsageStatusIn, expected_usage_status_id: Optional[CustomObjectId]
    ):
        """
        Returns the expected `find_one` calls that should occur when `_is_duplicate_usage_status` is called.

        :param usage_status_in: `UsageStatusIn` model containing the data about the usage status.
        :param expected_usage_status_id: Expected `usage_status_id` provided to `_is_duplicate_usage_status`.
        :return: Expected `find_one` calls.
        """
        return call({"code": usage_status_in.code, "_id": {"$ne": expected_usage_status_id}}, session=self.mock_session)


class CreateDSL(UsageStatusRepoDSL):
    """Base class for `create` tests."""

    _usage_status_in: UsageStatusIn
    _expected_usage_status_out: UsageStatusOut
    _created_usage_status: UsageStatusOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(self, usage_status_in_data: dict, duplicate_usage_status_in_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately to test the `create` repo method.

        :param usage_status_in_data: Dictionary containing the usage status data as would be required for a
            `UsageStatusIn` database model (i.e. no ID or created and modified times required).
        :param duplicate_usage_status_in_data: Either `None` or a dictionary containing usage status data for a
            duplicate usage status.
        """
        inserted_usage_status_id = CustomObjectId(str(ObjectId()))

        # Pass through UsageStatusIn first as need creation and modified times
        self._usage_status_in = UsageStatusIn(**usage_status_in_data)

        self._expected_usage_status_out = UsageStatusOut(
            **self._usage_status_in.model_dump(), id=inserted_usage_status_id
        )
        #
        self.mock_is_duplicate_usage_status(duplicate_usage_status_in_data)
        # Mock `insert one` to return object for inserted usage status
        RepositoryTestHelpers.mock_insert_one(self.usage_statuses_collection, inserted_usage_status_id)
        # Mock `find_one` to return the inserted usage status document
        RepositoryTestHelpers.mock_find_one(
            self.usage_statuses_collection, {**self._usage_status_in.model_dump(), "_id": inserted_usage_status_id}
        )

    def call_create(self) -> None:
        """Calls the `UsageStatusRepo` `create` method with the appropriate data from a prior call to `mock_create`."""
        self._created_usage_status = self.usage_status_repository.create(
            self._usage_status_in, session=self.mock_session
        )

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `UsageStatusRepo` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.usage_status_repository.create(self._usage_status_in, session=self.mock_session)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""
        usage_status_in_data = self._usage_status_in.model_dump()

        # Obtain a list of expected find_one calls
        expected_find_one_calls = [
            # This is the check for the duplicate
            self.get_is_duplicate_usage_status_expected_find_one_call(self._usage_status_in, None),
            # This is the check for the newly inserted usage status get
            call({"_id": CustomObjectId(self._expected_usage_status_out.id)}, session=self.mock_session),
        ]
        self.usage_statuses_collection.find_one.assert_has_calls(expected_find_one_calls)

        self.usage_statuses_collection.insert_one.assert_called_once_with(
            usage_status_in_data, session=self.mock_session
        )
        assert self._created_usage_status == self._expected_usage_status_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """
        self.usage_statuses_collection.insert_one.assert_not_called()
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a usage status."""

    def test_create(self):
        """Test creating a usage status."""
        self.mock_create(USAGE_STATUS_IN_DATA_NEW)
        self.call_create()
        self.check_create_success()

    def test_create_with_duplicate_name(self):
        """Test creating a usage status with a duplicate usage status being found."""
        self.mock_create(USAGE_STATUS_IN_DATA_NEW, duplicate_usage_status_in_data=USAGE_STATUS_IN_DATA_NEW)
        self.call_create_expecting_error(DuplicateRecordError)
        self.check_create_failed_with_exception("Duplicate usage status found")


class GetDSL(UsageStatusRepoDSL):
    """Base class for `get` tests."""

    _obtained_usage_status_id: str
    _expected_usage_status_out: Optional[UsageStatusOut]
    _obtained_usage_status_out: UsageStatusOut
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, usage_status_id: str, usage_status_in_data: Optional[dict]) -> None:
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param usage_status_id: ID of the usage status to be obtained.
        :param usage_status_in_data: Either `None` or a dictionary containing the usage status data as would be required
            for a `UsageStatusIn` database model (i.e. no ID or created and modified times required).
        """
        self._expected_usage_status_out = (
            UsageStatusOut(**UsageStatusIn(**usage_status_in_data).model_dump(), id=CustomObjectId(usage_status_id))
            if usage_status_in_data
            else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.usage_statuses_collection,
            self._expected_usage_status_out.model_dump() if self._expected_usage_status_out else None,
        )

    def call_get(self, usage_status_id: str) -> None:
        """
        Calls the `UsageStatusRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param usage_status_id: ID of the usage status to be obtained.
        """
        self._obtained_usage_status_id = usage_status_id
        self._obtained_usage_status_out = self.usage_status_repository.get(usage_status_id, session=self.mock_session)

    def call_get_expecting_error(self, usage_status_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `UsageStatusRepo` `get` method with the appropriate data from a prior call to `mock_get` while
        expecting an error to be raised.

        :param usage_status_id: ID of the usage status to be obtained.
        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.usage_status_repository.get(usage_status_id, session=self.mock_session)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""
        self.usage_statuses_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_usage_status_id)}, session=self.mock_session
        )
        assert self._obtained_usage_status_out == self._expected_usage_status_out

    def check_get_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception with the correct
        message.

        :param message: Expected message of the raised exception.
        """
        self.usage_statuses_collection.find_one.assert_not_called()
        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a usage status."""

    def test_get(self):
        """Test getting a usage status."""
        usage_status_id = str(ObjectId())

        self.mock_get(usage_status_id, USAGE_STATUS_IN_DATA_NEW)
        self.call_get(usage_status_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Testing getting a usage status with a non-existent ID."""
        usage_status_id = str(ObjectId())

        self.mock_get(usage_status_id, None)
        self.call_get(usage_status_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting a usage status with an invalid ID."""
        usage_status_id = "invalid-id"

        self.call_get_expecting_error(usage_status_id, InvalidObjectIdError)
        self.check_get_failed_with_exception(f"Invalid ObjectId value '{usage_status_id}'")


class ListDSL(UsageStatusRepoDSL):
    """Base class for `list` tests."""

    _expected_usage_status_out: list[UsageStatusOut]
    _obtained_usage_status_out: list[UsageStatusOut]

    def mock_list(self, usage_status_in_data: list[dict]) -> None:
        """
        Mocks database methods appropriately to test the `list` repo method.

        :param usage_status_in_data: List of dictionaries containing the usage status data as would be required for a
            `UsageStatusIn` database model (i.e. no ID or created and modified times required).
        """
        self._expected_usage_status_out = [
            UsageStatusOut(**UsageStatusIn(**usage_status_in_data).model_dump(), id=ObjectId())
            for usage_status_in_data in usage_status_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.usage_statuses_collection,
            [usage_status_out.model_dump() for usage_status_out in self._expected_usage_status_out],
        )

    def call_list(self) -> None:
        """Calls the `UsageStatusRepo` `list method` method."""
        self._obtained_usage_status_out = self.usage_status_repository.list(session=self.mock_session)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""
        self.usage_statuses_collection.find.assert_called_once_with(session=self.mock_session)
        assert self._obtained_usage_status_out == self._expected_usage_status_out


class TestList(ListDSL):
    """Tests for listing usage statuses."""

    def test_list(self):
        """Test listing all usage statuses."""
        self.mock_list([USAGE_STATUS_IN_DATA_NEW, USAGE_STATUS_IN_DATA_USED])
        self.call_list()
        self.check_list_success()

    def test_list_with_no_results(self):
        """Test listing all usage statuses returning no results."""
        self.mock_list([])
        self.call_list()
        self.check_list_success()


class DeleteDSL(UsageStatusRepoDSL):
    """Base class for `delete` tests."""

    _delete_usage_status_id: str
    _delete_exception: pytest.ExceptionInfo
    _mock_item_data: Optional[dict]

    def mock_delete(self, deleted_count: int, item_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        :param item_data: Dictionary containing an item's data (or `None`).
        """
        self.mock_is_usage_status_in_item(item_data)
        RepositoryTestHelpers.mock_delete_one(self.usage_statuses_collection, deleted_count)

    def call_delete(self, usage_status_id: str) -> None:
        """
        Calls the `UsageStatusRepo` `delete` method with the appropriate data from a prior call to `mock_delete`.

        :param usage_status_id: ID of the usage status to be deleted.
        """
        self._delete_usage_status_id = usage_status_id
        self.usage_status_repository.delete(usage_status_id, session=self.mock_session)

    def call_delete_expecting_error(self, usage_status_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `UsageStatusRepo` `delete` method with the appropriate data from a prior call to `mock_delete` while
        expecting an error to be raised.

        :param usage_status_id: ID of the usage status to be deleted.
        :param error_type: Expected exception to be raised.
        """
        self._delete_usage_status_id = usage_status_id
        with pytest.raises(error_type) as exc:
            self.usage_status_repository.delete(usage_status_id, session=self.mock_session)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""
        self.check_is_usage_status_in_item_performed_expected_calls(self._delete_usage_status_id)
        self.usage_statuses_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_usage_status_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """
        if not expecting_delete_one_called:
            self.usage_statuses_collection.delete_one.assert_not_called()
        else:
            self.usage_statuses_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_usage_status_id)}, session=self.mock_session
            )

        assert str(self._delete_exception.value) == message

    def mock_is_usage_status_in_item(self, item_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `_is_usage_status_in_item` repo method will be
        called.

        :param item_data: Dictionary containing an item's data (or `None`).
        """
        self._mock_item_data = item_data
        RepositoryTestHelpers.mock_find_one(self.items_collection, item_data)

    def check_is_usage_status_in_item_performed_expected_calls(self, expected_usage_status_id: str) -> None:
        """Checks that a call to `_is_usage_status_in_item` performed the expected method calls.

        :param expected_usage_status_id: Expected usage status ID used in the database calls.
        """
        self.items_collection.find_one.assert_called_once_with(
            {"usage_status_id": CustomObjectId(expected_usage_status_id)}, session=self.mock_session
        )


class TestDelete(DeleteDSL):
    """Tests for deleting a usage status."""

    def test_delete(self):
        """Test deleting a usage status."""
        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_when_part_of_item(self):
        """Test deleting a usage status when it is part of an item."""
        usage_status_id = str(ObjectId())

        self.mock_delete(
            deleted_count=1,
            item_data={
                **ITEM_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(ObjectId()),
                "system_id": str(ObjectId()),
                "usage_status_id": usage_status_id,
            },
        )
        self.call_delete_expecting_error(usage_status_id, PartOfItemError)
        self.check_delete_failed_with_exception(f"The usage status with ID {usage_status_id} is a part of an Item")

    def test_delete_non_existent_id(self):
        """Test deleting a usage status with a non-existent ID."""
        usage_status_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(usage_status_id, MissingRecordError)
        self.check_delete_failed_with_exception(
            f"No usage status found with ID: {usage_status_id}", expecting_delete_one_called=True
        )

    def test_delete_with_invalid_id(self):
        """Test deleting a usage status with an invalid ID."""
        usage_status_id = "invalid-id"

        self.call_delete_expecting_error(usage_status_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception(f"Invalid ObjectId value '{usage_status_id}'")
