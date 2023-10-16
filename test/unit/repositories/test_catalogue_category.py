# pylint: disable=too-many-lines
"""
Unit tests for the `CatalogueCategoryRepo` repository.
"""
from unittest.mock import call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    DuplicateRecordError,
    InvalidObjectIdError,
    ChildrenElementsExistError,
)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    CatalogueItemProperty,
)


def test_create(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category.

    Verify that the `create` method properly handles the catalogue category to be created, checks that there is not a
    duplicate catalogue category, and creates the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `count_documents` to return 0 (no duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )

    # pylint: disable=duplicate-code
    created_catalogue_category = catalogue_category_repository.create(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_categories.insert_one.assert_called_once_with(
        {
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        }
    )
    assert created_catalogue_category == catalogue_category


def test_create_leaf_category_without_catalogue_item_properties(
    test_helpers, database_mock, catalogue_category_repository
):
    """
    Test creating a leaf catalogue category without catalogue item properties.

    Verify that the `create` method properly handles the catalogue category to be created, checks that there is not a
    duplicate catalogue category, and creates the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `count_documents` to return 0 (no duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )

    # pylint: disable=duplicate-code
    created_catalogue_category = catalogue_category_repository.create(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=None,
        )
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_categories.insert_one.assert_called_once_with(
        {
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        }
    )
    assert created_catalogue_category == catalogue_category


def test_create_non_leaf_category_with_catalogue_item_properties(
    test_helpers, database_mock, catalogue_category_repository
):
    """
    Test creating a non-leaf catalogue category with catalogue item properties.

    Verify that the `create` method properly handles the catalogue category to be created, checks that there is not a
    duplicate catalogue category, and creates the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `count_documents` to return 0 (no duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )

    catalogue_item_properties = [
        CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
        CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
    ]
    # pylint: disable=duplicate-code
    created_catalogue_category = catalogue_category_repository.create(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_item_properties,
        )
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_categories.insert_one.assert_called_once_with(
        {
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_item_properties,
        }
    )
    assert created_catalogue_category == catalogue_category


def test_create_with_parent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a parent ID.

    Verify that the `create` method properly handles a catalogue category with a parent ID.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        is_leaf=True,
        name="Category B",
        code="category-b",
        path="/category-a/category-b",
        parent_path="/category-a",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )

    # Mock `find_one` to return the parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.parent_id),
            "name": "Category A",
            "code": "category-a",
            "is_leaf": False,
            "path": "/category-a",
            "parent_path": "/",
            "parent_id": None,
            "catalogue_item_properties": [],
        },
    )
    # Mock `count_documents` to return 0 (no duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": CustomObjectId(catalogue_category.parent_id),
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )

    # pylint: disable=duplicate-code
    created_catalogue_category = catalogue_category_repository.create(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_categories.insert_one.assert_called_once_with(
        {
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": CustomObjectId(catalogue_category.parent_id),
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        }
    )
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(catalogue_category.parent_id)}),
            call({"_id": CustomObjectId(catalogue_category.id)}),
        ]
    )
    assert created_catalogue_category == catalogue_category


def test_create_with_nonexistent_parent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a nonexistent parent ID.

    Verify that the `create` method properly handles a catalogue category with a nonexistent parent ID, does not find a
    parent catalogue category with an ID specified by `parent_id`, and does not create the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to not return a parent catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.create(
            CatalogueCategoryIn(
                name=catalogue_category.name,
                code=catalogue_category.code,
                is_leaf=False,
                path=catalogue_category.path,
                parent_path=catalogue_category.parent_path,
                parent_id=catalogue_category.parent_id,
                catalogue_item_properties=[],
            )
        )
    database_mock.catalogue_categories.insert_one.assert_not_called()
    assert str(exc.value) == f"No parent catalogue category found with ID: {catalogue_category.parent_id}"


def test_create_with_duplicate_name_within_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.

    Verify that the `create` method properly handles a catalogue category with a duplicate name, finds that there is a
    duplicate catalogue category, and does not create the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=True,
        path="/category-a/category-b",
        parent_path="/category-a",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.parent_id),
            "name": "Category A",
            "code": "category-a",
            "is_leaf": False,
            "path": "/category-a",
            "parent_path": "/",
            "parent_id": None,
            "catalogue_item_properties": [],
        },
    )
    # Mock `count_documents` to return 1 (duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        # pylint: disable=duplicate-code
        catalogue_category_repository.create(
            CatalogueCategoryIn(
                name=catalogue_category.name,
                code=catalogue_category.code,
                is_leaf=catalogue_category.is_leaf,
                path=catalogue_category.path,
                parent_path=catalogue_category.parent_path,
                parent_id=catalogue_category.parent_id,
                catalogue_item_properties=catalogue_category.catalogue_item_properties,
            )
        )
        # pylint: enable=duplicate-code
    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"
    database_mock.catalogue_categories.count_documents.assert_called_once_with(
        {"parent_id": CustomObjectId(catalogue_category.parent_id), "code": catalogue_category.code}
    )


def test_delete(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category.

    Verify that the `delete` method properly handles the deletion of a catalogue category by ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_categories, 1)

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)

    catalogue_category_repository.delete(catalogue_category_id)

    database_mock.catalogue_categories.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}
    )


def test_delete_with_children_catalogue_categories(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with children catalogue categories.

    Verify that the `delete` method properly handles the deletion of a catalogue category with children catalogue
    categories.
    """
    catalogue_category_id = str(ObjectId())

    # Mock count_documents to return 1 (children catalogue categories found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 1)
    # Mock count_documents to return 0 (children catalogue items not found)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)

    with pytest.raises(ChildrenElementsExistError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == (
        f"Catalogue category with ID {catalogue_category_id} has children elements and cannot be deleted"
    )


def test_delete_with_children_catalogue_items(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with children catalogue items.

    Verify that the `delete` method properly handles the deletion of a catalogue category with children catalogue items.
    """
    catalogue_category_id = str(ObjectId())

    # Mock count_documents to return 0 (children catalogue categories not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock count_documents to return 1 (children catalogue items found)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 1)

    with pytest.raises(ChildrenElementsExistError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == (
        f"Catalogue category with ID {catalogue_category_id} has children elements and cannot be deleted"
    )


def test_delete_with_invalid_id(catalogue_category_repository):
    """
    Test deleting a catalogue category with an invalid ID.

    Verify that the `delete` method properly handles the deletion of a catalogue category with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.delete("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_nonexistent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with a nonexistent ID.

    Verify that the `delete` method properly handles the deletion of a catalogue category with a nonexistent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `delete_one` to return that no document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_categories, 0)

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"
    database_mock.catalogue_categories.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}
    )


def test_get(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting a catalogue category.

    Verify that the `get` method properly handles the retrieval of a catalogue category by ID.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )

    retrieved_catalogue_category = catalogue_category_repository.get(catalogue_category.id)

    database_mock.catalogue_categories.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_category.id)})
    assert retrieved_catalogue_category == catalogue_category


def test_get_with_invalid_id(catalogue_category_repository):
    """
    Test getting a catalogue category with an invalid ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_nonexistent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting a catalogue category with a nonexistent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with a nonexistent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `find_one` to not return a catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    retrieved_catalogue_category = catalogue_category_repository.get(catalogue_category_id)

    assert retrieved_catalogue_category is None
    database_mock.catalogue_categories.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_category_id)})


def test_list(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories.

    Verify that the `list` method properly handles the retrieval of catalogue categories without filters.
    """
    # pylint: disable=duplicate-code
    catalogue_category_a = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )

    catalogue_category_b = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue category documents
    test_helpers.mock_find(
        database_mock.catalogue_categories,
        [
            {
                "_id": CustomObjectId(catalogue_category_a.id),
                "name": catalogue_category_a.name,
                "code": catalogue_category_a.code,
                "is_leaf": catalogue_category_a.is_leaf,
                "path": catalogue_category_a.path,
                "parent_path": catalogue_category_a.parent_path,
                "parent_id": catalogue_category_a.parent_id,
                "catalogue_item_properties": catalogue_category_a.catalogue_item_properties,
            },
            {
                "_id": CustomObjectId(catalogue_category_b.id),
                "name": catalogue_category_b.name,
                "code": catalogue_category_b.code,
                "is_leaf": catalogue_category_b.is_leaf,
                "path": catalogue_category_b.path,
                "parent_path": catalogue_category_b.parent_path,
                "parent_id": catalogue_category_b.parent_id,
                "catalogue_item_properties": catalogue_category_b.catalogue_item_properties,
            },
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list(None)

    database_mock.catalogue_categories.find.assert_called_once_with({})
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_parent_id_filter(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided parent_id filter.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided path
    filter.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue category documents
    test_helpers.mock_find(
        database_mock.catalogue_categories,
        [
            {
                "_id": CustomObjectId(catalogue_category.id),
                "name": catalogue_category.name,
                "code": catalogue_category.code,
                "is_leaf": catalogue_category.is_leaf,
                "path": catalogue_category.path,
                "parent_path": catalogue_category.parent_path,
                "parent_id": catalogue_category.parent_id,
                "catalogue_item_properties": catalogue_category.catalogue_item_properties,
            }
        ],
    )

    parent_id = ObjectId()
    retrieved_catalogue_categories = catalogue_category_repository.list(str(parent_id))

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_id": parent_id})
    assert retrieved_catalogue_categories == [catalogue_category]


def test_list_with_null_parent_id_filter(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories when the provided parent_id filter is "null"

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided parent
    path filter.
    """
    # pylint: disable=duplicate-code
    catalogue_category_a = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )

    catalogue_category_b = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue category documents
    test_helpers.mock_find(
        database_mock.catalogue_categories,
        [
            {
                "_id": CustomObjectId(catalogue_category_a.id),
                "name": catalogue_category_a.name,
                "code": catalogue_category_a.code,
                "is_leaf": catalogue_category_a.is_leaf,
                "path": catalogue_category_a.path,
                "parent_path": catalogue_category_a.parent_path,
                "parent_id": catalogue_category_a.parent_id,
                "catalogue_item_properties": catalogue_category_a.catalogue_item_properties,
            },
            {
                "_id": CustomObjectId(catalogue_category_b.id),
                "name": catalogue_category_b.name,
                "code": catalogue_category_b.code,
                "is_leaf": catalogue_category_b.is_leaf,
                "path": catalogue_category_b.path,
                "parent_path": catalogue_category_b.parent_path,
                "parent_id": catalogue_category_b.parent_id,
                "catalogue_item_properties": catalogue_category_b.catalogue_item_properties,
            },
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list("null")

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_id": None})
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_parent_id_filter_no_matching_results(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided parent_id filter when there is no matching
    results in the database.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided
    parent_path filters when there are no matching results in the database
    """
    # Mock `find` to return an empty list of catalogue category documents
    test_helpers.mock_find(database_mock.catalogue_categories, [])

    parent_id = ObjectId()
    retrieved_catalogue_categories = catalogue_category_repository.list(str(parent_id))

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_id": parent_id})
    assert retrieved_catalogue_categories == []


def test_list_with_invalid_parent_id_filter(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue_categories when given an invalid parent_id to filter on

    Verify that the `list` method properly handles the retrieval of catalogue categories when given an invalid
    parent_id filter
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.list("invalid")
    database_mock.catalogue_categories.find.assert_not_called()
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_update(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category.

    Verify that the `update` method properly handles the catalogue category to be updated, checks that the catalogue
    category does not have children elements, there is not a duplicate catalogue category, and updates the catalogue
    category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)
    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": "Category A",
            "code": "category-a",
            "is_leaf": catalogue_category.is_leaf,
            "path": "/category-a",
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )
    # Mock `count_documents` to return 0 (no duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock `update_one` to return an object for the updated catalogue category document
    test_helpers.mock_update_one(database_mock.catalogue_categories)
    # Mock `find_one` to return the updated catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
            "catalogue_item_properties": catalogue_category.catalogue_item_properties,
        },
    )

    # pylint: disable=duplicate-code
    updated_catalogue_category = catalogue_category_repository.update(
        catalogue_category.id,
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        ),
    )
    # pylint: enable=duplicate-code

    database_mock.catalogue_categories.update_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.id)},
        {
            "$set": {
                "name": catalogue_category.name,
                "code": catalogue_category.code,
                "is_leaf": catalogue_category.is_leaf,
                "path": catalogue_category.path,
                "parent_path": catalogue_category.parent_path,
                "parent_id": catalogue_category.parent_id,
                "catalogue_item_properties": catalogue_category.catalogue_item_properties,
            }
        },
    )
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(catalogue_category.id)}),
            call({"_id": CustomObjectId(catalogue_category.id)}),
        ]
    )
    assert updated_catalogue_category == catalogue_category


def test_update_with_invalid_id(catalogue_category_repository):
    """
    Test updating a catalogue category with invalid ID.

    Verify that the `update` method properly handles the update of a catalogue category with a nonexistent ID.
    """
    update_catalogue_category = CatalogueCategoryIn(
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )

    catalogue_category_id = "invalid"
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert str(exc.value) == f"Invalid ObjectId value '{catalogue_category_id}'"


def test_update_has_children_catalogue_categories(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with children catalogue categories.

    Verify that the `update` method properly handles the update of a catalogue category with children catalogue
    categories.
    """
    update_catalogue_category = CatalogueCategoryIn(
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )

    # Mock count_documents to return 1 (children catalogue categories found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 1)
    # Mock count_documents to return 0 (children catalogue items not found)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)

    catalogue_category_id = str(ObjectId())
    with pytest.raises(ChildrenElementsExistError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert (
        str(exc.value)
        == f"Catalogue category with ID {str(catalogue_category_id)} has children elements and cannot be updated"
    )


def test_update_has_children_catalogue_items(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with children catalogue items.

    Verify that the `update` method properly handles the update of a catalogue category with children catalogue items.
    """
    update_catalogue_category = CatalogueCategoryIn(
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )

    # Mock count_documents to return 0 (children catalogue categories not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    # Mock count_documents to return 1 (children catalogue items found)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 1)

    catalogue_category_id = str(ObjectId())
    with pytest.raises(ChildrenElementsExistError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert (
        str(exc.value)
        == f"Catalogue category with ID {str(catalogue_category_id)} has children elements and cannot be updated"
    )


def test_update_with_nonexistent_parent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with non-existent parent ID.

    Verify that the `update` method properly handles the update of a catalogue category with non-existent parent ID.
    """
    # pylint: disable=duplicate-code
    update_catalogue_category = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)
    # Mock `find_one` to not return a parent catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.update(str(ObjectId()), update_catalogue_category)
    assert str(exc.value) == f"No parent catalogue category found with ID: {update_catalogue_category.parent_id}"


def test_update_duplicate_name_within_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with a duplicate name within the parent catalogue category.

    Verify that the `update` method properly handles the update of a catalogue category with a duplicate name in a
    parent catalogue category.
    """
    # pylint: disable=duplicate-code
    update_catalogue_category = CatalogueCategoryIn(
        name="Category B",
        code="category-B",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)
    catalogue_category_id = str(ObjectId())
    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category_id),
            "name": "Category A",
            "code": "category-a",
            "is_leaf": update_catalogue_category.is_leaf,
            "path": "/category-a",
            "parent_path": update_catalogue_category.parent_path,
            "parent_id": update_catalogue_category.parent_id,
            "catalogue_item_properties": update_catalogue_category.catalogue_item_properties,
        },
    )
    # Mock `count_documents` to return 1 (duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"


def test_update_duplicate_name_within_new_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with a duplicate name within a new parent catalogue category.

    Verify that the `update` method properly handles the update of a catalogue category with a duplicate name in a new
    parent catalogue category.
    """
    update_catalogue_category = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-b/category-a",
        parent_path="/category-b",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[],
    )

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)
    # Mock `find_one` to return a parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": update_catalogue_category.parent_id,
            "name": "Category B",
            "code": "category-b",
            "is_leaf": False,
            "path": "/category-b",
            "parent_path": "/",
            "parent_id": None,
            "catalogue_item_properties": [],
        },
    )
    catalogue_category_id = str(ObjectId())
    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category_id),
            "name": update_catalogue_category.is_leaf,
            "code": update_catalogue_category.code,
            "is_leaf": update_catalogue_category.is_leaf,
            "path": "/category-a",
            "parent_path": "/",
            "parent_id": None,
            "catalogue_item_properties": update_catalogue_category.catalogue_item_properties,
        },
    )
    # Mock `count_documents` to return 1 (duplicate catalogue category found within the parent catalogue category)
    test_helpers.mock_count_documents(database_mock.catalogue_categories, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"
