"""
Unit tests for the `ItemRepo` repository.
"""

from test.mock_data import (
    ITEM_IN_DATA_ALL_VALUES_NO_PROPERTIES,
    ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
    PROPERTY_DATA_STRING_MANDATORY_TEXT,
    SYSTEM_IN_DATA_NO_PARENT_A,
)
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.models.item import ItemIn, ItemOut
from inventory_management_system_api.models.system import SystemIn
from inventory_management_system_api.repositories.item import ItemRepo


class ItemRepoDSL:
    """Base class for `ItemRepo` unit tests."""

    mock_database: Mock
    item_repository: ItemRepo
    items_collection: Mock
    systems_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures"""

        self.mock_database = database_mock
        self.item_repository = ItemRepo(database_mock)
        self.items_collection = database_mock.items
        self.systems_collection = database_mock.systems


class CreateDSL(ItemRepoDSL):
    """Base class for `create` tests."""

    _item_in: ItemIn
    _expected_item_out: ItemOut
    _created_item: ItemOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        item_in_data: dict,
        system_in_data: Optional[dict] = None,
    ) -> None:
        """Mocks database methods appropriately to test the `create` repo method.

        :param item_in_data: Dictionary containing the item data as would be required for a `ItemIn` database model
                             (i.e. no ID or created and modified times required).
        :param system_in_data: Either `None` or a dictionary system data as would be required for a `SystemIn` database
                               model.
        """

        inserted_item_id = CustomObjectId(str(ObjectId()))

        # Pass through `ItemIn` first as need creation and modified times
        self._item_in = ItemIn(**item_in_data)

        self._expected_item_out = ItemOut(**self._item_in.model_dump(by_alias=True), id=inserted_item_id)

        RepositoryTestHelpers.mock_find_one(
            self.systems_collection,
            (
                {
                    **SystemIn(**system_in_data).model_dump(),
                    "_id": ObjectId(),
                }
                if system_in_data
                else None
            ),
        )

        RepositoryTestHelpers.mock_insert_one(self.items_collection, inserted_item_id)
        RepositoryTestHelpers.mock_find_one(
            self.items_collection,
            {**self._item_in.model_dump(by_alias=True), "_id": inserted_item_id},
        )

    def call_create(self) -> None:
        """Calls the `ItemRepo` `create` method with the appropriate data from a prior call to `mock_create`."""

        self._created_item = self.item_repository.create(self._item_in, session=self.mock_session)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemRepo` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_repository.create(self._item_in)
        self._create_exception = exc

    def check_create_success(self):
        """Checks that a prior call to `call_create` worked as expected."""

        item_in_data = self._item_in.model_dump(by_alias=True)

        self.systems_collection.find_one.assert_called_with({"_id": self._item_in.system_id}, session=self.mock_session)

        self.items_collection.insert_one.assert_called_once_with(item_in_data, session=self.mock_session)
        self.items_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._expected_item_out.id)}, session=self.mock_session
        )

        assert self._created_item == self._expected_item_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.items_collection.insert_one.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating an item."""

    def test_create(self):
        """Test creating an item."""

        self.mock_create(ITEM_IN_DATA_REQUIRED_VALUES_ONLY, system_in_data=SYSTEM_IN_DATA_NO_PARENT_A)
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_system_id(self):
        """Test creating an item with a non-existent system ID."""

        self.mock_create(ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No system found with ID: {ITEM_IN_DATA_REQUIRED_VALUES_ONLY["system_id"]}"
        )


class GetDSL(ItemRepoDSL):
    """Base class for `get` tests"""

    _obtained_item_id: str
    _expected_item_out: Optional[ItemOut]
    _obtained_item: Optional[ItemOut]
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, item_id: str, item_in_data: Optional[dict]) -> None:
        """Mocks database methods appropriately to test the `get` repo method.

        :param item_id: ID of the item to be obtained.
        :param item_in_data: Either `None` or a Dictionary containing the item data as would be required for a `ItemIn`
                             database model (i.e. No ID or created and modified times required).
        """

        self._expected_item_out = (
            ItemOut(
                **ItemIn(**item_in_data).model_dump(by_alias=True),
                id=CustomObjectId(item_id),
            )
            if item_in_data
            else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.items_collection,
            self._expected_item_out.model_dump() if self._expected_item_out else None,
        )

    def call_get(self, item_id: str) -> None:
        """
        Calls the `ItemRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param item_id: ID of the item to be obtained.
        """

        self._obtained_item_id = item_id
        self._obtained_item = self.item_repository.get(item_id, session=self.mock_session)

    def call_get_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemRepo` `get` method with the appropriate data from a prior call to `mock_get` while expecting an
        error to be raised.

        :param item_id: ID of the item to be obtained.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_repository.get(item_id)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.items_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_item_id)}, session=self.mock_session
        )
        assert self._obtained_item == self._expected_item_out

    def check_get_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.items_collection.find_one.assert_not_called()

        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting an item."""

    def test_get(self):
        """Test getting an item."""

        item_id = str(ObjectId())

        self.mock_get(item_id, ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_get(item_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Test getting an item with a non-existent ID."""

        item_id = str(ObjectId())

        self.mock_get(item_id, None)
        self.call_get(item_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting an item with an invalid ID."""

        item_id = "invalid-id"

        self.call_get_expecting_error(item_id, InvalidObjectIdError)
        self.check_get_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class ListDSL(ItemRepoDSL):
    """Base class for `list` tests."""

    _expected_items_out: list[ItemOut]
    _system_id_filter: Optional[str]
    _catalogue_item_id_filter: Optional[str]
    _obtained_items_out: list[ItemOut]

    def mock_list(self, items_in_data: list[dict]) -> None:
        """Mocks database methods appropriately to test the `list` repo method

        :param items_in_data: List of dictionaries containing the item data as would be required for a `ItemIn` database
                              model (i.e. no ID or created and modified times required)
        """

        self._expected_items_out = [
            ItemOut(**ItemIn(**item_in_data).model_dump(by_alias=True), id=ObjectId()) for item_in_data in items_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.items_collection, [item_out.model_dump() for item_out in self._expected_items_out]
        )

    def call_list(self, system_id: Optional[str], catalogue_item_id: Optional[str]) -> None:
        """
        Calls the `ItemRepo` `list` method.

        :param system_id: ID of the system to query by, or `None`.
        :param catalogue_item_id: ID of the catalogue item to query by, or `None`.
        """

        self._system_id_filter = system_id
        self._catalogue_item_id_filter = catalogue_item_id

        self._obtained_items_out = self.item_repository.list(
            system_id=system_id, catalogue_item_id=catalogue_item_id, session=self.mock_session
        )

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        expected_query = {}
        if self._system_id_filter:
            expected_query["system_id"] = CustomObjectId(self._system_id_filter)
        if self._catalogue_item_id_filter:
            expected_query["catalogue_item_id"] = CustomObjectId(self._catalogue_item_id_filter)

        self.items_collection.find.assert_called_once_with(expected_query, session=self.mock_session)

        assert self._obtained_items_out == self._expected_items_out


class TestList(ListDSL):
    """Tests for listing items."""

    def test_list(self):
        """Test listing all items."""

        self.mock_list([ITEM_IN_DATA_REQUIRED_VALUES_ONLY, ITEM_IN_DATA_ALL_VALUES_NO_PROPERTIES])
        self.call_list(system_id=None, catalogue_item_id=None)
        self.check_list_success()

    def test_list_with_system_id_filter(self):
        """Test listing all items with a given `system_id`."""

        self.mock_list([ITEM_IN_DATA_REQUIRED_VALUES_ONLY, ITEM_IN_DATA_ALL_VALUES_NO_PROPERTIES])
        self.call_list(system_id=str(ObjectId()), catalogue_item_id=None)
        self.check_list_success()

    def test_list_with_catalogue_category_id_filter(self):
        """Test listing all items with a given `catalogue_category_id`."""

        self.mock_list([ITEM_IN_DATA_REQUIRED_VALUES_ONLY, ITEM_IN_DATA_ALL_VALUES_NO_PROPERTIES])
        self.call_list(system_id=None, catalogue_item_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_system_id_and_catalogue_category_id_with_no_results(self):
        """Test listing all items with a `system_id` and `catalogue_category_id` filter returning no results."""

        self.mock_list([])
        self.call_list(system_id=str(ObjectId()), catalogue_item_id=str(ObjectId()))
        self.check_list_success()


class UpdateDSL(ItemRepoDSL):
    """Base class for `update` tests."""

    _item_in: ItemIn
    _expected_item_out: ItemOut
    _updated_item_id: str
    _updated_item: ItemOut
    _update_exception: pytest.ExceptionInfo

    def set_update_data(self, new_item_in_data: dict):
        """
        Assigns the update data to use during a call to `call_update`.

        :param new_item_in_data: New item data as would be required for a `ItemIn` database model to supply to the
                                 `ItemRepo` `update` method.
        """
        self._item_in = ItemIn(**new_item_in_data)

    def mock_update(
        self,
        item_id: str,
        new_item_in_data: dict,
    ) -> None:
        """
        Mocks database methods appropriately to test the `update` repo method.

        :param item_id: ID of the item that will be updated.
        :param new_item_in_data: Dictionary containing the new item data as would be required for a `ItemIn` database
                                 model (i.e. no ID or created and modified times required).
        """
        self.set_update_data(new_item_in_data)

        # Final item after update
        self._expected_item_out = ItemOut(**self._item_in.model_dump(), id=CustomObjectId(item_id))
        RepositoryTestHelpers.mock_find_one(self.items_collection, self._expected_item_out.model_dump(by_alias=True))

    def call_update(self, item_id: str) -> None:
        """
        Calls the `ItemRepo` `update` method with the appropriate data from a prior call to `mock_update`
        (or `set_update_data`).

        :param item_id: ID of the item to be updated.
        """

        self._updated_item_id = item_id
        self._updated_item = self.item_repository.update(item_id, self._item_in, session=self.mock_session)

    def call_update_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemRepo` `update` method with the appropriate data from a prior call to `mock_update`
        (or `set_update_data`) while expecting an error to be raised.

        :param item_id: ID of the item to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_repository.update(item_id, self._item_in)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        self.items_collection.update_one.assert_called_once_with(
            {
                "_id": CustomObjectId(self._updated_item_id),
            },
            {
                "$set": self._item_in.model_dump(by_alias=True),
            },
            session=self.mock_session,
        )

        assert self._updated_item == self._expected_item_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.items_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating an item."""

    def test_update(self):
        """Test updating an item."""

        item_id = str(ObjectId())

        self.mock_update(item_id, ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_update(item_id)
        self.check_update_success()

    def test_update_with_invalid_id(self):
        """Test updating an item with an invalid ID."""

        item_id = "invalid-id"

        self.set_update_data(ITEM_IN_DATA_REQUIRED_VALUES_ONLY)
        self.call_update_expecting_error(item_id, InvalidObjectIdError)
        self.check_update_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class DeleteDSL(ItemRepoDSL):
    """Base class for `delete` tests."""

    _delete_item_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self,
        deleted_count: int,
    ) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        """

        RepositoryTestHelpers.mock_delete_one(self.items_collection, deleted_count)

    def call_delete(self, item_id: str) -> None:
        """
        Calls the `ItemRepo` `delete` method.

        :param item_id: ID of the item to be deleted.
        """

        self._delete_item_id = item_id
        self.item_repository.delete(item_id, session=self.mock_session)

    def call_delete_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemRepo` `delete` method while expecting an error to be raised.

        :param item_id: ID of the item to be deleted.
        :param error_type: Expected exception to be raised.
        """

        self._delete_item_id = item_id
        with pytest.raises(error_type) as exc:
            self.item_repository.delete(item_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.items_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_item_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """

        if not expecting_delete_one_called:
            self.items_collection.delete_one.assert_not_called()
        else:
            self.items_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_item_id)}, session=None
            )

        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting an item."""

    def test_delete(self):
        """Test deleting an item."""

        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_non_existent_id(self):
        """Test deleting an item with a non-existent ID."""

        item_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(item_id, MissingRecordError)
        self.check_delete_failed_with_exception(f"No item found with ID: {item_id}", expecting_delete_one_called=True)

    def test_delete_invalid_id(self):
        """Test deleting an item with an invalid ID."""

        item_id = "invalid-id"

        self.call_delete_expecting_error(item_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class InsertPropertyToAllInDSL(ItemRepoDSL):
    """Base class for `insert_property_to_all_in` tests"""

    _mock_datetime: Mock
    _insert_property_to_all_in_catalogue_item_ids: list[ObjectId]
    _property_in: PropertyIn

    @pytest.fixture(autouse=True)
    def setup_insert_property_to_all_in_dsl(self):
        """Setup fixtures"""

        with patch("inventory_management_system_api.repositories.item.datetime") as mock_datetime:
            self._mock_datetime = mock_datetime
            yield

    def call_insert_property_to_all_in(self, catalogue_item_ids: list[ObjectId], property_data: dict) -> None:
        """Calls the `ItemRepo` `insert_property_to_all_in` method.

        :param catalogue_item_ids: List of IDs of the catalogue items.
        :param property_data: Data of the property to insert as would be required for a `PropertyPostSchema` schema but
                              without an `id`.
        """

        self._property_in = PropertyIn(**property_data, id=str(ObjectId()))

        self._insert_property_to_all_in_catalogue_item_ids = catalogue_item_ids
        self.item_repository.insert_property_to_all_in(catalogue_item_ids, self._property_in, session=self.mock_session)

    def check_insert_property_to_all_in_success(self) -> None:
        """Checks that a prior call to `call_insert_property_to_all_in` worked as expected"""

        self.items_collection.update_many.assert_called_once_with(
            {"catalogue_item_id": {"$in": self._insert_property_to_all_in_catalogue_item_ids}},
            {
                "$push": {"properties": self._property_in.model_dump(by_alias=True)},
                "$set": {"modified_time": self._mock_datetime.now.return_value},
            },
            session=self.mock_session,
        )


class TestInsertPropertyToAllIn(InsertPropertyToAllInDSL):
    """Tests for `insert_property_to_all_in`."""

    def test_insert_property_to_all_matching(self):
        """Test `insert_property_to_all_in`."""

        self.call_insert_property_to_all_in([ObjectId(), ObjectId()], PROPERTY_DATA_STRING_MANDATORY_TEXT)
        self.check_insert_property_to_all_in_success()


class UpdateNamesOfAllPropertiesWithIDDSL(InsertPropertyToAllInDSL):
    """Base class for `update_names_of_all_properties_with_id` tests"""

    _update_names_of_all_properties_with_id_property_id: str
    _update_names_of_all_properties_with_id_new_property_name: str

    def call_update_names_of_all_properties_with_id(self, property_id: str, new_property_name: str) -> None:
        """Calls the `ItemRepo` `update_names_of_all_properties_with_id` method.

        :param property_id: ID of the property.
        :param new_property_name: New property name.
        """

        self._update_names_of_all_properties_with_id_property_id = property_id
        self._update_names_of_all_properties_with_id_new_property_name = new_property_name
        self.item_repository.update_names_of_all_properties_with_id(
            property_id, new_property_name, session=self.mock_session
        )

    def check_update_names_of_all_properties_with_id(self) -> None:
        """Checks that a prior call to `update_names_of_all_properties_with_id` worked as expected"""

        self.items_collection.update_many.assert_called_once_with(
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


class CountInCatalogueItemWithSystemTypeOneOfDSL(ItemRepoDSL):
    """Base class for `count_in_catalogue_item_with_system_type_once_of` tests."""

    _catalogue_item_id: str
    _system_type_ids: list[str]
    _expected_count: Optional[None]
    _obtained_count: int

    def mock_count_in_catalogue_item_with_system_type_one_of(self, count: Optional[int]):
        """
        Mocks database methods appropriately to test the `count_in_catalogue_item_with_system_type_one_of` repo
        method.

        :param count: Either `None` (if there are no results from the aggregate query) or the count as should be
                      returned from the function.
        """

        self._expected_count = 0 if count is None else count
        self.items_collection.aggregate.return_value = [] if count is None else [{"matching_items": count}]

    def call_count_in_catalogue_item_with_system_type_one_of(
        self, catalogue_item_id: str, system_type_ids: list[str]
    ) -> None:
        """Calls the `ItemRepo` `count_in_catalogue_item_with_system_type_one_of` method.

        :param catalogue_item_id: ID of the catalogue item for which items should be counted.
        :param system_type_ids: List of system type IDs which should be included in the count.
        """

        self._catalogue_item_id = catalogue_item_id
        self._system_type_ids = system_type_ids
        self._obtained_count = self.item_repository.count_in_catalogue_item_with_system_type_one_of(
            catalogue_item_id, system_type_ids, session=self.mock_session
        )

    def check_count_in_catalogue_item_with_system_type_one_of(self) -> None:
        """Checks that a prior call to `count_in_catalogue_item_with_system_type_one_of` worked as expected."""

        self.items_collection.aggregate.assert_called_once_with(
            [
                # Obtain a list of items with the same catalogue item ID
                {"$match": {"catalogue_item_id": self._catalogue_item_id}},
                {"$lookup": {"from": "systems", "localField": "system_id", "foreignField": "_id", "as": "system"}},
                {"$match": {"system.type_id": {"$in": self._system_type_ids}}},
                {"$count": "matching_items"},
            ],
            session=self.mock_session,
        )
        assert self._expected_count == self._obtained_count


class TestCountInCatalogueItemWithSystemTypeOneOf(CountInCatalogueItemWithSystemTypeOneOfDSL):
    """Tests for `count_in_catalogue_item_with_system_type_one_of`."""

    def test_count_in_catalogue_item_with_system_type_one_of(self):
        """Test `count_in_catalogue_item_with_system_type_one_of`."""

        self.mock_count_in_catalogue_item_with_system_type_one_of(42)
        self.call_count_in_catalogue_item_with_system_type_one_of(ObjectId(), [ObjectId(), ObjectId()])
        self.check_count_in_catalogue_item_with_system_type_one_of()

    def test_count_in_catalogue_item_with_system_type_one_of_when_no_result(self):
        """Test `count_in_catalogue_item_with_system_type_one_of` when there is no result."""

        self.mock_count_in_catalogue_item_with_system_type_one_of(None)
        self.call_count_in_catalogue_item_with_system_type_one_of(ObjectId(), [ObjectId(), ObjectId()])
        self.check_count_in_catalogue_item_with_system_type_one_of()
