# pylint: disable=duplicate-code
"""
Unit tests for the `CatalogueCategoryRepo` repository.
"""
from typing import List
from unittest.mock import Mock, call, MagicMock

import pytest
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from pymongo.results import InsertOneResult, DeleteResult

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    DuplicateRecordError,
    InvalidObjectIdError,
    ChildrenElementsExistError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo


@pytest.fixture(name="database_mock")
def fixture_database_mock() -> Mock:
    """
    Fixture to create a mock of the MongoDB database dependency and the `catalogue_categories` collection.

    :return: Mocked MongoDB database instance with the mocked `catalogue_categories` collection.
    """
    database_mock = Mock(Database)
    database_mock.catalogue_categories = Mock(Collection)
    return database_mock


@pytest.fixture(name="catalogue_category_repository")
def fixture_catalogue_category_repository(database_mock: Mock) -> CatalogueCategoryRepo:
    """
    Fixture to create a `CatalogueCategoryRepo` instance with a mocked Database dependency.

    :param database_mock: Mocked MongoDB database instance.
    :return: `CatalogueCategoryRepo` instance with the mocked dependency.
    """
    return CatalogueCategoryRepo(database_mock)


def mock_count_documents(database_mock: Mock, count: int) -> None:
    """
    Mock the `count_documents` method of the MongoDB database mock to return a specific count value.

    :param database_mock: Mocked MongoDB database instance.
    :param count: The count value to be returned by the `count_documents` method.
    """
    database_mock.catalogue_categories.count_documents.return_value = count


def mock_delete_one(database_mock: Mock, deleted_count: int) -> None:
    """
    Mock the `delete_one` method of the MongoDB database mock to return a `DeleteResult` object. The passed
    `deleted_count` values is return as the `deleted_count` attribute of the `DeleteResult` object, enabling for the
    code that relies on the `deleted_count` value to work.

    :param database_mock: Mocked MongoDB database instance.
    :param deleted_count: The value to be assigned to the `deleted_count` attribute of the `DeleteResult` object
    """
    delete_result_mock = Mock(DeleteResult)
    delete_result_mock.deleted_count = deleted_count
    database_mock.catalogue_categories.delete_one.return_value = delete_result_mock


def mock_insert_one(database_mock: Mock, inserted_id: ObjectId) -> None:
    """
    Mock the `insert_one` method of the MongoDB database mock to return an `InsertOneResult` object. The passed
    `inserted_id` value is returned as the `inserted_id` attribute of the `InsertOneResult` object, enabling for the
    code that relies on the `inserted_id` value to work.

    :param database_mock: Mocked MongoDB database instance.
    :param inserted_id: The `ObjectId` value to be assigned to the `inserted_id` attribute of the `InsertOneResult`
        object
    """
    insert_one_result_mock = Mock(InsertOneResult)
    insert_one_result_mock.inserted_id = inserted_id
    insert_one_result_mock.acknowledged = True
    database_mock.catalogue_categories.insert_one.return_value = insert_one_result_mock


def mock_find(database_mock: Mock, documents: List[dict]) -> None:
    """
    Mocks the `find` method of the MongoDB database mock to return a specific list of documents.

    :param database_mock: Mocked MongoDB database instance.
    :param documents: The list of documents to be returned by the `find` method.
    """
    cursor_mock = MagicMock(Cursor)
    cursor_mock.__iter__.return_value = iter(documents)
    database_mock.catalogue_categories.find.return_value = cursor_mock


def mock_find_one(database_mock: Mock, document: dict | None) -> None:
    """
    Mocks the `find_one` method of the MongoDB database mock to return a specific document.

    :param database_mock: Mocked MongoDB database instance.
    :param document: The document to be returned by the `find_one` method.
    """
    database_mock.catalogue_categories.find_one.return_value = document


def test_create(database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category.

    Verify that the `create` method properly handles the catalogue category to be created, finds that there is not
    a duplicate catalogue category, and creates the catalogue category.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
    )

    # Mock count_documents to return 0 (no duplicate catalogue category found within the parent catalogue category)
    mock_count_documents(database_mock, 0)
    # Mock insert_one to return an object for the inserted catalogue category document
    mock_insert_one(database_mock, CustomObjectId(catalogue_category.id))
    # Mock find_one to return the inserted catalogue category document
    mock_find_one(
        database_mock,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
        },
    )

    created_catalogue_category = catalogue_category_repository.create(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
        )
    )

    database_mock.catalogue_categories.insert_one.assert_called_once_with(
        {
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
        }
    )
    database_mock.catalogue_categories.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_category.id)})
    assert created_catalogue_category == catalogue_category


def test_create_with_parent_id(database_mock, catalogue_category_repository):
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
    )

    # Mock find_one to return the parent catalogue category document
    mock_find_one(
        database_mock,
        {
            "_id": CustomObjectId(catalogue_category.parent_id),
            "name": "Category A",
            "code": "category-a",
            "is_leaf": False,
            "path": "/category-a",
            "parent_path": "/",
            "parent_id": None,
        },
    )
    # Mock count_documents to return 0 (no duplicate catalogue category found within the parent catalogue category)
    mock_count_documents(database_mock, 0)
    # Mock insert_one to return an object for the inserted catalogue category document
    mock_insert_one(database_mock, CustomObjectId(catalogue_category.id))
    # Mock find_one to return the inserted catalogue category document
    mock_find_one(
        database_mock,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": CustomObjectId(catalogue_category.parent_id),
        },
    )

    created_catalogue_category = catalogue_category_repository.create(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
        )
    )

    database_mock.catalogue_categories.insert_one.assert_called_once_with(
        {
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": CustomObjectId(catalogue_category.parent_id),
        }
    )
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(catalogue_category.parent_id)}),
            call({"_id": CustomObjectId(catalogue_category.id)}),
        ]
    )
    assert created_catalogue_category == catalogue_category


def test_create_with_nonexistent_parent_id(database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a nonexistent parent ID.

    Verify that the `create` method properly handles a catalogue category with a nonexistent parent ID, does not find a
    parent catalogue category with an ID specified by `parent_id`, and does not create the catalogue category.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=str(ObjectId()),
    )

    # Mock find_one to not return a parent catalogue category document
    mock_find_one(database_mock, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.create(
            CatalogueCategoryIn(
                name=catalogue_category.name,
                code=catalogue_category.code,
                is_leaf=False,
                path=catalogue_category.path,
                parent_path=catalogue_category.parent_path,
                parent_id=catalogue_category.parent_id,
            )
        )
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category.parent_id}"
    database_mock.catalogue_categories.find_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.parent_id)}
    )


def test_create_with_duplicate_name_within_parent(database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.

    Verify that the `create` method properly handles a catalogue category with a duplicate name, find that there is a
    duplicate catalogue category, and does not create the catalogue category.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=True,
        path="/category-a/category-b",
        parent_path="/category-a",
        parent_id=str(ObjectId()),
    )

    # Mock find_one to return the parent catalogue category document
    mock_find_one(
        database_mock,
        {
            "_id": CustomObjectId(catalogue_category.parent_id),
            "name": "Category A",
            "code": "category-a",
            "is_leaf": False,
            "path": "/category-a",
            "parent_path": "/",
            "parent_id": None,
        },
    )
    # Mock count_documents to return 1 (duplicate catalogue category found within the parent catalogue category)
    mock_count_documents(database_mock, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_category_repository.create(
            CatalogueCategoryIn(
                name=catalogue_category.name,
                code=catalogue_category.code,
                is_leaf=catalogue_category.is_leaf,
                path=catalogue_category.path,
                parent_path=catalogue_category.parent_path,
                parent_id=catalogue_category.parent_id,
            )
        )
    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"
    database_mock.catalogue_categories.find_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.parent_id)}
    )
    database_mock.catalogue_categories.count_documents.assert_called_once_with(
        {"parent_id": CustomObjectId(catalogue_category.parent_id), "code": catalogue_category.code}
    )


def test_delete(database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category.

    Verify that the `delete` method properly handles the deletion of a catalogue category by ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock delete_one to return that one document has been deleted
    mock_delete_one(database_mock, 1)

    # Mock count_documents to return 1 (children elements not found)
    mock_count_documents(database_mock, 0)

    catalogue_category_repository.delete(catalogue_category_id)

    database_mock.catalogue_categories.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}
    )


def test_delete_with_children_elements(database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with children elements.

    Verify that the `delete` method properly handles the deletion of a catalogue category with children elements.
    """
    catalogue_category_id = str(ObjectId())

    # Mock count_documents to return 1 (children elements found)
    mock_count_documents(database_mock, 1)

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
    assert str(exc.value) == "Invalid ObjectId value"


def test_delete_with_nonexistent_id(database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with a nonexistent ID.

    Verify that the `delete` method properly handles the deletion of a catalogue category with a nonexistent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock delete_one to return that no document has been deleted
    mock_delete_one(database_mock, 0)

    # Mock count_documents to return 1 (children elements not found)
    mock_count_documents(database_mock, 0)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"
    database_mock.catalogue_categories.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}
    )


def test_get(database_mock, catalogue_category_repository):
    """
    Test getting a catalogue category.

    Verify that the `get` method properly handles the retrieval of a catalogue category by ID.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
    )

    # Mock find_one to return a catalogue category document
    mock_find_one(
        database_mock,
        {
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "path": catalogue_category.path,
            "parent_path": catalogue_category.parent_path,
            "parent_id": catalogue_category.parent_id,
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
    assert str(exc.value) == "Invalid ObjectId value"


def test_get_with_nonexistent_id(database_mock, catalogue_category_repository):
    """
    Test getting a catalogue category with a nonexistent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with a nonexistent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock find_one to not return a catalogue category document
    mock_find_one(database_mock, None)

    retrieved_catalogue_category = catalogue_category_repository.get(catalogue_category_id)

    assert retrieved_catalogue_category is None
    database_mock.catalogue_categories.find_one.assert_called_once_with({"_id": CustomObjectId(catalogue_category_id)})


def test_list(database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories.

    Verify that the `list` method properly handles the retrieval of catalogue categories without filters.
    """
    catalogue_category_a = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
    )

    catalogue_category_b = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
    )

    # Mock find to return a list of catalogue category documents
    mock_find(
        database_mock,
        [
            {
                "_id": CustomObjectId(catalogue_category_a.id),
                "name": catalogue_category_a.name,
                "code": catalogue_category_a.code,
                "is_leaf": catalogue_category_a.is_leaf,
                "path": catalogue_category_a.path,
                "parent_path": catalogue_category_a.parent_path,
                "parent_id": catalogue_category_a.parent_id,
            },
            {
                "_id": CustomObjectId(catalogue_category_b.id),
                "name": catalogue_category_b.name,
                "code": catalogue_category_b.code,
                "is_leaf": catalogue_category_b.is_leaf,
                "path": catalogue_category_b.path,
                "parent_path": catalogue_category_b.parent_path,
                "parent_id": catalogue_category_b.parent_id,
            },
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list(None, None)

    database_mock.catalogue_categories.find.assert_called_once_with({})
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_path_filter(database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided path filter.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided path
    filter.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
    )

    # Mock find to return a list of catalogue category documents
    mock_find(
        database_mock,
        [
            {
                "_id": CustomObjectId(catalogue_category.id),
                "name": catalogue_category.name,
                "code": catalogue_category.code,
                "is_leaf": catalogue_category.is_leaf,
                "path": catalogue_category.path,
                "parent_path": catalogue_category.parent_path,
                "parent_id": catalogue_category.parent_id,
            }
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list("/category-a", None)

    database_mock.catalogue_categories.find.assert_called_once_with({"path": "/category-a"})
    assert retrieved_catalogue_categories == [catalogue_category]


def test_list_with_parent_path_filter(database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided parent path filter.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided parent
    path filter.
    """
    catalogue_category_a = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
    )

    catalogue_category_b = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
    )

    # Mock find to return a list of catalogue category documents
    mock_find(
        database_mock,
        [
            {
                "_id": CustomObjectId(catalogue_category_a.id),
                "name": catalogue_category_a.name,
                "code": catalogue_category_a.code,
                "is_leaf": catalogue_category_a.is_leaf,
                "path": catalogue_category_a.path,
                "parent_path": catalogue_category_a.parent_path,
                "parent_id": catalogue_category_a.parent_id,
            },
            {
                "_id": CustomObjectId(catalogue_category_b.id),
                "name": catalogue_category_b.name,
                "code": catalogue_category_b.code,
                "is_leaf": catalogue_category_b.is_leaf,
                "path": catalogue_category_b.path,
                "parent_path": catalogue_category_b.parent_path,
                "parent_id": catalogue_category_b.parent_id,
            },
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list(None, "/")

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_path": "/"})
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_path_and_parent_path_filters(database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided path and parent path filters.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided path and
    parent path filters.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-b",
        parent_path="/",
        parent_id=None,
    )

    # Mock find to return a list of catalogue category documents
    mock_find(
        database_mock,
        [
            {
                "_id": CustomObjectId(catalogue_category.id),
                "name": catalogue_category.name,
                "code": catalogue_category.code,
                "is_leaf": catalogue_category.is_leaf,
                "path": catalogue_category.path,
                "parent_path": catalogue_category.parent_path,
                "parent_id": catalogue_category.parent_id,
            }
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list("/category-b", "/")

    database_mock.catalogue_categories.find.assert_called_once_with({"path": "/category-b", "parent_path": "/"})
    assert retrieved_catalogue_categories == [catalogue_category]


def test_list_with_path_and_parent_path_filters_no_matching_results(database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided path and parent path filters when there is no matching
    results in the database.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided path and
    parent path filters.
    """
    # Mock find to return an empty list of catalogue category documents
    mock_find(database_mock, [])

    retrieved_catalogue_categories = catalogue_category_repository.list("/category-a", "/")

    database_mock.catalogue_categories.find.assert_called_once_with({"path": "/category-a", "parent_path": "/"})
    assert retrieved_catalogue_categories == []
