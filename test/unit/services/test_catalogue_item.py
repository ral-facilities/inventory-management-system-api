"""
Unit tests for the `CatalogueCategoryService` service.
"""
from unittest.mock import Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    NonLeafCategoryError,
    MissingMandatoryCatalogueItemProperty,
    InvalidCatalogueItemPropertyTypeError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryOut, CatalogueItemProperty
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut, Property, CatalogueItemIn
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.schemas.catalogue_item import (
    PropertyPostRequestSchema,
    CatalogueItemPostRequestSchema,
)
from inventory_management_system_api.services.catalogue_item import CatalogueItemService


@pytest.fixture(name="catalogue_item_repository_mock")
def fixture_catalogue_item_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `CatalogueItemRepo` dependency.

    :return: Mocked CatalogueItemRepo instance.
    """
    return Mock(CatalogueItemRepo)


@pytest.fixture(name="catalogue_item_service")
def fixture_catalogue_item_service(
    catalogue_item_repository_mock: Mock, catalogue_category_repository_mock: Mock
) -> CatalogueItemService:
    """
    Fixture to create a `CatalogueItemService` instance with a mocked `CatalogueItemRepo` and `CatalogueCategoryRepo`
    dependencies.

    :param catalogue_item_repository_mock: Mocked `CatalogueItemRepo` instance.
    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :return: `CatalogueItemService` instance with the mocked dependency.
    """
    return CatalogueItemService(catalogue_item_repository_mock, catalogue_category_repository_mock)


def test_create(catalogue_item_repository_mock, catalogue_category_repository_mock, catalogue_item_service):
    """
    Test creating a catalogue item.

    Verify that the `create` method properly handles the catalogue item to be created, checks that the catalogue
    category exists and that it is a leaf category, checks for missing mandatory catalogue item properties, filters the
    matching catalogue item properties, adds the units to the supplied properties, and validates the property values.
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

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = CatalogueCategoryOut(
        id=catalogue_item.catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code
    # Mock `create` to return the created catalogue item
    catalogue_item_repository_mock.create.return_value = catalogue_item

    created_catalogue_item = catalogue_item_service.create(
        CatalogueItemPostRequestSchema(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            properties=[
                PropertyPostRequestSchema(name="Property A", value=20),
                PropertyPostRequestSchema(name="Property B", value=False),
                PropertyPostRequestSchema(name="Property C", value="20x15x10"),
            ],
        )
    )

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_item.catalogue_category_id)
    # pylint: disable=duplicate-code
    catalogue_item_repository_mock.create.assert_called_once_with(
        CatalogueItemIn(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            properties=catalogue_item.properties,
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_item == catalogue_item


def test_create_with_nonexistent_catalogue_category_id(catalogue_category_repository_mock, catalogue_item_service):
    """
    Test creating a catalogue item with a nonexistent parent ID.

    Verify that the `create` method properly handles a catalogue item with a nonexistent catalogue category ID, does not
    find a catalogue category with such ID, and does not create the catalogue item.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `get` to not return a catalogue category
    catalogue_category_repository_mock.get.return_value = None

    with pytest.raises(MissingRecordError) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category_id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property A", value=20),
                    PropertyPostRequestSchema(name="Property B", value=False),
                    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                ],
            )
        )
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)


def test_create_in_non_leaf_catalogue_category(catalogue_category_repository_mock, catalogue_item_service):
    """
    Test creating a catalogue item in a non-leaf catalogue category.

    Verify that the `create` method properly handles a catalogue item with a non-leaf catalogue category, checks that
    the catalogue category exists, finds that the catalogue category is not a leaf category, and does not create the
    catalogue item.
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

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = catalogue_category

    with pytest.raises(NonLeafCategoryError) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category.id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property A", value=20),
                    PropertyPostRequestSchema(name="Property B", value=False),
                    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                ],
            )
        )
    assert str(exc.value) == "Cannot add catalogue item to a non-leaf catalogue category"
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_without_properties(
    catalogue_item_repository_mock, catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item without properties.

    Verify that the `create` method properly handles the catalogue item to be created without properties.
    """
    # pylint: disable=duplicate-code
    catalogue_item = CatalogueItemOut(
        id=str(ObjectId()),
        catalogue_category_id=str(ObjectId()),
        name="Catalogue Item A",
        description="This is Catalogue Item A",
        properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = CatalogueCategoryOut(
        id=catalogue_item.catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[],
    )
    # Mock `create` to return the created catalogue item
    catalogue_item_repository_mock.create.return_value = catalogue_item

    created_catalogue_item = catalogue_item_service.create(
        CatalogueItemPostRequestSchema(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
        )
    )

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_item.catalogue_category_id)
    # pylint: disable=duplicate-code
    catalogue_item_repository_mock.create.assert_called_once_with(
        CatalogueItemIn(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            properties=catalogue_item.properties,
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_item == catalogue_item


def test_create_with_missing_mandatory_properties(catalogue_category_repository_mock, catalogue_item_service):
    """
    Test creating a catalogue item with missing mandatory catalogue item properties.

    Verify that the `create` method properly handles a catalogue item with missing mandatory properties, checks that
    the catalogue category exists and that it is a leaf category, finds that there are missing mandatory catalogue item
    properties, and does not create the catalogue item.
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
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = catalogue_category

    with pytest.raises(MissingMandatoryCatalogueItemProperty) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category.id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                ],
            )
        )
    assert (
        str(exc.value)
        == f"Missing mandatory catalogue item property: '{catalogue_category.catalogue_item_properties[1].name}'"
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_with_with_invalid_value_type_for_string_property(
    catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with invalid value type for a string catalogue item property.

    Verify that the `create` method properly handles a catalogue item with invalid value type for a string catalogue
    item property, checks that the catalogue category exists and that it is a leaf category, checks that there are no
    missing mandatory catalogue item properties, finds invalid value type for a string catalogue item property, and does
    not create the catalogue item.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = catalogue_category

    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category.id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property A", value=20),
                    PropertyPostRequestSchema(name="Property B", value=False),
                    PropertyPostRequestSchema(name="Property C", value=True),
                ],
            )
        )
    assert (
        str(exc.value)
        == f"Invalid value type for catalogue item property '{catalogue_category.catalogue_item_properties[2].name}'. "
        "Expected type: string."
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_with_with_invalid_value_type_for_number_property(
    catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with invalid value type for a number catalogue item property.

    Verify that the `create` method properly handles a catalogue item with invalid value type for a number catalogue
    item property, checks that the catalogue category exists and that it is a leaf category, checks that there are no
    missing mandatory catalogue item properties, finds invalid value type for a number catalogue item property, and does
    not create the catalogue item.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = catalogue_category

    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category.id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property A", value="20"),
                    PropertyPostRequestSchema(name="Property B", value=False),
                    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                ],
            )
        )
    assert (
        str(exc.value)
        == f"Invalid value type for catalogue item property '{catalogue_category.catalogue_item_properties[0].name}'. "
        "Expected type: number."
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_with_with_invalid_value_type_for_boolean_property(
    catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with invalid value type for a boolean catalogue item property.

    Verify that the `create` method properly handles a catalogue item with invalid value type for a boolean catalogue
    item property, checks that the catalogue category exists and that it is a leaf category, checks that there are no
    missing mandatory catalogue item properties, finds invalid value type for a boolean catalogue item property, and
    does not create the catalogue item.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        path="/category-a",
        parent_path="/",
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )

    # Mock `get` to return the catalogue category
    catalogue_category_repository_mock.get.return_value = catalogue_category

    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category.id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property A", value=20),
                    PropertyPostRequestSchema(name="Property B", value="False"),
                    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                ],
            )
        )
    assert (
        str(exc.value)
        == f"Invalid value type for catalogue item property '{catalogue_category.catalogue_item_properties[1].name}'. "
        "Expected type: boolean."
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_get(catalogue_item_repository_mock, catalogue_item_service):
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

    # Mock `get` to return a catalogue item
    catalogue_item_repository_mock.get.return_value = catalogue_item

    retrieved_catalogue_item = catalogue_item_service.get(catalogue_item.id)

    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item.id)
    assert retrieved_catalogue_item == catalogue_item


def test_get_with_nonexistent_id(catalogue_item_repository_mock, catalogue_item_service):
    """
    Test getting a catalogue item with a nonexistent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue item with a nonexistent ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `get` to not return a catalogue item
    catalogue_item_repository_mock.get.return_value = None

    retrieved_catalogue_item = catalogue_item_service.get(catalogue_item_id)

    assert retrieved_catalogue_item is None
    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)


def test_list(catalogue_item_repository_mock, catalogue_item_service):
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

    # Mock `list` to return a list of catalogue items
    catalogue_item_repository_mock.list.return_value = [catalogue_item_a, catalogue_item_b]

    retrieved_catalogue_items = catalogue_item_service.list(None)

    catalogue_item_repository_mock.list.assert_called_once_with(None)
    assert retrieved_catalogue_items == [catalogue_item_a, catalogue_item_b]


def test_list_with_catalogue_category_id_filter(catalogue_item_repository_mock, catalogue_item_service):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.

    Verify that the `list` method properly handles the retrieval of catalogue items based on the provided catalogue
    category ID filter.
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

    # Mock `list` to return a list of catalogue items
    catalogue_item_repository_mock.list.return_value = [catalogue_item]

    retrieved_catalogue_items = catalogue_item_service.list(catalogue_item.catalogue_category_id)

    catalogue_item_repository_mock.list.assert_called_once_with(catalogue_item.catalogue_category_id)
    assert retrieved_catalogue_items == [catalogue_item]


def test_list_with_catalogue_category_id_filter_no_matching_results(
    catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test getting catalogue items based on the provided catalogue category ID filter when there is no matching results in
    the database.

    Verify that the `list` method properly handles the retrieval of catalogue items based on the provided catalogue
    category ID filter.
    """
    # Mock `list` to return an empty list of catalogue item documents
    catalogue_item_repository_mock.list.return_value = []

    catalogue_category_id = str(ObjectId())
    retrieved_catalogue_items = catalogue_item_service.list(catalogue_category_id)

    catalogue_item_repository_mock.list.assert_called_once_with(catalogue_category_id)
    assert retrieved_catalogue_items == []
