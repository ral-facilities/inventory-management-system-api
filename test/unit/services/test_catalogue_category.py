# pylint: disable=duplicate-code
"""
Unit tests for the `CatalogueCategoryService` service.
"""
from unittest.mock import Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import LeafCategoryError
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryOut,
    CatalogueCategoryIn,
    CatalogueItemProperty,
)
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
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )

    # Mock `create` to return the created catalogue category
    catalogue_category_repository_mock.create.return_value = catalogue_category

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(
            name=catalogue_category.name,
            is_leaf=catalogue_category.is_leaf,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )

    catalogue_category_repository_mock.create.assert_called_once_with(
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
        is_leaf=True,
        path="/category-a/category-b",
        parent_path="/category-a",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )

    # Mock `get` to return the parent catalogue category
    catalogue_category_repository_mock.get.return_value = CatalogueCategoryOut(
        id=catalogue_category.parent_id,
        name="Category A",
        code="category-a",
        is_leaf=False,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # Mock `create` to return the created catalogue category
    catalogue_category_repository_mock.create.return_value = catalogue_category

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(
            name=catalogue_category.name,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.parent_id)
    catalogue_category_repository_mock.create.assert_called_once_with(
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
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )

    # Mock `create` to return the created catalogue category
    catalogue_category_repository_mock.create.return_value = catalogue_category

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(
            name=catalogue_category.name,
            is_leaf=catalogue_category.is_leaf,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )

    catalogue_category_repository_mock.create.assert_called_once_with(
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
    assert created_catalogue_category == catalogue_category


def test_create_with_leaf_parent_catalogue_category(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category in a leaf parent catalogue category.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        path="/category-a/category-b",
        parent_path="/category-a",
        parent_id=str(ObjectId()),
        catalogue_item_properties=[],
    )

    # Mock `get` to return the parent catalogue category
    catalogue_category_repository_mock.get.return_value = CatalogueCategoryOut(
        id=catalogue_category.parent_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )

    with pytest.raises(LeafCategoryError) as exc:
        catalogue_category_service.create(
            CatalogueCategoryPostRequestSchema(
                name=catalogue_category.name,
                is_leaf=catalogue_category.is_leaf,
                parent_id=catalogue_category.parent_id,
                catalogue_item_properties=catalogue_category.catalogue_item_properties,
            )
        )
    assert str(exc.value) == "Cannot add catalogue category to a leaf parent catalogue category"
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.parent_id)


def test_delete(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test deleting a catalogue category.

    Verify that the `delete` method properly handles the deletion of a catalogue category by ID.
    """
    catalogue_category_id = str(ObjectId())

    catalogue_category_service.delete(catalogue_category_id)

    catalogue_category_repository_mock.delete.assert_called_once_with(catalogue_category_id)


def test_get(catalogue_category_repository_mock, catalogue_category_service):
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
        catalogue_item_properties=[],
    )

    # Mock `get` to return a catalogue category
    catalogue_category_repository_mock.get.return_value = catalogue_category

    retrieved_catalogue_category = catalogue_category_service.get(catalogue_category.id)

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)
    assert retrieved_catalogue_category == catalogue_category


def test_get_with_nonexistent_id(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test getting a catalogue category with a nonexistent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with a nonexistent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `get` to not return a catalogue category
    catalogue_category_repository_mock.get.return_value = None

    retrieved_catalogue_category = catalogue_category_service.get(catalogue_category_id)

    assert retrieved_catalogue_category is None
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)


def test_list(catalogue_category_repository_mock, catalogue_category_service):
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

    # Mock `list` to return a list of catalogue categories
    catalogue_category_repository_mock.list.return_value = [catalogue_category_a, catalogue_category_b]

    retrieved_catalogue_categories = catalogue_category_service.list(None, None)

    catalogue_category_repository_mock.list.assert_called_once_with(None, None)
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_path_filter(catalogue_category_repository_mock, catalogue_category_service):
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
        catalogue_item_properties=[],
    )

    # Mock `list` to return a list of catalogue categories
    catalogue_category_repository_mock.list.return_value = [catalogue_category]

    retrieved_catalogue_categories = catalogue_category_service.list("/category-a", None)

    catalogue_category_repository_mock.list.assert_called_once_with("/category-a", None)
    assert retrieved_catalogue_categories == [catalogue_category]


def test_list_with_parent_path_filter(catalogue_category_repository_mock, catalogue_category_service):
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

    # Mock `list` to return a list of catalogue categories
    catalogue_category_repository_mock.list.return_value = [catalogue_category_a, catalogue_category_b]

    retrieved_catalogue_categories = catalogue_category_service.list(None, "/")

    catalogue_category_repository_mock.list.assert_called_once_with(None, "/")
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_path_and_parent_path_filters(catalogue_category_repository_mock, catalogue_category_service):
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
        catalogue_item_properties=[],
    )

    # Mock `list` to return a list of catalogue categories
    catalogue_category_repository_mock.list.return_value = [catalogue_category]

    retrieved_catalogue_categories = catalogue_category_service.list("/category-b", "/")

    catalogue_category_repository_mock.list.assert_called_once_with("/category-b", "/")
    assert retrieved_catalogue_categories == [catalogue_category]


def test_list_with_path_and_parent_path_filters_no_matching_results(
    catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test getting catalogue categories based on the provided path and parent path filters when there is no matching
    results in the database.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided path and
    parent path filters.
    """
    # Mock `list` to return an empty list of catalogue categories
    catalogue_category_repository_mock.list.return_value = []

    retrieved_catalogue_categories = catalogue_category_service.list("/category-b", "/")

    catalogue_category_repository_mock.list.assert_called_once_with("/category-b", "/")
    assert retrieved_catalogue_categories == []
