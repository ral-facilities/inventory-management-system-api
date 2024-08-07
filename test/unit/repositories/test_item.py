"""
Unit tests for the `ItemRepo` repository.
"""

from test.mock_data import ITEM_IN_DATA_REQUIRED_VALUES_ONLY, SYSTEM_IN_DATA_NO_PARENT_A
from test.unit.repositories.conftest import RepositoryTestHelpers
from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME, MOCK_PROPERTY_A_INFO
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

        self.mock_session = MagicMock()


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

        :param item_in_data: Dictionary containing the catalogue item data as would be required for a `ItemIn` database
                             model (i.e. no ID or created and modified times required).
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

        self.items_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._expected_item_out.id)}, session=self.mock_session
        )

        # TODO: Move this above line above - final find is after the insert... - Same for other repo tests...
        self.items_collection.insert_one.assert_called_once_with(item_in_data, session=self.mock_session)
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


# FULL_ITEM_INFO = {
#     "purchase_order_number": None,
#     "is_defective": False,
#     "warranty_end_date": "2015-11-15T23:59:59Z",
#     "asset_number": None,
#     "serial_number": "xyz123",
#     "delivered_date": "2012-12-05T12:00:00Z",
#     "notes": "Test notes",
#     "properties": [{"id": str(ObjectId()), "name": "Property A", "value": 21, "unit": "mm"}],
# }
# # pylint: enable=duplicate-code


# def test_delete(test_helpers, database_mock, item_repository):
#     """
#     Test deleting an item.

#     Verify that the `delete` method properly handles the deletion of an item by ID.
#     """
#     item_id = str(ObjectId())
#     session = MagicMock()

#     # Mock `delete_one` to return that one document has been deleted
#     test_helpers.mock_delete_one(database_mock.items, 1)

#     item_repository.delete(item_id, session=session)

#     database_mock.items.delete_one.assert_called_once_with({"_id": CustomObjectId(item_id)}, session=session)


# def test_delete_with_invalid_id(item_repository):
#     """
#     Test deleting an item with an invalid ID.

#     Verify that the `delete` method properly handles the deletion of an item with an invalid ID.
#     """
#     with pytest.raises(InvalidObjectIdError) as exc:
#         item_repository.delete("invalid")
#     assert str(exc.value) == "Invalid ObjectId value 'invalid'"


# def test_delete_with_non_existent_id(test_helpers, database_mock, item_repository):
#     """
#     Test deleting an item with an invalid ID.

#     Verify that the `delete` method properly handles the deletion of an item with a non-existent ID.
#     """
#     item_id = str(ObjectId())

#     # Mock `delete_one` to return that no document has been deleted
#     test_helpers.mock_delete_one(database_mock.items, 0)

#     with pytest.raises(MissingRecordError) as exc:
#         item_repository.delete(item_id)
#     assert str(exc.value) == f"No item found with ID: {item_id}"
#     database_mock.items.delete_one.assert_called_once_with({"_id": CustomObjectId(item_id)}, session=None)


# def test_list(test_helpers, database_mock, item_repository):
#     """
#     Test getting items.

#     Verify that the `list` method properly handles the retrieval of items
#     """
#     # pylint: disable=duplicate-code
#     item_a = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )

#     item_b = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )
#     # pylint: enable=duplicate-code
#     session = MagicMock()

#     # Mock `find` to return a list of item documents
#     test_helpers.mock_find(
#         database_mock.items,
#         [
#             {
#                 **FULL_ITEM_INFO,
#                 **MOCK_CREATED_MODIFIED_TIME,
#                 "_id": CustomObjectId(item_a.id),
#                 "catalogue_item_id": CustomObjectId(item_a.catalogue_item_id),
#                 "system_id": CustomObjectId(item_a.system_id),
#                 "usage_status_id": CustomObjectId(item_a.usage_status_id),
#                 "usage_status": item_a.usage_status,
#             },
#             {
#                 **FULL_ITEM_INFO,
#                 **MOCK_CREATED_MODIFIED_TIME,
#                 "_id": CustomObjectId(item_b.id),
#                 "catalogue_item_id": CustomObjectId(item_b.catalogue_item_id),
#                 "system_id": CustomObjectId(item_b.system_id),
#                 "usage_status_id": CustomObjectId(item_b.usage_status_id),
#                 "usage_status": item_b.usage_status,
#             },
#         ],
#     )

#     retrieved_item = item_repository.list(None, None, session=session)

#     database_mock.items.find.assert_called_once_with({}, session=session)
#     assert retrieved_item == [item_a, item_b]


# def test_list_with_system_id_filter(test_helpers, database_mock, item_repository):
#     """
#     Test getting items based on the provided system ID filter.

#     Verify that the `list` method properly handles the retrieval of items based on
#     the provided system ID filter
#     """
#     # pylint: disable=duplicate-code
#     item = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )
#     session = MagicMock()
#     # pylint: enable=duplicate-code

#     # Mock `find` to return a list of item documents
#     test_helpers.mock_find(
#         database_mock.items,
#         [
#             {
#                 **FULL_ITEM_INFO,
#                 **MOCK_CREATED_MODIFIED_TIME,
#                 "_id": CustomObjectId(item.id),
#                 "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
#                 "system_id": CustomObjectId(item.system_id),
#                 "usage_status_id": CustomObjectId(item.usage_status_id),
#                 "usage_status": item.usage_status,
#             }
#         ],
#     )

#     retrieved_item = item_repository.list(item.system_id, None, session=session)

#     database_mock.items.find.assert_called_once_with({"system_id": CustomObjectId(item.system_id)}, session=session)
#     assert retrieved_item == [item]


# def test_list_with_system_id_filter_no_matching_results(test_helpers, database_mock, item_repository):
#     """
#     Test getting items based on the provided system ID filter when there are no matching results in
#     the database.

#     Verify the `list` method properly handles the retrieval of items based on the provided
#     system ID filter
#     """
#     session = MagicMock()

#     # Mock `find` to return an empty list of item documents
#     test_helpers.mock_find(database_mock.items, [])

#     system_id = str(ObjectId())
#     retrieved_items = item_repository.list(system_id, None, session=session)

#     database_mock.items.find.assert_called_once_with({"system_id": CustomObjectId(system_id)}, session=session)
#     assert retrieved_items == []


# def test_list_with_invalid_system_id_filter(item_repository):
#     """
#     Test getting an item with an invalid system ID filter

#     Verify that the `list` method properly handles the retrieval of items with the provided
#     ID filter
#     """
#     with pytest.raises(InvalidObjectIdError) as exc:
#         item_repository.list("Invalid", None)
#     assert str(exc.value) == "Invalid ObjectId value 'Invalid'"


# def test_list_with_catalogue_item_id_filter(test_helpers, database_mock, item_repository):
#     """
#     Test getting items based on the provided catalogue item ID filter.

#     Verify that the `list` method properly handles the retrieval of items based on
#     the provided catalogue item ID filter
#     """
#     # pylint: disable=duplicate-code
#     item = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )
#     session = MagicMock()
#     # pylint: enable=duplicate-code

#     # Mock `find` to return a list of item documents
#     test_helpers.mock_find(
#         database_mock.items,
#         [
#             {
#                 **FULL_ITEM_INFO,
#                 **MOCK_CREATED_MODIFIED_TIME,
#                 "_id": CustomObjectId(item.id),
#                 "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
#                 "system_id": CustomObjectId(item.system_id),
#                 "usage_status_id": CustomObjectId(item.usage_status_id),
#                 "usage_status": item.usage_status,
#             }
#         ],
#     )

#     retrieved_item = item_repository.list(None, item.catalogue_item_id, session=session)

#     database_mock.items.find.assert_called_once_with(
#         {"catalogue_item_id": CustomObjectId(item.catalogue_item_id)}, session=session
#     )
#     assert retrieved_item == [item]


# def test_with_catalogue_item_id_filter_no_matching_results(test_helpers, database_mock, item_repository):
#     """
#     Test getting items based on the provided catalogue item ID filter when there are no matching results in
#     the database.

#     Verify the `list` method properly handles the retrieval of items based on the provided
#     catalogue item ID filter
#     """
#     session = MagicMock()

#     # Mock `find` to return an empty list of item documents
#     test_helpers.mock_find(database_mock.items, [])

#     catalogue_item_id = str(ObjectId())
#     retrieved_items = item_repository.list(None, catalogue_item_id, session=session)

#     database_mock.items.find.assert_called_once_with(
#         {"catalogue_item_id": CustomObjectId(catalogue_item_id)}, session=session
#     )
#     assert retrieved_items == []


# def test_list_with_invalid_catalogue_item_id(item_repository):
#     """
#     Test getting an item with an invalid catalogue item ID filter

#     Verify that the `list` method properly handles the retrieval of items with the provided
#     ID filter
#     """
#     with pytest.raises(InvalidObjectIdError) as exc:
#         item_repository.list(None, "Invalid")
#     assert str(exc.value) == "Invalid ObjectId value 'Invalid'"


# def test_list_with_both_system_catalogue_item_id_filters(test_helpers, database_mock, item_repository):
#     """
#     Test getting an item with both system and catalogue item id filters.

#     Verify that the `list` method properly handles the retrieval of items with the provided ID filters
#     """
#     # pylint: disable=duplicate-code
#     item = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )
#     session = MagicMock()
#     # pylint: enable=duplicate-code

#     # Mock `find` to return a list of item documents
#     test_helpers.mock_find(
#         database_mock.items,
#         [
#             {
#                 **FULL_ITEM_INFO,
#                 **MOCK_CREATED_MODIFIED_TIME,
#                 "_id": CustomObjectId(item.id),
#                 "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
#                 "system_id": CustomObjectId(item.system_id),
#                 "usage_status_id": CustomObjectId(item.usage_status_id),
#                 "usage_status": item.usage_status,
#             }
#         ],
#     )

#     retrieved_item = item_repository.list(item.system_id, item.catalogue_item_id, session=session)

#     database_mock.items.find.assert_called_once_with(
#         {"system_id": CustomObjectId(item.system_id), "catalogue_item_id": CustomObjectId(item.catalogue_item_id)},
#         session=session,
#     )
#     assert retrieved_item == [item]


# def test_list_no_matching_result_both_filters(test_helpers, database_mock, item_repository):
#     """
#     Test getting items based on the provided system and catalogue item ID filters when there are no matching results in
#     the database.

#     Verify the `list` method properly handles the retrieval of items based on the provided
#     system and catalogue item ID filters
#     """
#     session = MagicMock()

#     # Mock `find` to return an empty list of item documents
#     test_helpers.mock_find(database_mock.items, [])

#     system_id = str(ObjectId())
#     catalogue_item_id = str(ObjectId())
#     retrieved_items = item_repository.list(system_id, catalogue_item_id, session=session)

#     database_mock.items.find.assert_called_once_with(
#         {"system_id": CustomObjectId(system_id), "catalogue_item_id": CustomObjectId(catalogue_item_id)},
#         session=session,
#     )
#     assert retrieved_items == []


# def test_list_two_filters_no_matching_results(test_helpers, database_mock, item_repository):
#     """
#     Test getting items based on the provided system and catalogue item ID filters when there are no matching results for
#     one of the filters in the database.

#     Verify the `list` method properly handles the retrieval of items based on the provided
#     system and catalogue item ID filters
#     """
#     # pylint: disable=duplicate-code
#     item = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )
#     session = MagicMock()
#     # pylint: enable=duplicate-code

#     # Mock `find` to return a list of item documents
#     test_helpers.mock_find(
#         database_mock.items,
#         [],
#     )

#     # catalogue item id no matching results
#     rd_catalogue_item_id = str(ObjectId())
#     retrieved_item = item_repository.list(item.system_id, rd_catalogue_item_id, session=session)

#     database_mock.items.find.assert_called_with(
#         {"system_id": CustomObjectId(item.system_id), "catalogue_item_id": CustomObjectId(rd_catalogue_item_id)},
#         session=session,
#     )
#     assert retrieved_item == []

#     # # Mock `find` to return a list of item documents
#     test_helpers.mock_find(
#         database_mock.items,
#         [],
#     )

#     # system id no matching results
#     rd_system_id = str(ObjectId())
#     retrieved_item = item_repository.list(rd_system_id, item.catalogue_item_id, session=session)

#     database_mock.items.find.assert_called_with(
#         {"system_id": CustomObjectId(rd_system_id), "catalogue_item_id": CustomObjectId(item.catalogue_item_id)},
#         session=session,
#     )
#     assert retrieved_item == []


# def test_update(test_helpers, database_mock, item_repository):
#     """
#     Test updating an item.

#     Verify that the `update` method properly handles the item to be updated.
#     """
#     # pylint: disable=duplicate-code
#     item = ItemOut(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#     )
#     session = MagicMock()
#     # pylint: enable=duplicate-code

#     # Mock `update_one` to return an object for the updated item document
#     test_helpers.mock_update_one(database_mock.items)
#     # Mock `find_one` to return the updated catalogue item document
#     test_helpers.mock_find_one(
#         database_mock.items,
#         {
#             **FULL_ITEM_INFO,
#             **MOCK_CREATED_MODIFIED_TIME,
#             "_id": CustomObjectId(item.id),
#             "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
#             "system_id": CustomObjectId(item.system_id),
#             "usage_status_id": CustomObjectId(item.usage_status_id),
#             "usage_status": item.usage_status,
#         },
#     )

#     item_in = ItemIn(
#         **FULL_ITEM_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         catalogue_item_id=item.catalogue_item_id,
#         system_id=item.system_id,
#         usage_status_id=item.usage_status_id,
#         usage_status=item.usage_status,
#     )
#     updated_item = item_repository.update(item.id, item_in, session=session)

#     database_mock.items.update_one.assert_called_once_with(
#         {"_id": CustomObjectId(item.id)},
#         {
#             "$set": {
#                 "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
#                 **item_in.model_dump(by_alias=True),
#             }
#         },
#         session=session,
#     )
#     database_mock.items.find_one.assert_called_once_with({"_id": CustomObjectId(item.id)}, session=session)
#     assert updated_item == item


# def test_update_with_invalid_id(item_repository):
#     """
#     Test updating an item with an invalid ID.

#     Verify that the `update` method properly handles the update of an item with an invalid ID.
#     """
#     updated_item = MagicMock()
#     item_id = "invalid"

#     with pytest.raises(InvalidObjectIdError) as exc:
#         item_repository.update(item_id, updated_item)
#     assert str(exc.value) == f"Invalid ObjectId value '{item_id}'"


# @patch("inventory_management_system_api.repositories.item.datetime")
# def test_insert_property_to_all_in(datetime_mock, test_helpers, database_mock, item_repository):
#     """
#     Test inserting a property

#     Verify that the `insert_property_to_all_matching` method properly handles the insertion of a
#     property
#     """
#     session = MagicMock()
#     catalogue_item_ids = [ObjectId(), ObjectId()]
#     property_in = PropertyIn(**MOCK_PROPERTY_A_INFO)

#     # Mock 'update_many'
#     test_helpers.mock_update_many(database_mock.items)

#     item_repository.insert_property_to_all_in(catalogue_item_ids, property_in, session=session)

#     database_mock.items.update_many.assert_called_once_with(
#         {"catalogue_item_id": {"$in": catalogue_item_ids}},
#         {
#             "$push": {"properties": property_in.model_dump(by_alias=True)},
#             "$set": {"modified_time": datetime_mock.now.return_value},
#         },
#         session=session,
#     )


# # pylint:disable=duplicate-code


# @patch("inventory_management_system_api.repositories.item.datetime")
# def test_update_names_of_all_properties_with_id(datetime_mock, test_helpers, database_mock, item_repository):
#     """
#     Test updating the names of all properties with a given id

#     Verify that the `update_names_of_all_properties_with_id` method properly handles the update of
#     property names
#     """
#     session = MagicMock()
#     property_id = str(ObjectId())
#     new_property_name = "new property name"

#     # Mock 'update_many'
#     test_helpers.mock_update_many(database_mock.items)

#     item_repository.update_names_of_all_properties_with_id(property_id, new_property_name, session=session)

#     database_mock.items.update_many.assert_called_once_with(
#         {"properties._id": CustomObjectId(property_id)},
#         {
#             "$set": {"properties.$[elem].name": new_property_name, "modified_time": datetime_mock.now.return_value},
#         },
#         array_filters=[{"elem._id": CustomObjectId(property_id)}],
#         session=session,
#     )


# # pylint:enable=duplicate-code
