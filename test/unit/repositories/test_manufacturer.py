"""
Unit tests for the `ManufacturerRepo` repository.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY, MANUFACTURER_IN_DATA_A, MANUFACTURER_IN_DATA_B
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfCatalogueItemError,
)
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo


class ManufacturerRepoDSL:
    """Base class for `ManufacturerRepo` unit tests."""

    mock_database: Mock
    manufacturer_repository: ManufacturerRepo
    manufacturers_collection: Mock
    catalogue_items_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures"""
        self.mock_database = database_mock
        self.manufacturer_repository = ManufacturerRepo(database_mock)
        self.manufacturers_collection = database_mock.manufacturers
        self.catalogue_items_collection = database_mock.catalogue_items

        yield


class CreateDSL(ManufacturerRepoDSL):
    """Base class for `create` tests."""

    _manufacturer_in: ManufacturerIn
    _expected_manufacturer_out: ManufacturerOut
    _created_manufacturer: ManufacturerOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        manufacturer_in_data: dict,
        raise_duplicate_key_error: bool = False,
    ) -> None:
        """
        Mocks database methods appropriately to test the `create` repo method.

        :param manufacturer_in_data: Dictionary containing the manufacturer data as would be required for a
            `ManufacturerIn` database model (i.e. no ID or created and modified times required).
        :param raise_duplicate_key_error: Whether a duplicate key error should be raised by the pymongo `insert_one`
            method.
        """
        inserted_manufacturer_id = CustomObjectId(str(ObjectId()))

        # Pass through ManufacturerIn first as need creation and modified times
        self._manufacturer_in = ManufacturerIn(**manufacturer_in_data)

        self._expected_manufacturer_out = ManufacturerOut(
            **self._manufacturer_in.model_dump(), id=inserted_manufacturer_id
        )
        #
        # Mock `insert one` to return object for inserted manufacturer
        RepositoryTestHelpers.mock_insert_one(
            self.manufacturers_collection, inserted_manufacturer_id, raise_duplicate_key_error=raise_duplicate_key_error
        )
        # Mock `find_one` to return the inserted manufacturer document
        RepositoryTestHelpers.mock_find_one(
            self.manufacturers_collection, {**self._manufacturer_in.model_dump(), "_id": inserted_manufacturer_id}
        )

    def call_create(self) -> None:
        """Calls the `ManufacturerRepo` `create` method with the appropriate data from a prior call to `mock_create`."""
        self._created_manufacturer = self.manufacturer_repository.create(
            self._manufacturer_in, session=self.mock_session
        )

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `ManufacturerRepo` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.manufacturer_repository.create(self._manufacturer_in, session=self.mock_session)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""
        manufacturer_in_data = self._manufacturer_in.model_dump()

        self.manufacturers_collection.insert_one.assert_called_once_with(
            manufacturer_in_data, session=self.mock_session
        )
        # This is the check for the newly inserted manufacturer get
        self.manufacturers_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._expected_manufacturer_out.id)}, session=self.mock_session
        )

        assert self._created_manufacturer == self._expected_manufacturer_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """
        self.manufacturers_collection.insert_one.assert_called_once_with(
            self._manufacturer_in.model_dump(), session=self.mock_session
        )
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a manufacturer."""

    def test_create(self):
        """Test creating a manufacturer."""
        self.mock_create(MANUFACTURER_IN_DATA_A)
        self.call_create()
        self.check_create_success()

    def test_create_with_duplicate_name(self):
        """Test creating a manufacturer with a duplicate manufacturer being found."""
        self.mock_create(MANUFACTURER_IN_DATA_A, raise_duplicate_key_error=True)
        self.call_create_expecting_error(DuplicateRecordError)
        self.check_create_failed_with_exception("Duplicate manufacturer found")


class GetDSL(ManufacturerRepoDSL):
    """Base class for `get` tests."""

    _obtained_manufacturer_id: str
    _expected_manufacturer_out: Optional[ManufacturerOut]
    _obtained_manufacturer_out: ManufacturerOut
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, manufacturer_id: str, manufacturer_in_data: Optional[dict]) -> None:
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param manufacturer_id: ID of the manufacturer to be obtained.
        :param manufacturer_in_data: Either `None` or a dictionary containing the manufacturer data as would be required
            for a `ManufacturerIn` database model (i.e. no ID or created and modified times required).
        """
        self._expected_manufacturer_out = (
            ManufacturerOut(**ManufacturerIn(**manufacturer_in_data).model_dump(), id=CustomObjectId(manufacturer_id))
            if manufacturer_in_data
            else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.manufacturers_collection,
            self._expected_manufacturer_out.model_dump() if self._expected_manufacturer_out else None,
        )

    def call_get(self, manufacturer_id: str) -> None:
        """
        Calls the `ManufacturerRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param manufacturer_id: ID of the manufacturer to be obtained.
        """
        self._obtained_manufacturer_id = manufacturer_id
        self._obtained_manufacturer_out = self.manufacturer_repository.get(manufacturer_id, session=self.mock_session)

    def call_get_expecting_error(self, manufacturer_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ManufacturerRepo` `get` method with the appropriate data from a prior call to `mock_get` while
        expecting an error to be raised.

        :param manufacturer_id: ID of the manufacturer to be obtained.
        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.manufacturer_repository.get(manufacturer_id, session=self.mock_session)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""
        self.manufacturers_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_manufacturer_id)}, session=self.mock_session
        )
        assert self._obtained_manufacturer_out == self._expected_manufacturer_out

    def check_get_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception with the correct
        message.

        :param message: Expected message of the raised exception.
        """
        self.manufacturers_collection.find_one.assert_not_called()
        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a manufacturer."""

    def test_get(self):
        """Test getting a system."""
        manufacturer_id = str(ObjectId())

        self.mock_get(manufacturer_id, MANUFACTURER_IN_DATA_A)
        self.call_get(manufacturer_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Testing getting a manufacturer with a non-existent ID."""
        manufacturer_id = str(ObjectId())

        self.mock_get(manufacturer_id, None)
        self.call_get(manufacturer_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting a manufacturer with an invalid ID."""
        manufacturer_id = "invalid-id"

        self.call_get_expecting_error(manufacturer_id, InvalidObjectIdError)
        self.check_get_failed_with_exception(f"Invalid ObjectId value '{manufacturer_id}'")


class ListDSL(ManufacturerRepoDSL):
    """Base class for `list` tests."""

    _expected_manufacturers_out: list[ManufacturerOut]
    _obtained_manufacturers_out: list[ManufacturerOut]

    def mock_list(self, manufacturers_in_data: list[dict]) -> None:
        """
        Mocks database methods appropriately to test the `list` repo method.

        :param manufacturers_in_data: List of dictionaries containing the manufacturer data as would be required for a
            `ManufacturerIn` database model (i.e. no ID or created and modified times required).
        """
        self._expected_manufacturers_out = [
            ManufacturerOut(**ManufacturerIn(**manufacturer_in_data).model_dump(), id=ObjectId())
            for manufacturer_in_data in manufacturers_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.manufacturers_collection,
            [manufacturer_out.model_dump() for manufacturer_out in self._expected_manufacturers_out],
        )

    def call_list(self) -> None:
        """Calls the `ManufacturerRepo` `list method` method."""
        self._obtained_manufacturers_out = self.manufacturer_repository.list(session=self.mock_session)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""
        self.manufacturers_collection.find.assert_called_once_with(session=self.mock_session)
        assert self._obtained_manufacturers_out == self._expected_manufacturers_out


class TestList(ListDSL):
    """Tests for listing manufacturers."""

    def test_list(self):
        """Test listing all manufacturers."""
        self.mock_list([MANUFACTURER_IN_DATA_A, MANUFACTURER_IN_DATA_B])
        self.call_list()
        self.check_list_success()

    def test_list_with_no_results(self):
        """Test listing all manufacturers returning no results."""
        self.mock_list([])
        self.call_list()
        self.check_list_success()


class UpdateDSL(ManufacturerRepoDSL):
    """Base class for `update` tests."""

    _manufacturer_in: ManufacturerIn
    _stored_manufacturer_out: Optional[ManufacturerOut]
    _expected_manufacturer_out: ManufacturerOut
    _updated_manufacturer_id: str
    _updated_manufacturer: ManufacturerOut
    _update_exception: pytest.ExceptionInfo

    def set_update_data(self, new_manufacturer_in_data: dict) -> None:
        """
        Assigns the update data to use during a call to `call_update`.

        :param new_manufacturer_in_data: New manufacturer data as would be required for a `ManufacturerIn` database
            model to supply to the `SystemRepo` `update` method.
        """
        self._manufacturer_in = ManufacturerIn(**new_manufacturer_in_data)

    def mock_update(
        self,
        manufacturer_id: str,
        new_manufacturer_in_data: dict,
        stored_manufacturer_in_data: Optional[dict],
        raise_duplicate_key_error: bool = False,
    ) -> None:
        """
        Mocks database methods appropriately to test the `update` repo method.

        :param manufacturer_id: ID of the manufacturer to be updated.
        :param new_manufacturer_in_data: Dictionary containing the new manufacturer data as would be required for a
            `ManufacturerIn` database model (i.e. no ID or created and modified times required).
        :param stored_manufacturer_in_data: Dictionary containing the data of the existing stored manufacturer as would
            be required for a `ManufacturerIn` database model.
        :param raise_duplicate_key_error: Whether a duplicate key error should be raised by the pymongo `update_one`
            method.
        """
        self.set_update_data(new_manufacturer_in_data)

        # Stored manufacturer
        self._stored_manufacturer_out = (
            ManufacturerOut(
                **ManufacturerIn(**stored_manufacturer_in_data).model_dump(), id=CustomObjectId(manufacturer_id)
            )
            if stored_manufacturer_in_data
            else None
        )

        RepositoryTestHelpers.mock_update_one(
            self.manufacturers_collection, raise_duplicate_key_error=raise_duplicate_key_error
        )

        # Final manufacturer after update
        self._expected_manufacturer_out = ManufacturerOut(
            **self._manufacturer_in.model_dump(), id=CustomObjectId(manufacturer_id)
        )
        RepositoryTestHelpers.mock_find_one(self.manufacturers_collection, self._expected_manufacturer_out.model_dump())

    def call_update(self, manufacturer_id: str) -> None:
        """
        Calls the `ManufacturerRepo` `update` method with the appropriate data from a prior call to `mock_update` (or
        `set_update_data`).

        :param manufacturer_id: ID of the manufacturer to be updated.
        """
        self._updated_manufacturer_id = manufacturer_id
        self._updated_manufacturer = self.manufacturer_repository.update(
            manufacturer_id, self._manufacturer_in, session=self.mock_session
        )

    def call_update_expecting_error(self, manufacturer_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ManufacturerRepo` `update` method with the appropriate data from a prior call to `mock_update` (or
        `set_update_data`) while expecting an error to be raised.

        :param manufacturer_id: ID of the manufacturer to be updated.
        :param error_type: Expected exception to be raised.
        """
        self._updated_manufacturer_id = manufacturer_id
        with pytest.raises(error_type) as exc:
            self.manufacturer_repository.update(manufacturer_id, self._manufacturer_in)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""
        self.manufacturers_collection.update_one.assert_called_once_with(
            {
                "_id": CustomObjectId(self._updated_manufacturer_id),
            },
            {
                "$set": self._manufacturer_in.model_dump(),
            },
            session=self.mock_session,
        )
        self.manufacturers_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._expected_manufacturer_out.id)}, session=self.mock_session
        )

        assert self._updated_manufacturer == self._expected_manufacturer_out

    def check_update_failed_with_exception(self, message: str, expecting_update_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        :param expecting_update_one_called: Whether the `update_one` method is expected to be called or not.
        """
        if expecting_update_one_called:
            self.manufacturers_collection.update_one.assert_called_once_with(
                {
                    "_id": CustomObjectId(self._updated_manufacturer_id),
                },
                {
                    "$set": self._manufacturer_in.model_dump(),
                },
                session=None,
            )
        else:
            self.manufacturers_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a manufacturer."""

    def test_update(self):
        """Test updating a manufacturer."""
        manufacturer_id = str(ObjectId())

        self.mock_update(manufacturer_id, MANUFACTURER_IN_DATA_A, MANUFACTURER_IN_DATA_B)
        self.call_update(manufacturer_id)
        self.check_update_success()

    def test_update_name_capitalisation(self):
        """Test updating the name capitalisation of a manufacturer."""
        manufacturer_id = str(ObjectId())
        new_name = "manufacturer a"

        self.mock_update(manufacturer_id, {**MANUFACTURER_IN_DATA_A, "name": new_name}, MANUFACTURER_IN_DATA_A)
        self.call_update(manufacturer_id)
        self.check_update_success()

    def test_update_name_to_duplicate(self):
        """Test updating the name of a manufacturer to one that is a duplicate."""
        manufacturer_id = str(ObjectId())
        duplicate_name = "Duplicate name"

        self.mock_update(
            manufacturer_id,
            {**MANUFACTURER_IN_DATA_A, "name": duplicate_name},
            MANUFACTURER_IN_DATA_A,
            raise_duplicate_key_error=True,
        )
        self.call_update_expecting_error(manufacturer_id, DuplicateRecordError)
        self.check_update_failed_with_exception("Duplicate manufacturer found", expecting_update_one_called=True)

    def test_update_with_invalid_id(self):
        """Test updating a manufacturer with an invalid ID."""
        manufacturer_id = "invalid-id"

        self.set_update_data(MANUFACTURER_IN_DATA_A)
        self.call_update_expecting_error(manufacturer_id, InvalidObjectIdError)
        self.check_update_failed_with_exception(f"Invalid ObjectId value '{manufacturer_id}'")


class DeleteDSL(ManufacturerRepoDSL):
    """Base class for `delete` tests."""

    _delete_manufacturer_id: str
    _delete_exception: pytest.ExceptionInfo
    _mock_catalogue_item_data: Optional[dict]

    def mock_delete(self, deleted_count: int, catalogue_item_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        :param catalogue_item_data: Dictionary containing a catalogue item's data (or `None`).
        """
        self.mock_is_manufacturer_in_catalogue_item(catalogue_item_data)
        RepositoryTestHelpers.mock_delete_one(self.manufacturers_collection, deleted_count)

    def call_delete(self, manufacturer_id: str) -> None:
        """
        Calls the `ManufacturerRepo` `delete` method with the appropriate data from a prior call to `mock_delete`.

        :param manufacturer_id: ID of the manufacturer to be deleted.
        """
        self._delete_manufacturer_id = manufacturer_id
        self.manufacturer_repository.delete(manufacturer_id, session=self.mock_session)

    def call_delete_expecting_error(self, manufacturer_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ManufacturerRepo` `delete` method with the appropriate data from a prior call to `mock_delete` while
        expecting an error to be raised.

        :param manufacturer_id: ID of the manufacturer to be deleted.
        :param error_type: Expected exception to be raised.
        """
        self._delete_manufacturer_id = manufacturer_id
        with pytest.raises(error_type) as exc:
            self.manufacturer_repository.delete(manufacturer_id, session=self.mock_session)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""
        self.check_is_manufacturer_in_catalogue_item_performed_expected_calls(self._delete_manufacturer_id)
        self.manufacturers_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_manufacturer_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """
        if not expecting_delete_one_called:
            self.manufacturers_collection.delete_one.assert_not_called()
        else:
            self.manufacturers_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_manufacturer_id)}, session=self.mock_session
            )

        assert str(self._delete_exception.value) == message

    def mock_is_manufacturer_in_catalogue_item(self, catalogue_item_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `_is_manufacturer_in_catalogue_item` repo method will be
        called.

        :param catalogue_item_data: Dictionary containing a catalogue item's data (or `None`).
        """
        self._mock_catalogue_item_data = catalogue_item_data
        RepositoryTestHelpers.mock_find_one(self.catalogue_items_collection, catalogue_item_data)

    def check_is_manufacturer_in_catalogue_item_performed_expected_calls(self, expected_manufacturer_id: str) -> None:
        """Checks that a call to `_is_manufacturer_in_catalogue_item` performed the expected method calls.

        :param expected_manufacturer_id: Expected manufacturer ID used in the database calls.
        """
        self.catalogue_items_collection.find_one.assert_called_once_with(
            {"manufacturer_id": CustomObjectId(expected_manufacturer_id)}, session=self.mock_session
        )


class TestDelete(DeleteDSL):
    """Tests for deleting a manufacturer."""

    def test_delete(self):
        """Test deleting a manufacturer."""
        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_when_part_of_catalogue_item(self):
        """Test deleting a manufacturer when it is part of a catalogue item."""
        manufacturer_id = str(ObjectId())

        self.mock_delete(
            deleted_count=1,
            catalogue_item_data=CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
        )
        self.call_delete_expecting_error(manufacturer_id, PartOfCatalogueItemError)
        self.check_delete_failed_with_exception(f"Manufacturer with ID '{manufacturer_id}' is part of a catalogue item")

    def test_delete_non_existent_id(self):
        """Test deleting a manufacturer with a non-existent ID."""
        manufacturer_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(manufacturer_id, MissingRecordError)
        self.check_delete_failed_with_exception(
            f"No manufacturer found with ID: {manufacturer_id}", expecting_delete_one_called=True
        )

    def test_delete_with_invalid_id(self):
        """Test deleting a manufacturer with an invalid ID."""
        manufacturer_id = "invalid-id"

        self.call_delete_expecting_error(manufacturer_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception(f"Invalid ObjectId value '{manufacturer_id}'")
