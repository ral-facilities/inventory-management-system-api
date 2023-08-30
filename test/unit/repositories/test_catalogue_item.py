"""
Unit tests for the `CatalogueItemRepo` repository.
"""
import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DuplicateRecordError
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut, Property, CatalogueItemIn


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
            "catalogue_category_id": catalogue_item.catalogue_category_id,
            "name": catalogue_item.name,
            "description": catalogue_item.description,
            "properties": catalogue_item.properties,
        },
    )

    # pylint: disable=duplicate-code
    created_catalogue_item = catalogue_item_repository.create(
        CatalogueItemIn(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            properties=catalogue_item.properties,
        )
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_items.insert_one.assert_called_once_with(
        {
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
            "name": catalogue_item.name,
            "description": catalogue_item.description,
            "properties": catalogue_item.properties,
        }
    )

    database_mock.catalogue_items.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_item.id)})
    assert created_catalogue_item == catalogue_item


def test_create_with_duplicate_name_within_catalogue_category(test_helpers, database_mock, catalogue_item_repository):
    """
    Test creating a catalogue item with a duplicate name within the catalogue category.

    Verify that the `create` method properly handles a catalogue item with a duplicate name, finds that there is a
    duplicate catalogue item, and does not create the catalogue item.
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
    )

    # Mock `count_documents` to return 1 (duplicate catalogue item found within the catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_item_repository.create(
            CatalogueItemIn(
                catalogue_category_id=catalogue_item.catalogue_category_id,
                name=catalogue_item.name,
                description=catalogue_item.description,
                properties=catalogue_item.properties,
            )
        )
    assert str(exc.value) == "Duplicate catalogue item found within the catalogue category"
    database_mock.catalogue_items.count_documents.assert_called_once_with(
        {"catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id), "name": catalogue_item.name}
    )
