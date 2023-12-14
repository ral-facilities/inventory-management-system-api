"""
Unit tests for the `ItemRepo` repository.
"""
import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.item import ItemOut, ItemIn

# pylint: disable=duplicate-code
FULL_SYSTEM_A_INFO = {
    "parent_id": None,
    "name": "System A",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
    "code": "system-a",
}

FULL_ITEM_INFO = {
    "purchase_order_number": None,
    "is_defective": False,
    "usage_status": 0,
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "asset_number": None,
    "serial_number": "xyz123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
    "properties": [{"name": "Property A", "value": 21, "unit": "mm"}],
}
# pylint: enable=duplicate-code


def test_create(test_helpers, database_mock, item_repository):
    """
    Test creating an item.
    """
    item = ItemOut(id=str(ObjectId()), catalogue_item_id=str(ObjectId()), system_id=str(ObjectId()), **FULL_ITEM_INFO)

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(database_mock.systems, {"_id": CustomObjectId(item.system_id), **FULL_SYSTEM_A_INFO})
    # Mock `insert_one` to return an object for the inserted item document
    test_helpers.mock_insert_one(database_mock.items, CustomObjectId(item.id))
    # Mock `find_one` to return the inserted item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            "_id": CustomObjectId(item.id),
            "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
            "system_id": CustomObjectId(item.system_id),
            **FULL_ITEM_INFO,
        },
    )

    item_in = ItemIn(catalogue_item_id=item.catalogue_item_id, system_id=item.system_id, **FULL_ITEM_INFO)
    created_item = item_repository.create(item_in)

    database_mock.systems.find_one.assert_called_once_with({"_id": CustomObjectId(item.system_id)})
    database_mock.items.insert_one.assert_called_once_with(item_in.model_dump())
    assert created_item == item


def test_create_with_non_existent_system_id(test_helpers, database_mock, item_repository):
    """
    Test creating an item with a non-existent system ID.
    """
    system_id = str(ObjectId())

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(database_mock.systems, None)

    with pytest.raises(MissingRecordError) as exc:
        item_repository.create(ItemIn(catalogue_item_id=str(ObjectId()), system_id=system_id, **FULL_ITEM_INFO))

    database_mock.systems.find_one.assert_called_once_with({"_id": CustomObjectId(system_id)})
    database_mock.items.insert_one.assert_not_called()
    assert str(exc.value) == f"No system found with ID: {system_id}"

def test_get(test_helpers, database_mock, item_repository):
    """
    Test getting an item

    Verify that the `get` method properly handles the retrieval of an item by ID.
    """
    item = ItemOut(id=str(ObjectId()), catalogue_item_id=str(ObjectId()), system_id=str(ObjectId()), **FULL_ITEM_INFO)

    # Mock `find_one` to return the inserted item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            "_id": CustomObjectId(item.id),
            "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
            "system_id": CustomObjectId(item.system_id),
            **FULL_ITEM_INFO,
        },
    )

    retrieved_item = item_repository.get(item.id)

    database_mock.items.find_one.assert_called_once_with({"_id": CustomObjectId(item.id)})
    assert retrieved_item == item

def test_get_with_invalid_id(item_repository):
    """
    Test getting an item with an invalid ID.

    Verify the `get` method properly handles the retrieval of an item with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        item_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"

def test_get_with_nonexistent_id(test_helpers, database_mock, item_repository):
    """
    Test getting an item with a nonexistent ID.

    Verify the `get` method properly handles the retrieval of an item with a nonexistent ID.
    """
    item_id = str(ObjectId())

    # Mock `find_one` to not return a catalogue item document
    test_helpers.mock_find_one(database_mock.items, None)

    retrieved_item = item_repository.get(item_id)

    assert retrieved_item is None
    database_mock.items.find_one.assert_called_once_with({"_id": CustomObjectId(item_id)})

