"""
Unit tests for the `CatalogueItemRepo` repository.
"""
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.catalogue_item import (
    CatalogueItemOut,
    Property,
    CatalogueItemIn,
    Manufacturer,
)


def test_create(test_helpers, database_mock, catalogue_item_repository):
    """
    Test creating a catalogue item.

    Verify that the `create` method properly handles the catalogue item to be created, checks that there is not a
    duplicate catalogue item, and creates the catalogue item.
    """
    # pylint: disable=duplicate-code
    catalogue_item = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        name="Catalogue Item A",
        description="This is Catalogue Item A",
        properties=[
            Property(name="Property A", value=20, unit="mm"),
            Property(name="Property B", value=False),
            Property(name="Property C", value="20x15x10", unit="cm"),
        ],
        manufacturer=Manufacturer(
            name="Manufacturer A",
            address="1 Address, City, Country, Postcode",
            url="https://www.manufacturer-a.co.uk",
        ),
    )
    # pylint: enable=duplicate-code

    # Mock `count_documents` to return 0 (no duplicate catalogue item found within the catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)
    # Mock `insert_one` to return an object for the inserted catalogue item document
    test_helpers.mock_insert_one(database_mock.catalogue_items, CustomObjectId(catalogue_item.id))
    # Mock `find_one` to return the inserted catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            "_id": CustomObjectId(catalogue_item.id),
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            "name": catalogue_item.name,
            "description": catalogue_item.description,
            "properties": catalogue_item.properties,
            "manufacturer": catalogue_item.manufacturer,
        },
    )

    # pylint: disable=duplicate-code
    created_catalogue_item = catalogue_item_repository.create(
        CatalogueItemIn(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            properties=catalogue_item.properties,
            manufacturer=catalogue_item.manufacturer,
        )
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_items.insert_one.assert_called_once_with(
        {
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            "name": catalogue_item.name,
            "description": catalogue_item.description,
            "properties": [prop.model_dump() for prop in catalogue_item.properties],
            "manufacturer": catalogue_item.manufacturer.model_dump(),
        }
    )
    assert created_catalogue_item == catalogue_item


def test_delete(test_helpers, database_mock, catalogue_item_repository):
    """
    Test deleting a catalogue item.

    Verify that the `delete` method properly handles the deletion of a catalogue item by ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_items, 1)

    # pylint: disable=fixme
    # TODO - (when the relevant item logic is implemented) mock it so that no children items are returned

    catalogue_item_repository.delete(catalogue_item_id)

    database_mock.catalogue_items.delete_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item_id)})


def test_delete_with_children_items():
    """
    Test deleting a catalogue item with children items.

    Verify that the `delete` method properly handles the deletion of a catalogue item with children items.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant item logic is implemented


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

    # pylint: disable=fixme
    # TODO - (when the relevant item logic is implemented) mock it so that no children items are returned

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
        name="Catalogue Item A",
        description="This is Catalogue Item A",
        properties=[
            Property(name="Property A", value=20, unit="mm"),
            Property(name="Property B", value=False),
            Property(name="Property C", value="20x15x10", unit="cm"),
        ],
        manufacturer=Manufacturer(
            name="Manufacturer A",
            address="1 Address, City, Country, Postcode",
            url="https://www.manufacturer-a.co.uk",
        ),
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            "_id": CustomObjectId(catalogue_item.id),
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            "name": catalogue_item.name,
            "description": catalogue_item.description,
            "properties": catalogue_item.properties,
            "manufacturer": catalogue_item.manufacturer,
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
    # pylint: disable=duplicate-code
    catalogue_item_a = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        name="Catalogue Item A",
        description="This is Catalogue Item A",
        properties=[
            Property(name="Property A", value=20, unit="mm"),
            Property(name="Property B", value=False),
            Property(name="Property C", value="20x15x10", unit="cm"),
        ],
        manufacturer=Manufacturer(
            name="Manufacturer A",
            address="1 Address, City, Country, Postcode",
            url="https://www.manufacturer-a.co.uk",
        ),
    )

    catalogue_item_b = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        name="Catalogue Item B",
        description="This is Catalogue Item B",
        properties=[Property(name="Property A", value=True)],
        manufacturer=Manufacturer(
            name="Manufacturer A",
            address="1 Address, City, Country, Postcode",
            url="https://www.manufacturer-a.co.uk",
        ),
    )
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue item documents
    test_helpers.mock_find(
        database_mock.catalogue_items,
        [
            {
                "_id": CustomObjectId(catalogue_item_a.id),
                "catalogue_category_id": CustomObjectId(catalogue_item_a.catalogue_category_id),
                "name": catalogue_item_a.name,
                "description": catalogue_item_a.description,
                "properties": catalogue_item_a.properties,
                "manufacturer": catalogue_item_a.manufacturer,
            },
            {
                "_id": CustomObjectId(catalogue_item_b.id),
                "catalogue_category_id": CustomObjectId(catalogue_item_b.catalogue_category_id),
                "name": catalogue_item_b.name,
                "description": catalogue_item_b.description,
                "properties": catalogue_item_b.properties,
                "manufacturer": catalogue_item_b.manufacturer,
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
    catalogue_item = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        name="Catalogue Item A",
        description="This is Catalogue Item A",
        properties=[
            Property(name="Property A", value=20, unit="mm"),
            Property(name="Property B", value=False),
            Property(name="Property C", value="20x15x10", unit="cm"),
        ],
        manufacturer=Manufacturer(
            name="Manufacturer A",
            address="1 Address, City, Country, Postcode",
            url="https://www.manufacturer-a.co.uk",
        ),
    )

    # Mock `find` to return a list of catalogue item documents
    test_helpers.mock_find(
        database_mock.catalogue_items,
        [
            {
                "_id": CustomObjectId(catalogue_item.id),
                "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
                "name": catalogue_item.name,
                "description": catalogue_item.description,
                "properties": catalogue_item.properties,
                "manufacturer": catalogue_item.manufacturer,
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
    # pylint: disable=duplicate-code
    catalogue_item_info = {
        "name": "Catalogue Item B",
        "description": "This is Catalogue Item B",
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "url": "https://www.manufacturer-a.co.uk",
        },
    }
    # pylint: enable=duplicate-code
    catalogue_item = CatalogueItemOut(id=str(ObjectId()), catalogue_category_id=str(ObjectId()), **catalogue_item_info)

    # Mock `update_one` to return an object for the updated catalogue item document
    test_helpers.mock_update_one(database_mock.catalogue_items)
    # Mock `find_one` to return the updated catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            "_id": CustomObjectId(catalogue_item.id),
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            **catalogue_item_info,
        },
    )

    catalogue_item_in = CatalogueItemIn(
        catalogue_category_id=catalogue_item.catalogue_category_id, **catalogue_item_info
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


def test_update_has_child_items():
    """
    Test updating a catalogue item with child items.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant item logic is implemented.
