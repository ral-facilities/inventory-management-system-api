# pylint: disable=duplicate-code
"""
Unit tests for the `CatalogueCategoryRepo` repository.
"""
from unittest.mock import Mock, call

import pytest
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import MissingRecordError, DuplicateRecordError
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


def mock_insert_one(database_mock: Mock, inserted_id: ObjectId) -> None:
    """
    Mock the `insert_one` method of the MongoDB database mock to return an `InsertOneResult` object. The passed
    `inserted_id` value is returned as the `inserted_id` attribute of the `InsertOneResult` object, enabling for the
    code that relies on the `inserted_id` value to work.

    :param database_mock: Mocked MongoDB database instance.
    :param inserted_id: The `ObjectId` value to be assigned to the `inserted_id` attribute of the `InsertOneResult`
        object
    """
    database_mock.catalogue_categories.insert_one.return_value = InsertOneResult(
        inserted_id=inserted_id, acknowledged=True
    )


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
        path="/category-a/",
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
        path="/category-a/category-b/",
        parent_path="/category-a/",
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
            "path": "/category-a/",
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
        path="/category-a/",
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
    assert str(exc.value) == f"No catalogue category found with id: {catalogue_category.parent_id}"
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
        path="/category-a/category-b/",
        parent_path="/category-a/",
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
            "path": "/category-a/",
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
