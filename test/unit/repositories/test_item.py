"""
Unit tests for the `ItemRepo` repository.
"""

from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.item import ItemIn, ItemOut

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
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "asset_number": None,
    "serial_number": "xyz123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
    "properties": [{"id": str(ObjectId()), "name": "Property A", "value": 21, "unit": "mm"}],
}
# pylint: enable=duplicate-code


def test_create(test_helpers, database_mock, item_repository):
    """
    Test creating an item.
    """
    # pylint: disable=duplicate-code
    item_in = ItemIn(
        **FULL_ITEM_INFO,
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    item_info = item_in.model_dump(by_alias=True)
    item_out = ItemOut(
        **item_info,
        id=str(ObjectId()),
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            **FULL_SYSTEM_A_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(item_out.system_id),
        },
    )
    # Mock `insert_one` to return an object for the inserted item document
    test_helpers.mock_insert_one(database_mock.items, CustomObjectId(item_out.id))
    # Mock `find_one` to return the inserted item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            **item_info,
            "_id": CustomObjectId(item_out.id),
        },
    )

    created_item = item_repository.create(item_in, session=session)

    database_mock.systems.find_one.assert_called_once_with({"_id": CustomObjectId(item_out.system_id)}, session=session)
    database_mock.items.insert_one.assert_called_once_with(item_in.model_dump(by_alias=True), session=session)
    assert created_item == item_out


def test_create_with_non_existent_system_id(test_helpers, database_mock, item_repository):
    """
    Test creating an item with a non-existent system ID.
    """
    system_id = str(ObjectId())

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(database_mock.systems, None)

    with pytest.raises(MissingRecordError) as exc:
        item_repository.create(
            ItemIn(
                **FULL_ITEM_INFO,
                catalogue_item_id=str(ObjectId()),
                system_id=system_id,
                usage_status_id=str(ObjectId()),
                usage_status="New",
            )
        )

    database_mock.systems.find_one.assert_called_once_with({"_id": CustomObjectId(system_id)}, session=None)
    database_mock.items.insert_one.assert_not_called()
    assert str(exc.value) == f"No system found with ID: {system_id}"


def test_delete(test_helpers, database_mock, item_repository):
    """
    Test deleting an item.

    Verify that the `delete` method properly handles the deletion of an item by ID.
    """
    item_id = str(ObjectId())
    session = MagicMock()

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.items, 1)

    item_repository.delete(item_id, session=session)

    database_mock.items.delete_one.assert_called_once_with({"_id": CustomObjectId(item_id)}, session=session)


def test_delete_with_invalid_id(item_repository):
    """
    Test deleting an item with an invalid ID.

    Verify that the `delete` method properly handles the deletion of an item with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        item_repository.delete("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_non_existent_id(test_helpers, database_mock, item_repository):
    """
    Test deleting an item with an invalid ID.

    Verify that the `delete` method properly handles the deletion of an item with a non-existent ID.
    """
    item_id = str(ObjectId())

    # Mock `delete_one` to return that no document has been deleted
    test_helpers.mock_delete_one(database_mock.items, 0)

    with pytest.raises(MissingRecordError) as exc:
        item_repository.delete(item_id)
    assert str(exc.value) == f"No item found with ID: {item_id}"
    database_mock.items.delete_one.assert_called_once_with({"_id": CustomObjectId(item_id)}, session=None)


def test_list(test_helpers, database_mock, item_repository):
    """
    Test getting items.

    Verify that the `list` method properly handles the retrieval of items
    """
    # pylint: disable=duplicate-code
    item_a = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )

    item_b = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    # pylint: enable=duplicate-code
    session = MagicMock()

    # Mock `find` to return a list of item documents
    test_helpers.mock_find(
        database_mock.items,
        [
            {
                **FULL_ITEM_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(item_a.id),
                "catalogue_item_id": CustomObjectId(item_a.catalogue_item_id),
                "system_id": CustomObjectId(item_a.system_id),
                "usage_status_id": CustomObjectId(item_a.usage_status_id),
                "usage_status": item_a.usage_status,
            },
            {
                **FULL_ITEM_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(item_b.id),
                "catalogue_item_id": CustomObjectId(item_b.catalogue_item_id),
                "system_id": CustomObjectId(item_b.system_id),
                "usage_status_id": CustomObjectId(item_b.usage_status_id),
                "usage_status": item_b.usage_status,
            },
        ],
    )

    retrieved_item = item_repository.list(None, None, session=session)

    database_mock.items.find.assert_called_once_with({}, session=session)
    assert retrieved_item == [item_a, item_b]


def test_list_with_system_id_filter(test_helpers, database_mock, item_repository):
    """
    Test getting items based on the provided system ID filter.

    Verify that the `list` method properly handles the retrieval of items based on
    the provided system ID filter
    """
    # pylint: disable=duplicate-code
    item = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of item documents
    test_helpers.mock_find(
        database_mock.items,
        [
            {
                **FULL_ITEM_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(item.id),
                "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
                "system_id": CustomObjectId(item.system_id),
                "usage_status_id": CustomObjectId(item.usage_status_id),
                "usage_status": item.usage_status,
            }
        ],
    )

    retrieved_item = item_repository.list(item.system_id, None, session=session)

    database_mock.items.find.assert_called_once_with({"system_id": CustomObjectId(item.system_id)}, session=session)
    assert retrieved_item == [item]


def test_list_with_system_id_filter_no_matching_results(test_helpers, database_mock, item_repository):
    """
    Test getting items based on the provided system ID filter when there are no matching results in
    the database.

    Verify the `list` method properly handles the retrieval of items based on the provided
    system ID filter
    """
    session = MagicMock()

    # Mock `find` to return an empty list of item documents
    test_helpers.mock_find(database_mock.items, [])

    system_id = str(ObjectId())
    retrieved_items = item_repository.list(system_id, None, session=session)

    database_mock.items.find.assert_called_once_with({"system_id": CustomObjectId(system_id)}, session=session)
    assert retrieved_items == []


def test_list_with_invalid_system_id_filter(item_repository):
    """
    Test getting an item with an invalid system ID filter

    Verify that the `list` method properly handles the retrieval of items with the provided
    ID filter
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        item_repository.list("Invalid", None)
    assert str(exc.value) == "Invalid ObjectId value 'Invalid'"


def test_list_with_catalogue_item_id_filter(test_helpers, database_mock, item_repository):
    """
    Test getting items based on the provided catalogue item ID filter.

    Verify that the `list` method properly handles the retrieval of items based on
    the provided catalogue item ID filter
    """
    # pylint: disable=duplicate-code
    item = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of item documents
    test_helpers.mock_find(
        database_mock.items,
        [
            {
                **FULL_ITEM_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(item.id),
                "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
                "system_id": CustomObjectId(item.system_id),
                "usage_status_id": CustomObjectId(item.usage_status_id),
                "usage_status": item.usage_status,
            }
        ],
    )

    retrieved_item = item_repository.list(None, item.catalogue_item_id, session=session)

    database_mock.items.find.assert_called_once_with(
        {"catalogue_item_id": CustomObjectId(item.catalogue_item_id)}, session=session
    )
    assert retrieved_item == [item]


def test_with_catalogue_item_id_filter_no_matching_results(test_helpers, database_mock, item_repository):
    """
    Test getting items based on the provided catalogue item ID filter when there are no matching results in
    the database.

    Verify the `list` method properly handles the retrieval of items based on the provided
    catalogue item ID filter
    """
    session = MagicMock()

    # Mock `find` to return an empty list of item documents
    test_helpers.mock_find(database_mock.items, [])

    catalogue_item_id = str(ObjectId())
    retrieved_items = item_repository.list(None, catalogue_item_id, session=session)

    database_mock.items.find.assert_called_once_with(
        {"catalogue_item_id": CustomObjectId(catalogue_item_id)}, session=session
    )
    assert retrieved_items == []


def test_list_with_invalid_catalogue_item_id(item_repository):
    """
    Test getting an item with an invalid catalogue item ID filter

    Verify that the `list` method properly handles the retrieval of items with the provided
    ID filter
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        item_repository.list(None, "Invalid")
    assert str(exc.value) == "Invalid ObjectId value 'Invalid'"


def test_list_with_both_system_catalogue_item_id_filters(test_helpers, database_mock, item_repository):
    """
    Test getting an item with both system and catalogue item id filters.

    Verify that the `list` method properly handles the retrieval of items with the provided ID filters
    """
    # pylint: disable=duplicate-code
    item = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of item documents
    test_helpers.mock_find(
        database_mock.items,
        [
            {
                **FULL_ITEM_INFO,
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(item.id),
                "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
                "system_id": CustomObjectId(item.system_id),
                "usage_status_id": CustomObjectId(item.usage_status_id),
                "usage_status": item.usage_status,
            }
        ],
    )

    retrieved_item = item_repository.list(item.system_id, item.catalogue_item_id, session=session)

    database_mock.items.find.assert_called_once_with(
        {"system_id": CustomObjectId(item.system_id), "catalogue_item_id": CustomObjectId(item.catalogue_item_id)},
        session=session,
    )
    assert retrieved_item == [item]


def test_list_no_matching_result_both_filters(test_helpers, database_mock, item_repository):
    """
    Test getting items based on the provided system and catalogue item ID filters when there are no matching results in
    the database.

    Verify the `list` method properly handles the retrieval of items based on the provided
    system and catalogue item ID filters
    """
    session = MagicMock()

    # Mock `find` to return an empty list of item documents
    test_helpers.mock_find(database_mock.items, [])

    system_id = str(ObjectId())
    catalogue_item_id = str(ObjectId())
    retrieved_items = item_repository.list(system_id, catalogue_item_id, session=session)

    database_mock.items.find.assert_called_once_with(
        {"system_id": CustomObjectId(system_id), "catalogue_item_id": CustomObjectId(catalogue_item_id)},
        session=session,
    )
    assert retrieved_items == []


def test_list_two_filters_no_matching_results(test_helpers, database_mock, item_repository):
    """
    Test getting items based on the provided system and catalogue item ID filters when there are no matching results for
    one of the filters in the database.

    Verify the `list` method properly handles the retrieval of items based on the provided
    system and catalogue item ID filters
    """
    # pylint: disable=duplicate-code
    item = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of item documents
    test_helpers.mock_find(
        database_mock.items,
        [],
    )

    # catalogue item id no matching results
    rd_catalogue_item_id = str(ObjectId())
    retrieved_item = item_repository.list(item.system_id, rd_catalogue_item_id, session=session)

    database_mock.items.find.assert_called_with(
        {"system_id": CustomObjectId(item.system_id), "catalogue_item_id": CustomObjectId(rd_catalogue_item_id)},
        session=session,
    )
    assert retrieved_item == []

    # # Mock `find` to return a list of item documents
    test_helpers.mock_find(
        database_mock.items,
        [],
    )

    # system id no matching results
    rd_system_id = str(ObjectId())
    retrieved_item = item_repository.list(rd_system_id, item.catalogue_item_id, session=session)

    database_mock.items.find.assert_called_with(
        {"system_id": CustomObjectId(rd_system_id), "catalogue_item_id": CustomObjectId(item.catalogue_item_id)},
        session=session,
    )
    assert retrieved_item == []


def test_get(test_helpers, database_mock, item_repository):
    """
    Test getting an item

    Verify that the `get` method properly handles the retrieval of an item by ID.
    """
    # pylint: disable=duplicate-code
    item = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the inserted item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            **FULL_ITEM_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(item.id),
            "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
            "system_id": CustomObjectId(item.system_id),
            "usage_status_id": CustomObjectId(item.usage_status_id),
            "usage_status": item.usage_status,
        },
    )

    retrieved_item = item_repository.get(item.id, session=session)

    database_mock.items.find_one.assert_called_once_with({"_id": CustomObjectId(item.id)}, session=session)
    assert retrieved_item == item


def test_get_with_invalid_id(item_repository):
    """
    Test getting an item with an invalid ID.

    Verify the `get` method properly handles the retrieval of an item with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        item_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_non_existent_id(test_helpers, database_mock, item_repository):
    """
    Test getting an item with a non-existent ID.

    Verify the `get` method properly handles the retrieval of an item with a non-existent ID.
    """
    item_id = str(ObjectId())

    # Mock `find_one` to not return a catalogue item document
    test_helpers.mock_find_one(database_mock.items, None)

    retrieved_item = item_repository.get(item_id)

    assert retrieved_item is None
    database_mock.items.find_one.assert_called_once_with({"_id": CustomObjectId(item_id)}, session=None)


def test_update(test_helpers, database_mock, item_repository):
    """
    Test updating an item.

    Verify that the `update` method properly handles the item to be updated.
    """
    # pylint: disable=duplicate-code
    item = ItemOut(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `update_one` to return an object for the updated item document
    test_helpers.mock_update_one(database_mock.items)
    # Mock `find_one` to return the updated catalogue item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            **FULL_ITEM_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(item.id),
            "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
            "system_id": CustomObjectId(item.system_id),
            "usage_status_id": CustomObjectId(item.usage_status_id),
            "usage_status": item.usage_status,
        },
    )

    item_in = ItemIn(
        **FULL_ITEM_INFO,
        **MOCK_CREATED_MODIFIED_TIME,
        catalogue_item_id=item.catalogue_item_id,
        system_id=item.system_id,
        usage_status_id=item.usage_status_id,
        usage_status=item.usage_status,
    )
    updated_item = item_repository.update(item.id, item_in, session=session)

    database_mock.items.update_one.assert_called_once_with(
        {"_id": CustomObjectId(item.id)},
        {
            "$set": {
                "catalogue_item_id": CustomObjectId(item.catalogue_item_id),
                **item_in.model_dump(by_alias=True),
            }
        },
        session=session,
    )
    database_mock.items.find_one.assert_called_once_with({"_id": CustomObjectId(item.id)}, session=session)
    assert updated_item == item


def test_update_with_invalid_id(item_repository):
    """
    Test updating an item with Inavlid ID.

    Verify that the `update` method properly handles the update of an item with an invalid ID.
    """
    updated_item = MagicMock()
    item_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        item_repository.update(item_id, updated_item)
    assert str(exc.value) == f"Invalid ObjectId value '{item_id}'"
