"""
Unit tests for the `CatalogueItemRepo` repository.
"""

from unittest.mock import MagicMock
from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from test.unit.repositories.test_item import FULL_ITEM_INFO

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut, CatalogueItemIn


FULL_CATALOGUE_ITEM_A_INFO = {
    "name": "Catalogue Item A",
    "description": "This is Catalogue Item A",
    "cost_gbp": 129.99,
    "cost_to_rework_gbp": None,
    "days_to_replace": 2.0,
    "days_to_rework": None,
    "drawing_number": None,
    "drawing_link": "https://drawing-link.com/",
    "item_model_number": "abc123",
    "is_obsolete": False,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "notes": None,
    "properties": [
        {"name": "Property A", "value": 20, "unit": "mm"},
        {"name": "Property B", "value": False, "unit": None},
        {"name": "Property C", "value": "20x15x10", "unit": "cm"},
    ],
}

# pylint: disable=duplicate-code
FULL_CATALOGUE_ITEM_B_INFO = {
    "name": "Catalogue Item B",
    "description": "This is Catalogue Item B",
    "cost_gbp": 300.00,
    "cost_to_rework_gbp": 120.99,
    "days_to_replace": 1.5,
    "days_to_rework": 3.0,
    "drawing_number": "789xyz",
    "drawing_link": None,
    "item_model_number": None,
    "is_obsolete": False,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "notes": "Some extra information",
    "properties": [{"name": "Property A", "value": True, "unit": None}],
}
# pylint: enable=duplicate-code


def test_create(test_helpers, database_mock, catalogue_item_repository):
    """
    Test creating a catalogue item.

    Verify that the `create` method properly handles the catalogue item to be created, checks that there is not a
    duplicate catalogue item, and creates the catalogue item.
    """
    # pylint: disable=duplicate-code
    catalogue_item_in = CatalogueItemIn(
        **FULL_CATALOGUE_ITEM_A_INFO,
        catalogue_category_id=str(ObjectId()),
        manufacturer_id=str(ObjectId()),
    )
    catalogue_item_info = catalogue_item_in.model_dump()
    catalogue_item_out = CatalogueItemOut(
        **catalogue_item_info,
        id=str(ObjectId()),
    )
    # pylint: enable=duplicate-code

    # Mock `insert_one` to return an object for the inserted catalogue item document
    test_helpers.mock_insert_one(database_mock.catalogue_items, CustomObjectId(catalogue_item_out.id))

    # Mock `find_one` to return the inserted catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            **catalogue_item_info,
            "_id": CustomObjectId(catalogue_item_out.id),
        },
    )

    # Mock `find_one` to return no duplicate catalogue items found
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    created_catalogue_item = catalogue_item_repository.create(catalogue_item_in)

    database_mock.catalogue_items.insert_one.assert_called_once_with(catalogue_item_info)
    assert created_catalogue_item == catalogue_item_out


def test_delete(test_helpers, database_mock, catalogue_item_repository):
    """
    Test deleting a catalogue item.

    Verify that the `delete` method properly handles the deletion of a catalogue item by ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_items, 1)

    # Mock `find_one` to return no child item document
    test_helpers.mock_find_one(database_mock.items, None)

    catalogue_item_repository.delete(catalogue_item_id)

    database_mock.catalogue_items.delete_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item_id)})


def test_delete_with_child_items(test_helpers, database_mock, catalogue_item_repository):
    """
    Test deleting a catalogue item with child items.

    Verify that the `delete` method properly handles the deletion of a catalogue item with child items.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `find_one` to return the child item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_item_id": CustomObjectId(catalogue_item_id),
            **FULL_ITEM_INFO,
        },
    )

    with pytest.raises(ChildElementsExistError) as exc:
        catalogue_item_repository.delete(catalogue_item_id)
    assert str(exc.value) == f"Catalogue item with ID {catalogue_item_id} has child elements and cannot be deleted"


def test_delete_with_invalid_id(catalogue_item_repository):
    """
    Test deleting a catalogue item with an invalid ID.

    Verify that the `delete` method properly handles the deletion of a catalogue item with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_item_repository.delete("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_nonexistent_id(test_helpers, database_mock, catalogue_item_repository):
    """
    Test deleting a catalogue item with a nonexistent ID.

    Verify that the `delete` method properly handles the deletion of a catalogue item with a nonexistent ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `delete_one` to return that no document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_items, 0)

    # Mock `find_one` to return no child item document
    test_helpers.mock_find_one(database_mock.items, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_item_repository.delete(catalogue_item_id)
    assert str(exc.value) == f"No catalogue item found with ID: {catalogue_item_id}"
    database_mock.catalogue_items.delete_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item_id)})


def test_get(test_helpers, database_mock, catalogue_item_repository):
    """
    Test getting a catalogue item.

    Verify that the `get` method properly handles the retrieval of a catalogue item by ID.
    """
    # pylint: disable=duplicate-code
    catalogue_item = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        manufacturer_id=str(ObjectId()),
        **FULL_CATALOGUE_ITEM_A_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            **FULL_CATALOGUE_ITEM_A_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(catalogue_item.id),
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            "manufacturer_id": CustomObjectId(catalogue_item.manufacturer_id),
        },
    )

    retrieved_catalogue_item = catalogue_item_repository.get(catalogue_item.id)

    database_mock.catalogue_items.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item.id)})
    assert retrieved_catalogue_item == catalogue_item


def test_get_with_invalid_id(catalogue_item_repository):
    """
    Test getting a catalogue item with an invalid ID.

    Verify that the `get` method properly handles the retrieval of a catalogue item with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_item_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_nonexistent_id(test_helpers, database_mock, catalogue_item_repository):
    """
    Test getting a catalogue item with a nonexistent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue item with a nonexistent ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `find_one` to not return a catalogue item document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    retrieved_catalogue_item = catalogue_item_repository.get(catalogue_item_id)

    assert retrieved_catalogue_item is None
    database_mock.catalogue_items.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item_id)})


def test_list(test_helpers, database_mock, catalogue_item_repository):
    """
    Test getting catalogue items.

    Verify that the `list` method properly handles the retrieval of catalogue items without filters.
    """
    catalogue_item_a = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        manufacturer_id=str(ObjectId()),
        **FULL_CATALOGUE_ITEM_A_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
    )
    catalogue_item_b = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        manufacturer_id=str(ObjectId()),
        **FULL_CATALOGUE_ITEM_B_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
    )

    # Mock `find` to return a list of catalogue item documents
    test_helpers.mock_find(
        database_mock.catalogue_items,
        [
            {
                **FULL_CATALOGUE_ITEM_A_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_item_a.id),
                "catalogue_category_id": CustomObjectId(catalogue_item_a.catalogue_category_id),
                "manufacturer_id": CustomObjectId(catalogue_item_a.manufacturer_id),
            },
            {
                **FULL_CATALOGUE_ITEM_B_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_item_b.id),
                "catalogue_category_id": CustomObjectId(catalogue_item_b.catalogue_category_id),
                "manufacturer_id": CustomObjectId(catalogue_item_b.manufacturer_id),
            },
        ],
    )

    retrieved_catalogue_items = catalogue_item_repository.list(None)

    database_mock.catalogue_items.find.assert_called_once_with({})
    assert retrieved_catalogue_items == [catalogue_item_a, catalogue_item_b]


def test_list_with_catalogue_category_id_filter(test_helpers, database_mock, catalogue_item_repository):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.

    Verify that the `list` method properly handles the retrieval of catalogue items based on the provided catalogue
    category ID filter.
    """
    # pylint: disable=duplicate-code
    catalogue_item = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        manufacturer_id=str(ObjectId()),
        **FULL_CATALOGUE_ITEM_A_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
    )
    # pylint: enable=duplicate-code
    # Mock `find` to return a list of catalogue item documents
    test_helpers.mock_find(
        database_mock.catalogue_items,
        [
            {
                **FULL_CATALOGUE_ITEM_A_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_item.id),
                "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
                "manufacturer_id": CustomObjectId(catalogue_item.manufacturer_id),
            }
        ],
    )

    retrieved_catalogue_items = catalogue_item_repository.list(catalogue_item.catalogue_category_id)

    database_mock.catalogue_items.find.assert_called_once_with(
        {"catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id)}
    )
    assert retrieved_catalogue_items == [catalogue_item]


def test_list_with_catalogue_category_id_filter_no_matching_results(
    test_helpers, database_mock, catalogue_item_repository
):
    """
    Test getting catalogue items based on the provided catalogue category ID filter when there is no matching results in
    the database.

    Verify that the `list` method properly handles the retrieval of catalogue items based on the provided catalogue
    category ID filter.
    """
    # Mock `find` to return an empty list of catalogue item documents
    test_helpers.mock_find(database_mock.catalogue_items, [])

    catalogue_category_id = str(ObjectId())
    retrieved_catalogue_items = catalogue_item_repository.list(catalogue_category_id)

    database_mock.catalogue_items.find.assert_called_once_with(
        {"catalogue_category_id": CustomObjectId(catalogue_category_id)}
    )
    assert retrieved_catalogue_items == []


def test_list_with_invalid_catalogue_category_id_filter(catalogue_item_repository):
    """
    Test getting a catalogue items with an invalid catalogue category ID filter.

    Verify that the `list` method properly handles the retrieval of catalogue items with an invalid catalogue category
    ID filter.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_item_repository.list("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_update(test_helpers, database_mock, catalogue_item_repository):
    """
    Test updating a catalogue item.

    Verify that the `update` method properly handles the catalogue item to be updated.
    """
    catalogue_item_info = {
        **FULL_CATALOGUE_ITEM_A_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        "name": "Catalogue Item B",
        "description": "This is Catalogue Item B",
    }
    # pylint: disable=duplicate-code
    catalogue_item = CatalogueItemOut(
        **catalogue_item_info,
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        manufacturer_id=str(ObjectId()),
    )
    # pylint: enable=duplicate-code

    # Mock `update_one` to return an object for the updated catalogue item document
    test_helpers.mock_update_one(database_mock.catalogue_items)
    # Mock `find_one` to return the updated catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            "_id": CustomObjectId(catalogue_item.id),
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            "manufacturer_id": CustomObjectId(catalogue_item.manufacturer_id),
            **catalogue_item_info,
        },
    )

    # Mock `find_one` to return no child item document
    test_helpers.mock_find_one(database_mock.items, None)

    catalogue_item_in = CatalogueItemIn(
        **catalogue_item_info,
        catalogue_category_id=catalogue_item.catalogue_category_id,
        manufacturer_id=catalogue_item.manufacturer_id,
    )
    updated_catalogue_item = catalogue_item_repository.update(catalogue_item.id, catalogue_item_in)

    database_mock.catalogue_items.update_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_item.id)},
        {
            "$set": {
                "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
                **catalogue_item_in.model_dump(),
            }
        },
    )
    database_mock.catalogue_items.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item.id)})
    assert updated_catalogue_item == catalogue_item


def test_update_with_invalid_id(catalogue_item_repository):
    """
    Test updating a catalogue category with invalid ID.

    Verify that the `update` method properly handles the update of a catalogue category with an invalid ID.
    """
    update_catalogue_item = MagicMock()
    catalogue_item_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_item_repository.update(catalogue_item_id, update_catalogue_item)
    assert str(exc.value) == f"Invalid ObjectId value '{catalogue_item_id}'"


def test_has_child_elements_with_no_child_items(test_helpers, database_mock, catalogue_item_repository):
    """
    Test has_child_elements returns false when there are no child items
    """
    # Mock `find_one` to return no child items category document
    test_helpers.mock_find_one(database_mock.items, None)

    result = catalogue_item_repository.has_child_elements(ObjectId())

    assert not result


def test_has_child_elements_with_child_items(test_helpers, database_mock, catalogue_item_repository):
    """
    Test has_child_elements returns true when there are child items
    """

    catalogue_category_id = str(ObjectId())

    # Mock find_one to return 1 (child items found)
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **FULL_ITEM_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_item_id": catalogue_category_id,
        },
    )
    # Mock find_one to return 0 (child items not found)
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    result = catalogue_item_repository.has_child_elements(catalogue_category_id)

    assert result


def test_has_child_elements_with_child_catalogue_items(test_helpers, database_mock, catalogue_item_repository):
    """
    Test has_child_elements returns true when there are child items.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `find_one` to return no child catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # pylint: disable=duplicate-code
    # Mock `find_one` to return the child catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            **FULL_CATALOGUE_ITEM_A_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_category_id": CustomObjectId(catalogue_category_id),
        },
    )
    # pylint: enable=duplicate-code
    result = catalogue_item_repository.has_child_elements(catalogue_category_id)

    assert result
