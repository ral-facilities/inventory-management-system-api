"""
Unit tests for the `CatalogueItemRepo` repository.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import (
    CATALOGUE_ITEM_IN_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
)
from test.unit.repositories.conftest import RepositoryTestHelpers
from test.unit.repositories.test_item import FULL_ITEM_INFO
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut, PropertyIn
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo


class CatalogueItemRepoDSL:
    """Base class for `CatalogueItemRepo` unit tests."""

    # pylint:disable=too-many-instance-attributes
    mock_database: Mock
    catalogue_item_repository: CatalogueItemRepo
    catalogue_items_collection: Mock
    items_collection: Mock

    mock_session = MagicMock()

    # Internal data for utility functions
    _mock_child_item_data: Optional[dict]

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures"""

        self.mock_database = database_mock
        self.catalogue_item_repository = CatalogueItemRepo(database_mock)
        self.catalogue_items_collection = database_mock.catalogue_items
        self.items_collection = database_mock.items

        self.mock_session = MagicMock()

    def mock_has_child_elements(self, child_item_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `has_child_elements` repo method will be called.

        :param child_item_data: Dictionary containing a child item's data (or `None`)
        """

        self._mock_child_item_data = child_item_data

        RepositoryTestHelpers.mock_find_one(self.items_collection, child_item_data)

    def check_has_child_elements_performed_expected_calls(self, expected_catalogue_item_id: str) -> None:
        """
        Checks that a call to `has_child_elements` performed the expected function calls.

        :param expected_catalogue_item_id: Expected `catalogue_item_id` used in the database calls.
        """

        self.items_collection.find_one.assert_called_once_with(
            {"catalogue_item_id": CustomObjectId(expected_catalogue_item_id)}, session=self.mock_session
        )


class CreateDSL(CatalogueItemRepoDSL):
    """Base class for `create` tests."""

    _catalogue_item_in: CatalogueItemIn
    _expected_catalogue_item_out: CatalogueItemOut
    _created_catalogue_item: CatalogueItemOut

    def mock_create(
        self,
        catalogue_item_in_data: dict,
    ) -> None:
        """Mocks database methods appropriately to test the `create` repo method.

        :param catalogue_item_in_data: Dictionary containing the catalogue item data as would be required for a
                                       `CatalogueItemIn` database model (i.e. no ID or created and modified times
                                       required).
        """

        inserted_catalogue_item_id = CustomObjectId(str(ObjectId()))

        # Pass through `CatalogueItemIn` first as need creation and modified times
        self._catalogue_item_in = CatalogueItemIn(**catalogue_item_in_data)

        self._expected_catalogue_item_out = CatalogueItemOut(
            **self._catalogue_item_in.model_dump(by_alias=True), id=inserted_catalogue_item_id
        )

        RepositoryTestHelpers.mock_insert_one(self.catalogue_items_collection, inserted_catalogue_item_id)
        RepositoryTestHelpers.mock_find_one(
            self.catalogue_items_collection,
            {**self._catalogue_item_in.model_dump(by_alias=True), "_id": inserted_catalogue_item_id},
        )

    def call_create(self) -> None:
        """Calls the `CatalogueItemRepo` `create` method with the appropriate data from a prior call to
        `mock_create`."""

        self._created_catalogue_item = self.catalogue_item_repository.create(
            self._catalogue_item_in, session=self.mock_session
        )

    def check_create_success(self):
        """Checks that a prior call to `call_create` worked as expected."""

        catalogue_item_in_data = self._catalogue_item_in.model_dump(by_alias=True)

        self.catalogue_items_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._expected_catalogue_item_out.id)}, session=self.mock_session
        )

        self.catalogue_items_collection.insert_one.assert_called_once_with(
            catalogue_item_in_data, session=self.mock_session
        )
        assert self._created_catalogue_item == self._expected_catalogue_item_out


class TestCreate(CreateDSL):
    """Tests for creating a catalogue item."""

    def test_create(self):
        """Test creating a catalogue item."""
        self.mock_create(CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_create()
        self.check_create_success()


class GetDSL(CatalogueItemRepoDSL):
    """Base class for `get` tests"""

    _obtained_catalogue_item_id: str
    _expected_catalogue_item_out: Optional[CatalogueItemOut]
    _obtained_catalogue_item: Optional[CatalogueItemOut]
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, catalogue_item_id: str, catalogue_item_in_data: Optional[dict]) -> None:
        """Mocks database methods appropriately to test the `get` repo method.

        :param catalogue_item_id: ID of the catalogue item to be obtained.
        :param catalogue_item_in_data: Either `None` or a Dictionary containing the catalogue item data as would
                                           be required for a `CatalogueItemIn` database model (i.e. No ID or created
                                           and modified times required).
        """

        self._expected_catalogue_item_out = (
            CatalogueItemOut(
                **CatalogueItemIn(**catalogue_item_in_data).model_dump(by_alias=True),
                id=CustomObjectId(catalogue_item_id),
            )
            if catalogue_item_in_data
            else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.catalogue_items_collection,
            self._expected_catalogue_item_out.model_dump() if self._expected_catalogue_item_out else None,
        )

    def call_get(self, catalogue_item_id: str) -> None:
        """
        Calls the `CatalogueItemRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param catalogue_item_id: ID of the catalogue item to be obtained.
        """

        self._obtained_catalogue_item_id = catalogue_item_id
        self._obtained_catalogue_item = self.catalogue_item_repository.get(catalogue_item_id, session=self.mock_session)

    def call_get_expecting_error(self, catalogue_item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemRepo` `get` method with the appropriate data from a prior call to `mock_get`
        while expecting an error to be raised.

        :param catalogue_item_id: ID of the catalogue item to be obtained.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_item_repository.get(catalogue_item_id)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.catalogue_items_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_catalogue_item_id)}, session=self.mock_session
        )
        assert self._obtained_catalogue_item == self._expected_catalogue_item_out

    def check_get_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_items_collection.find_one.assert_not_called()

        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a catalogue item."""

    def test_get(self):
        """Test getting a catalogue item."""

        catalogue_item_id = str(ObjectId())

        self.mock_get(catalogue_item_id, CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_get(catalogue_item_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Test getting a catalogue item with a non-existent ID."""

        catalogue_item_id = str(ObjectId())

        self.mock_get(catalogue_item_id, None)
        self.call_get(catalogue_item_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting a catalogue item with an invalid ID."""

        catalogue_item_id = "invalid-id"

        self.call_get_expecting_error(catalogue_item_id, InvalidObjectIdError)
        self.check_get_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class ListDSL(CatalogueItemRepoDSL):
    """Base class for `list` tests."""

    _expected_catalogue_items_out: list[CatalogueItemOut]
    _catalogue_category_id_filter: Optional[str]
    _obtained_catalogue_items_out: list[CatalogueItemOut]

    def mock_list(self, catalogue_items_in_data: list[dict]) -> None:
        """Mocks database methods appropriately to test the `list` repo method

        :param catalogue_items_in_data: List of dictionaries containing the catalogue item data as would be
                                             required for a `CatalogueItemIn` database model (i.e. no ID or created
                                             and modified times required)
        """

        self._expected_catalogue_items_out = [
            CatalogueItemOut(**CatalogueItemIn(**catalogue_item_in_data).model_dump(by_alias=True), id=ObjectId())
            for catalogue_item_in_data in catalogue_items_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.catalogue_items_collection,
            [catalogue_item_out.model_dump() for catalogue_item_out in self._expected_catalogue_items_out],
        )

    def call_list(self, catalogue_category_id: Optional[str]) -> None:
        """
        Calls the `CatalogueItemRepo` `list` method.

        :param catalogue_category_id: ID of the catalogue category to query by, or `None`.
        """

        self._catalogue_category_id_filter = catalogue_category_id

        self._obtained_catalogue_items_out = self.catalogue_item_repository.list(
            catalogue_category_id=catalogue_category_id, session=self.mock_session
        )

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        expected_query = {}
        if self._catalogue_category_id_filter:
            expected_query["catalogue_category_id"] = CustomObjectId(self._catalogue_category_id_filter)

        self.catalogue_items_collection.find.assert_called_once_with(expected_query, session=self.mock_session)

        assert self._obtained_catalogue_items_out == self._expected_catalogue_items_out


class TestList(ListDSL):
    """Tests for listing catalogue items."""

    def test_list(self):
        """Test listing all catalogue items."""

        self.mock_list(
            [
                CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
                CATALOGUE_ITEM_IN_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            ]
        )
        self.call_list(catalogue_category_id=None)
        self.check_list_success()

    def test_list_with_catalogue_category_id_filter(self):
        """Test listing all catalogue items with a given `catalogue_category_id`."""

        self.mock_list(
            [
                CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
                CATALOGUE_ITEM_IN_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            ]
        )
        self.call_list(catalogue_category_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_catalogue_category_id_with_no_results(self):
        """Test listing all catalogue categories with a `catalogue_category_id` filter returning no results."""

        self.mock_list([])
        self.call_list(catalogue_category_id=str(ObjectId()))
        self.check_list_success()


class UpdateDSL(CatalogueItemRepoDSL):
    """Base class for `update` tests."""

    _catalogue_item_in: CatalogueItemIn
    _expected_catalogue_item_out: CatalogueItemOut
    _updated_catalogue_item_id: str
    _updated_catalogue_item: CatalogueItemOut
    _update_exception: pytest.ExceptionInfo

    def set_update_data(self, new_catalogue_item_in_data: dict):
        """
        Assigns the update data to use during a call to `call_update`.

        :param new_catalogue_item_in_data: New catalogue item data as would be required for a `CatalogueItemIn` database
                                           model to supply to the `CatalogueItemRepo` `update` method.
        """
        self._catalogue_item_in = CatalogueItemIn(**new_catalogue_item_in_data)

    # pylint:disable=too-many-arguments
    def mock_update(
        self,
        catalogue_item_id: str,
        new_catalogue_item_in_data: dict,
    ) -> None:
        """
        Mocks database methods appropriately to test the `update` repo method.

        :param catalogue_item_id: ID of the catalogue item that will be updated.
        :param new_catalogue_item_in_data: Dictionary containing the new catalogue item data as would be required for a
                                           `CatalogueItemIn` database model (i.e. no ID or created and modified times
                                           required).
        """
        self.set_update_data(new_catalogue_item_in_data)

        # Final catalogue item after update
        self._expected_catalogue_item_out = CatalogueItemOut(
            **self._catalogue_item_in.model_dump(), id=CustomObjectId(catalogue_item_id)
        )
        RepositoryTestHelpers.mock_find_one(
            self.catalogue_items_collection, self._expected_catalogue_item_out.model_dump()
        )

    def call_update(self, catalogue_item_id: str) -> None:
        """
        Calls the `CatalogueItemRepo` `update` method with the appropriate data from a prior call to `mock_update`
        (or`set_update_data`).

        :param catalogue_item_id: ID of the catalogue item to be updated.
        """

        self._updated_catalogue_item_id = catalogue_item_id
        self._updated_catalogue_item = self.catalogue_item_repository.update(
            catalogue_item_id, self._catalogue_item_in, session=self.mock_session
        )

    def call_update_expecting_error(self, catalogue_item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemRepo` `update` method with the appropriate data from a prior call to `mock_update`
        (or `set_update_data`) while expecting an error to be raised.

        :param catalogue_item_id: ID of the catalogue item to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_item_repository.update(catalogue_item_id, self._catalogue_item_in)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        self.catalogue_items_collection.update_one.assert_called_once_with(
            {
                "_id": CustomObjectId(self._updated_catalogue_item_id),
            },
            {
                "$set": self._catalogue_item_in.model_dump(),
            },
            session=self.mock_session,
        )

        assert self._updated_catalogue_item == self._expected_catalogue_item_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_items_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue item."""

    def test_update(self):
        """Test updating a catalogue item."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_with_invalid_id(self):
        """Test updating a catalogue item with an invalid ID."""

        catalogue_item_id = "invalid-id"

        self.set_update_data(CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_update_expecting_error(catalogue_item_id, InvalidObjectIdError)
        self.check_update_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class DeleteDSL(CatalogueItemRepoDSL):
    """Base class for `delete` tests."""

    _delete_catalogue_item_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self,
        deleted_count: int,
        child_item_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        :param child_item_data: Dictionary containing a child item's data (or `None`).
        """

        self.mock_has_child_elements(child_item_data)
        RepositoryTestHelpers.mock_delete_one(self.catalogue_items_collection, deleted_count)

    def call_delete(self, catalogue_item_id: str) -> None:
        """
        Calls the `CatalogueItemRepo` `delete` method.

        :param catalogue_item_id: ID of the catalogue item to be deleted.
        """

        self._delete_catalogue_item_id = catalogue_item_id
        self.catalogue_item_repository.delete(catalogue_item_id, session=self.mock_session)

    def call_delete_expecting_error(self, catalogue_item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemRepo` `delete` method while expecting an error to be raised.

        :param catalogue_item_id: ID of the catalogue item to be deleted.
        :param error_type: Expected exception to be raised.
        """

        self._delete_catalogue_item_id = catalogue_item_id
        with pytest.raises(error_type) as exc:
            self.catalogue_item_repository.delete(catalogue_item_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.check_has_child_elements_performed_expected_calls(self._delete_catalogue_item_id)
        self.catalogue_items_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_catalogue_item_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """

        if not expecting_delete_one_called:
            self.catalogue_items_collection.delete_one.assert_not_called()
        else:
            self.catalogue_items_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_catalogue_item_id)}, session=None
            )

        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue item."""

    def test_delete(self):
        """Test deleting a catalogue item."""

        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_child_item(self):
        """Test deleting a catalogue item when it has a child item."""

        catalogue_item_id = str(ObjectId())

        # pylint:disable=fixme
        # TODO: Replace FULL_ITEM_INFO once items has been refactored
        self.mock_delete(deleted_count=1, child_item_data=FULL_ITEM_INFO)
        self.call_delete_expecting_error(catalogue_item_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(
            f"Catalogue item with ID {catalogue_item_id} has child elements and cannot be deleted"
        )

    def test_delete_non_existent_id(self):
        """Test deleting a catalogue item with a non-existent ID."""

        catalogue_item_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(catalogue_item_id, MissingRecordError)
        self.check_delete_failed_with_exception(
            f"No catalogue item found with ID: {catalogue_item_id}", expecting_delete_one_called=True
        )

    def test_delete_invalid_id(self):
        """Test deleting a catalogue item with an invalid ID."""

        catalogue_item_id = "invalid-id"

        self.call_delete_expecting_error(catalogue_item_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class HasChildElementsDSL(CatalogueItemRepoDSL):
    """Base class for `has_child_elements` tests"""

    _has_child_elements_catalogue_item_id: str
    _has_child_elements_result: bool

    def call_has_child_elements(self, catalogue_item_id: str) -> None:
        """Calls the `CatalogueItemRepo` `has_child_elements` method.

        :param catalogue_item_id: ID of the catalogue item to check.
        """

        self._has_child_elements_catalogue_item_id = catalogue_item_id
        self._has_child_elements_result = self.catalogue_item_repository.has_child_elements(
            CustomObjectId(catalogue_item_id), session=self.mock_session
        )

    def check_has_child_elements_success(self, expected_result: bool) -> None:
        """Checks that a prior call to `call_has_child_elements` worked as expected

        :param expected_result: The expected result returned by `has_child_elements`
        """

        self.check_has_child_elements_performed_expected_calls(self._has_child_elements_catalogue_item_id)

        assert self._has_child_elements_result == expected_result


class TestHasChildElements(HasChildElementsDSL):
    """Tests for `has_child_elements`."""

    def test_has_child_elements_with_no_children(self):
        """Test `has_child_elements` when there are no child items."""

        self.mock_has_child_elements(child_item_data=None)
        self.call_has_child_elements(catalogue_item_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=False)

    def test_has_child_elements_with_child_item(self):
        """Test `has_child_elements` when there is a child item."""

        # pylint:disable=fixme
        # TODO: Replace FULL_ITEM_INFO once items has been refactored
        self.mock_has_child_elements(
            child_item_data=FULL_ITEM_INFO,
        )
        self.call_has_child_elements(catalogue_item_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=True)


class ListIDsDSL(CatalogueItemRepoDSL):
    """Base class for `list_ids` tests"""

    _list_ids_catalogue_category_id: str
    _list_ids_result: bool

    def call_list_ids(self, catalogue_category_id: str) -> None:
        """Calls the `CatalogueItemRepo` `list_ids` method.

        :param catalogue_category_id: ID of the catalogue category.
        """

        self._list_ids_catalogue_category_id = catalogue_category_id
        self._list_ids_result = self.catalogue_item_repository.list_ids(
            catalogue_category_id, session=self.mock_session
        )

    def check_list_ids_success(self) -> None:
        """Checks that a prior call to `call_list_ids` worked as expected

        :param expected_result: The expected result returned by `list_ids`
        """

        self.catalogue_items_collection.find.assert_called_once_with(
            {"catalogue_category_id": CustomObjectId(self._list_ids_catalogue_category_id)},
            {"_id": 1},
            session=self.mock_session,
        )
        self.catalogue_items_collection.find.return_value.distinct.assert_called_once_with("_id")

        assert self._list_ids_result == self.catalogue_items_collection.find.return_value.distinct.return_value


class TestListIDs(ListIDsDSL):
    """Tests for `list_ids`."""

    def test_list_ids(self):
        """Test `list_ids`."""

        self.call_list_ids(str(ObjectId()))
        self.check_list_ids_success()


class InsertPropertyToAllMatchingDSL(CatalogueItemRepoDSL):
    """Base class for `insert_property_to_all_matching` tests"""

    _mock_datetime: Mock
    _insert_property_to_all_matching_catalogue_category_id: str
    _property_in: PropertyIn

    @pytest.fixture(autouse=True)
    def setup_insert_property_to_all_matching_dsl(self):
        """Setup fixtures"""

        with patch("inventory_management_system_api.repositories.catalogue_item.datetime") as mock_datetime:
            self._mock_datetime = mock_datetime
            yield

    def call_insert_property_to_all_matching(self, catalogue_category_id: str, property_data: dict) -> None:
        """Calls the `CatalogueItemRepo` `insert_property_to_all_matching` method.

        :param catalogue_category_id: ID of the catalogue category.
        :param property_data: Data of the property to insert as would be required for a `PropertyPostSchema` schema but
                        without an `id`.
        """

        self._property_in = PropertyIn(**property_data, id=str(ObjectId()))

        self._insert_property_to_all_matching_catalogue_category_id = catalogue_category_id
        self.catalogue_item_repository.insert_property_to_all_matching(
            catalogue_category_id, self._property_in, session=self.mock_session
        )

    def check_insert_property_to_all_matching_success(self) -> None:
        """Checks that a prior call to `call_insert_property_to_all_matching` worked as expected"""

        self.catalogue_items_collection.update_many.assert_called_once_with(
            {"catalogue_category_id": CustomObjectId(self._insert_property_to_all_matching_catalogue_category_id)},
            {
                "$push": {"properties": self._property_in.model_dump(by_alias=True)},
                "$set": {"modified_time": self._mock_datetime.now.return_value},
            },
            session=self.mock_session,
        )


class TestInsertPropertyToAllMatching(InsertPropertyToAllMatchingDSL):
    """Tests for `insert_property_to_all_matching`."""

    def test_insert_property_to_all_matching(self):
        """Test `insert_property_to_all_matching`."""

        self.call_insert_property_to_all_matching(str(ObjectId()), PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE)
        self.check_insert_property_to_all_matching_success()


class UpdateNamesOfAllPropertiesWithIDDSL(InsertPropertyToAllMatchingDSL):
    """Base class for `update_names_of_all_properties_with_id` tests"""

    _update_names_of_all_properties_with_id_property_id: str
    _update_names_of_all_properties_with_id_new_property_name: str

    def call_update_names_of_all_properties_with_id(self, property_id: str, new_property_name: str) -> None:
        """Calls the `CatalogueItemRepo` `update_names_of_all_properties_with_id` method.

        :param property_id: ID of the property.
        :param new_property_name: New property name.
        """

        self._update_names_of_all_properties_with_id_property_id = property_id
        self._update_names_of_all_properties_with_id_new_property_name = new_property_name
        self.catalogue_item_repository.update_names_of_all_properties_with_id(
            property_id, new_property_name, session=self.mock_session
        )

    def check_update_names_of_all_properties_with_id(self) -> None:
        """Checks that a prior call to `update_names_of_all_properties_with_id` worked as expected"""

        self.catalogue_items_collection.update_many.assert_called_once_with(
            {"properties._id": CustomObjectId(self._update_names_of_all_properties_with_id_property_id)},
            {
                "$set": {
                    "properties.$[elem].name": self._update_names_of_all_properties_with_id_new_property_name,
                    "modified_time": self._mock_datetime.now.return_value,
                }
            },
            array_filters=[{"elem._id": CustomObjectId(self._update_names_of_all_properties_with_id_property_id)}],
            session=self.mock_session,
        )


class TestUpdateNamesOfAllPropertiesWithID(UpdateNamesOfAllPropertiesWithIDDSL):
    """Tests for `update_names_of_all_properties_with_id`."""

    def test_update_names_of_all_properties_with_id(self):
        """Test `update_names_of_all_properties_with_id`."""

        self.call_update_names_of_all_properties_with_id(str(ObjectId()), "New name")
        self.check_update_names_of_all_properties_with_id()
