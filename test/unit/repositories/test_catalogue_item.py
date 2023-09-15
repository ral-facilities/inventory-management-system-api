"""
Unit tests for the `CatalogueItemRepo` repository.
"""
import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DuplicateRecordError, InvalidObjectIdError
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
            "catalogue_category_id": CustomObjectId(catalogue_item.catalogue_category_id),
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
    )

    catalogue_item_b = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        name="Catalogue Item B",
        description="This is Catalogue Item B",
        properties=[Property(name="Property A", value=True)],
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
            },
            {
                "_id": CustomObjectId(catalogue_item_b.id),
                "catalogue_category_id": CustomObjectId(catalogue_item_b.catalogue_category_id),
                "name": catalogue_item_b.name,
                "description": catalogue_item_b.description,
                "properties": catalogue_item_b.properties,
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
