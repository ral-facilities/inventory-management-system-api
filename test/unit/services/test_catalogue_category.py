# pylint: disable=duplicate-code
"""
Unit tests for the `CatalogueCategoryService` service.
"""
from unittest.mock import Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.models.catalogue_category import CatalogueCategoryOut, CatalogueCategoryIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.schemas.catalogue_category import CatalogueCategoryPostRequestSchema
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService


@pytest.fixture(name="catalogue_category_repository_mock")
def fixture_catalogue_category_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `CatalogueCategoryRepo` dependency.

    :return: Mocked CatalogueCategoryRepo instance.
    """
    return Mock(CatalogueCategoryRepo)


@pytest.fixture(name="catalogue_category_service")
def fixture_catalogue_category_service(catalogue_category_repository_mock: Mock) -> CatalogueCategoryService:
    """
    Fixture to create a `CatalogueCategoryService` instance with a mocked `CatalogueCategoryRepo` dependency.

    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :return: `CatalogueCategoryService` instance with the mocked dependency.
    """
    return CatalogueCategoryService(catalogue_category_repository_mock)


def test_create(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category.

    Verify that the `create` method properly handles the catalogue category to be created, generates the code and paths,
    and calls the repository's create method.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()), name="Category A", code="category-a", path="/category-a/", parent_path="/", parent_id=None
    )

    catalogue_category_repository_mock.create.return_value = catalogue_category

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(name=catalogue_category.name)
    )

    catalogue_category_repository_mock.create.assert_called_once_with(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
        )
    )
    assert created_catalogue_category == catalogue_category


def test_create_with_parent_id(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category with a parent ID.

    Verify that the `create` method properly handles a catalogue category with a parent ID.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        path="/category-a/category-b/",
        parent_path="/category-a/",
        parent_id=str(ObjectId()),
    )

    catalogue_category_repository_mock.get.return_value = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        path="/category-a/",
        parent_path="/",
        parent_id=catalogue_category.parent_id,
    )
    catalogue_category_repository_mock.create.return_value = catalogue_category

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(name=catalogue_category.name, parent_id=catalogue_category.parent_id)
    )

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.parent_id)
    catalogue_category_repository_mock.create.assert_called_once_with(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
        )
    )
    assert created_catalogue_category == catalogue_category


def test_create_with_whitespace_name(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category name containing leading/trailing/consecutive whitespaces.

    Verify that the `create` method trims the whitespace from the category name and handles it correctly.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="    Category   A         ",
        code="category-a",
        path="/category-a/",
        parent_path="/",
        parent_id=None,
    )

    catalogue_category_repository_mock.create.return_value = catalogue_category

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(name=catalogue_category.name)
    )

    catalogue_category_repository_mock.create.assert_called_once_with(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            path=catalogue_category.path,
            parent_path=catalogue_category.parent_path,
            parent_id=catalogue_category.parent_id,
        )
    )
    assert created_catalogue_category == catalogue_category
