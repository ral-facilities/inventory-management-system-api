"""
Module for providing common test configuration, test fixtures, and helper functions.
"""
from typing import List, Type
from unittest.mock import Mock, MagicMock

import pytest
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from pymongo.results import DeleteResult, InsertOneResult

from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo


@pytest.fixture(name="database_mock")
def fixture_database_mock() -> Mock:
    """
    Fixture to create a mock of the MongoDB database dependency and the `catalogue_categories` and `catalogue_items`
    collections.

    :return: Mocked MongoDB database instance with the mocked `catalogue_categories` and `catalogue_items` collections.
    """
    database_mock = Mock(Database)
    database_mock.catalogue_categories = Mock(Collection)
    database_mock.catalogue_items = Mock(Collection)
    return database_mock


@pytest.fixture(name="catalogue_category_repository")
def fixture_catalogue_category_repository(database_mock: Mock) -> CatalogueCategoryRepo:
    """
    Fixture to create a `CatalogueCategoryRepo` instance with a mocked Database dependency.

    :param database_mock: Mocked MongoDB database instance.
    :return: `CatalogueCategoryRepo` instance with the mocked dependency.
    """
    return CatalogueCategoryRepo(database_mock)


@pytest.fixture(name="catalogue_item_repository")
def fixture_catalogue_item_repository(database_mock: Mock) -> CatalogueItemRepo:
    """
    Fixture to create a `CatalogueItemRepo` instance with a mocked Database dependency.

    :param database_mock: Mocked MongoDB database instance.
    :return: `CatalogueItemRepo` instance with the mocked dependency.
    """
    return CatalogueItemRepo(database_mock)


class TestHelpers:
    """
    A utility class containing common helper methods for tests.

    This class provides a set of static methods that encapsulate common functionality frequently used in tests.
    """

    @staticmethod
    def mock_count_documents(collection_mock: Mock, count: int) -> None:
        """
        Mock the `count_documents` method of the MongoDB database collection mock to return a specific count value.

        :param collection_mock: Mocked MongoDB database collection instance.
        :param count: The count value to be returned by the `count_documents` method.
        """
        collection_mock.count_documents.return_value = count

    @staticmethod
    def mock_delete_one(collection_mock: Mock, deleted_count: int) -> None:
        """
        Mock the `delete_one` method of the MongoDB database collection mock to return a `DeleteResult` object. The
        passed `deleted_count` value is returned as the `deleted_count` attribute of the `DeleteResult` object, enabling
        for the code that relies on the `deleted_count` value to work.

        :param collection_mock: Mocked MongoDB database collection instance.
        :param deleted_count: The value to be assigned to the `deleted_count` attribute of the `DeleteResult` object
        """
        delete_result_mock = Mock(DeleteResult)
        delete_result_mock.deleted_count = deleted_count
        collection_mock.delete_one.return_value = delete_result_mock

    @staticmethod
    def mock_insert_one(collection_mock: Mock, inserted_id: ObjectId) -> None:
        """
        Mock the `insert_one` method of the MongoDB database collection mock to return an `InsertOneResult` object. The
        passed `inserted_id` value is returned as the `inserted_id` attribute of the `InsertOneResult` object, enabling
        for the code that relies on the `inserted_id` value to work.

        :param collection_mock: Mocked MongoDB database collection instance.
        :param inserted_id: The `ObjectId` value to be assigned to the `inserted_id` attribute of the `InsertOneResult`
            object
        """
        insert_one_result_mock = Mock(InsertOneResult)
        insert_one_result_mock.inserted_id = inserted_id
        insert_one_result_mock.acknowledged = True
        collection_mock.insert_one.return_value = insert_one_result_mock

    @staticmethod
    def mock_find(collection_mock: Mock, documents: List[dict]) -> None:
        """
        Mocks the `find` method of the MongoDB database collection mock to return a specific list of documents.

        :param collection_mock: Mocked MongoDB database collection instance.
        :param documents: The list of documents to be returned by the `find` method.
        """
        cursor_mock = MagicMock(Cursor)
        cursor_mock.__iter__.return_value = iter(documents)
        collection_mock.find.return_value = cursor_mock

    @staticmethod
    def mock_find_one(collection_mock: Mock, document: dict | None) -> None:
        """
        Mocks the `find_one` method of the MongoDB database collection mock to return a specific document.

        :param collection_mock: Mocked MongoDB database collection instance.
        :param document: The document to be returned by the `find_one` method.
        """
        collection_mock.find_one.return_value = document


@pytest.fixture(name="test_helpers")
def fixture_test_helpers() -> Type[TestHelpers]:
    """
    Fixture to provide a TestHelpers class.
    """
    return TestHelpers