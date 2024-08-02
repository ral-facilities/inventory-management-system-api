"""
Unit tests for the `CatalogueItemRepo` repository.
"""

from test.mock_data import (
    CATALOGUE_ITEM_IN_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY,
)
from test.unit.repositories.conftest import RepositoryTestHelpers
from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME, MOCK_PROPERTY_A_INFO
from test.unit.repositories.test_item import FULL_ITEM_INFO
from typing import Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId
from pymongo.cursor import Cursor

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

        RepositoryTestHelpers.mock_find_one(self.catalogue_items_collection, child_item_data)

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
    _create_exception: pytest.ExceptionInfo

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

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemRepo` `create` method with the appropriate data from a prior call to `mock_create`
        while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_item_repository.create(self._catalogue_item_in)
        self._create_exception = exc

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

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_items_collection.insert_one.assert_not_called()

        assert str(self._create_exception.value) == message


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


# FULL_CATALOGUE_ITEM_A_INFO = {
#     "name": "Catalogue Item A",
#     "description": "This is Catalogue Item A",
#     "cost_gbp": 129.99,
#     "cost_to_rework_gbp": None,
#     "days_to_replace": 2.0,
#     "days_to_rework": None,
#     "drawing_number": None,
#     "drawing_link": "https://drawing-link.com/",
#     "item_model_number": "abc123",
#     "is_obsolete": False,
#     "obsolete_reason": None,
#     "obsolete_replacement_catalogue_item_id": None,
#     "notes": None,
#     "properties": [
#         {"id": str(ObjectId()), "name": "Property A", "value": 20, "unit": "mm"},
#         {"id": str(ObjectId()), "name": "Property B", "value": False, "unit": None},
#         {"id": str(ObjectId()), "name": "Property C", "value": "20x15x10", "unit": "cm"},
#     ],
# }

# # pylint: disable=duplicate-code
# FULL_CATALOGUE_ITEM_B_INFO = {
#     "name": "Catalogue Item B",
#     "description": "This is Catalogue Item B",
#     "cost_gbp": 300.00,
#     "cost_to_rework_gbp": 120.99,
#     "days_to_replace": 1.5,
#     "days_to_rework": 3.0,
#     "drawing_number": "789xyz",
#     "drawing_link": None,
#     "item_model_number": None,
#     "is_obsolete": False,
#     "obsolete_reason": None,
#     "obsolete_replacement_catalogue_item_id": None,
#     "notes": "Some extra information",
#     "properties": [{"id": str(ObjectId()), "name": "Property A", "value": True, "unit": None}],
# }
# # pylint: enable=duplicate-code


# def test_delete(test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test deleting a catalogue item.

#     Verify that the `delete` method properly handles the deletion of a catalogue item by ID.
#     """
#     catalogue_item_id = str(ObjectId())
#     session = MagicMock()

#     # Mock `delete_one` to return that one document has been deleted
#     test_helpers.mock_delete_one(database_mock.catalogue_items, 1)

#     # Mock `find_one` to return no child item document
#     test_helpers.mock_find_one(database_mock.items, None)

#     catalogue_item_repository.delete(catalogue_item_id, session=session)

#     database_mock.catalogue_items.delete_one.assert_called_once_with(
#         {"_id": CustomObjectId(catalogue_item_id)}, session=session
#     )


# def test_delete_with_child_items(test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test deleting a catalogue item with child items.

#     Verify that the `delete` method properly handles the deletion of a catalogue item with child items.
#     """
#     catalogue_item_id = str(ObjectId())

#     # Mock `find_one` to return the child item document
#     test_helpers.mock_find_one(
#         database_mock.items,
#         {
#             "_id": CustomObjectId(str(ObjectId())),
#             "catalogue_item_id": CustomObjectId(catalogue_item_id),
#             **FULL_ITEM_INFO,
#         },
#     )

#     with pytest.raises(ChildElementsExistError) as exc:
#         catalogue_item_repository.delete(catalogue_item_id)
#     assert str(exc.value) == f"Catalogue item with ID {catalogue_item_id} has child elements and cannot be deleted"


# def test_delete_with_invalid_id(catalogue_item_repository):
#     """
#     Test deleting a catalogue item with an invalid ID.

#     Verify that the `delete` method properly handles the deletion of a catalogue item with an invalid ID.
#     """
#     with pytest.raises(InvalidObjectIdError) as exc:
#         catalogue_item_repository.delete("invalid")
#     assert str(exc.value) == "Invalid ObjectId value 'invalid'"


# def test_delete_with_non_existent_id(test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test deleting a catalogue item with a non-existent ID.

#     Verify that the `delete` method properly handles the deletion of a catalogue item with a non-existent ID.
#     """
#     catalogue_item_id = str(ObjectId())

#     # Mock `delete_one` to return that no document has been deleted
#     test_helpers.mock_delete_one(database_mock.catalogue_items, 0)

#     # Mock `find_one` to return no child item document
#     test_helpers.mock_find_one(database_mock.items, None)

#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_item_repository.delete(catalogue_item_id)
#     assert str(exc.value) == f"No catalogue item found with ID: {catalogue_item_id}"
#     database_mock.catalogue_items.delete_one.assert_called_once_with(
#         {"_id": CustomObjectId(catalogue_item_id)}, session=None
#     )


# def test_update(test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test updating a catalogue item.

#     Verify that the `update` method properly handles the catalogue item to be updated.
#     """
#     catalogue_item_info = {
#         **FULL_CATALOGUE_ITEM_A_INFO,
#         **MOCK_CREATED_MODIFIED_TIME,
#         "name": "Catalogue Item B",
#         "description": "This is Catalogue Item B",
#     }
#     # pylint: disable=duplicate-code
#     catalogue_item = CatalogueItemOut(
#         **catalogue_item_info,
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#     )
#     session = MagicMock()
#     # pylint: enable=duplicate-code

#     # Mock `update_one` to return an object for the updated catalogue item document
#     test_helpers.mock_update_one(database_mock.catalogue_items)
#     # Mock `find_one` to return the updated catalogue item document
#     test_helpers.mock_find_one(
#         database_mock.catalogue_items,
#         {
#             "_id": CustomObjectId(catalogue_item.id),
#             "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
#             "manufacturer_id": CustomObjectId(catalogue_item.manufacturer_id),
#             **catalogue_item_info,
#         },
#     )

#     # Mock `find_one` to return no child item document
#     test_helpers.mock_find_one(database_mock.items, None)

#     catalogue_item_in = CatalogueItemIn(
#         **catalogue_item_info,
#         catalogue_category_id=catalogue_item.catalogue_category_id,
#         manufacturer_id=catalogue_item.manufacturer_id,
#     )
#     updated_catalogue_item = catalogue_item_repository.update(catalogue_item.id, catalogue_item_in, session=session)

#     database_mock.catalogue_items.update_one.assert_called_once_with(
#         {"_id": CustomObjectId(catalogue_item.id)},
#         {
#             "$set": {
#                 "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
#                 **catalogue_item_in.model_dump(by_alias=True),
#             }
#         },
#         session=session,
#     )
#     database_mock.catalogue_items.find_one.assert_called_once_with(
#         {"_id": CustomObjectId(catalogue_item.id)}, session=session
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_with_invalid_id(catalogue_item_repository):
#     """
#     Test updating a catalogue category with invalid ID.

#     Verify that the `update` method properly handles the update of a catalogue category with an invalid ID.
#     """
#     update_catalogue_item = MagicMock()
#     catalogue_item_id = "invalid"

#     with pytest.raises(InvalidObjectIdError) as exc:
#         catalogue_item_repository.update(catalogue_item_id, update_catalogue_item)
#     assert str(exc.value) == f"Invalid ObjectId value '{catalogue_item_id}'"


# def test_has_child_elements_with_no_child_items(test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test has_child_elements returns false when there are no child items
#     """
#     # Mock `find_one` to return no child items category document
#     test_helpers.mock_find_one(database_mock.items, None)

#     result = catalogue_item_repository.has_child_elements(ObjectId())

#     assert not result


# def test_has_child_elements_with_child_items(test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test has_child_elements returns true when there are child items.
#     """

#     catalogue_category_id = str(ObjectId())

#     # Mock find_one to return 1 (child items found)
#     test_helpers.mock_find_one(
#         database_mock.catalogue_categories,
#         {
#             **FULL_ITEM_INFO,
#             "_id": CustomObjectId(str(ObjectId())),
#             "catalogue_item_id": catalogue_category_id,
#         },
#     )
#     # Mock find_one to return 0 (child items not found)
#     test_helpers.mock_find_one(database_mock.catalogue_items, None)

#     result = catalogue_item_repository.has_child_elements(catalogue_category_id)

#     assert result


# def test_list_ids(database_mock, catalogue_item_repository):
#     """
#     Test getting catalogue item IDs.

#     Verify that the `list_ids` method properly handles the retrieval of catalogue item IDs given a
#     catalogue_category_id to filter by.
#     """
#     session = MagicMock()
#     catalogue_category_id = str(ObjectId())
#     find_cursor_mock = MagicMock(Cursor)

#     # Mock `find` to return the cursor mock so we can check distinct is used correctly
#     database_mock.catalogue_items.find.return_value = find_cursor_mock

#     retrieved_catalogue_items = catalogue_item_repository.list_ids(catalogue_category_id, session=session)

#     database_mock.catalogue_items.find.assert_called_once_with(
#         {"catalogue_category_id": CustomObjectId(catalogue_category_id)}, {"_id": 1}, session=session
#     )
#     find_cursor_mock.distinct.assert_called_once_with("_id")
#     assert retrieved_catalogue_items == find_cursor_mock.distinct.return_value


# @patch("inventory_management_system_api.repositories.catalogue_item.datetime")
# def test_insert_property_to_all_matching(datetime_mock, test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test inserting a property.

#     Verify that the `insert_property_to_all_matching` method properly handles the insertion of a
#     property.
#     """
#     session = MagicMock()
#     catalogue_category_id = str(ObjectId())
#     property_in = PropertyIn(**MOCK_PROPERTY_A_INFO)

#     # Mock 'update_many'
#     test_helpers.mock_update_many(database_mock.catalogue_items)

#     catalogue_item_repository.insert_property_to_all_matching(catalogue_category_id, property_in, session=session)

#     database_mock.catalogue_items.update_many.assert_called_once_with(
#         {"catalogue_category_id": CustomObjectId(catalogue_category_id)},
#         {
#             "$push": {"properties": property_in.model_dump(by_alias=True)},
#             "$set": {"modified_time": datetime_mock.now.return_value},
#         },
#         session=session,
#     )


# @patch("inventory_management_system_api.repositories.catalogue_item.datetime")
# def test_update_names_of_all_properties_with_id(datetime_mock, test_helpers, database_mock, catalogue_item_repository):
#     """
#     Test updating the names of all properties with a given ID.

#     Verify that the `update_names_of_all_properties_with_id` method properly handles the update of
#     property names.
#     """
#     session = MagicMock()
#     property_id = str(ObjectId())
#     new_property_name = "new property name"

#     # Mock 'update_many'
#     test_helpers.mock_update_many(database_mock.catalogue_items)

#     catalogue_item_repository.update_names_of_all_properties_with_id(property_id, new_property_name, session=session)

#     database_mock.catalogue_items.update_many.assert_called_once_with(
#         {"properties._id": CustomObjectId(property_id)},
#         {
#             "$set": {"properties.$[elem].name": new_property_name, "modified_time": datetime_mock.now.return_value},
#         },
#         array_filters=[{"elem._id": CustomObjectId(property_id)}],
#         session=session,
#     )
