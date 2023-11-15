# pylint: disable=too-many-lines
"""
Unit tests for the `CatalogueCategoryService` service.
"""

from unittest.mock import MagicMock
import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    NonLeafCategoryError,
    MissingMandatoryCatalogueItemProperty,
    InvalidCatalogueItemPropertyTypeError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryOut, CatalogueItemProperty
from inventory_management_system_api.models.catalogue_item import (
    CatalogueItemOut,
    Property,
    CatalogueItemIn,
)
from inventory_management_system_api.models.manufacturer import ManufacturerOut
from inventory_management_system_api.schemas.catalogue_item import (
    PropertyPostRequestSchema,
    CatalogueItemPostRequestSchema,
    CatalogueItemPatchRequestSchema,
)
from inventory_management_system_api.schemas.manufacturer import AddressSchema


def test_create(
    test_helpers,
    catalogue_item_repository_mock,
    catalogue_category_repository_mock,
    manufacturer_repository_mock,
    catalogue_item_service,
):
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
        manufacturer_id=str(ObjectId()),
    )

    # Mock `get` to return the catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_item.catalogue_category_id,
            name="Category A",
            code="category-a",
            is_leaf=True,
            parent_id=None,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
                CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
                CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
            ],
        ),
    )
    test_helpers.mock_get(
        manufacturer_repository_mock,
        ManufacturerOut(
            id=catalogue_item.manufacturer_id,
            name="Manufacturer A",
            code="manufacturer-a",
            url="https://test.co.uk",
            address=AddressSchema(
                building_number="1",
                street_name="Example Street",
                postcode="AB1 2CD",
            ),
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `create` to return the created catalogue item
    test_helpers.mock_create(catalogue_item_repository_mock, catalogue_item)

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
            manufacturer_id=catalogue_item.manufacturer_id,
        )
    )

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_item.catalogue_category_id)
    # pylint: disable=duplicate-code
    catalogue_item_repository_mock.create.assert_called_once_with(
        CatalogueItemIn(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            properties=[prop.model_dump() for prop in catalogue_item.properties],
            manufacturer_id=catalogue_item.manufacturer_id,
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_item == catalogue_item


def test_create_with_nonexistent_catalogue_category_id(
    test_helpers, catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with a nonexistent parent ID.

    Verify that the `create` method properly handles a catalogue item with a nonexistent catalogue category ID, does not
    find a catalogue category with such ID, and does not create the catalogue item.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `get` to not return a catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, None)

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
                manufacturer_id=str(ObjectId()),
            ),
        )

    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)


def test_create_with_nonexistent_manufacturer_id(
    test_helpers, catalogue_category_repository_mock, manufacturer_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with a manufacturer id that is nonexistent
    """

    catalogue_category_id = str(ObjectId())

    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            name="Category A",
            code="category-a",
            is_leaf=True,
            parent_id=None,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
                CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
                CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
            ],
        ),
    )
    manufacturer_id = str(ObjectId())
    test_helpers.mock_get(manufacturer_repository_mock, None)

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
                manufacturer_id=manufacturer_id,
            ),
        )
    assert str(exc.value) == f"No manufacturer found with ID: {manufacturer_id}"


def test_create_in_non_leaf_catalogue_category(
    test_helpers, catalogue_category_repository_mock, catalogue_item_service
):
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
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

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
                manufacturer_id=str(ObjectId()),
            ),
        )

    assert str(exc.value) == "Cannot add catalogue item to a non-leaf catalogue category"
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_without_properties(
    test_helpers, catalogue_item_repository_mock, catalogue_category_repository_mock, catalogue_item_service
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
        manufacturer_id=str(ObjectId()),
    )

    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_item.catalogue_category_id,
            name="Category A",
            code="category-a",
            is_leaf=True,
            parent_id=None,
            catalogue_item_properties=[],
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `create` to return the created catalogue item
    test_helpers.mock_create(catalogue_item_repository_mock, catalogue_item)

    created_catalogue_item = catalogue_item_service.create(
        CatalogueItemPostRequestSchema(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            name=catalogue_item.name,
            description=catalogue_item.description,
            manufacturer_id=catalogue_item.manufacturer_id,
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
            manufacturer_id=catalogue_item.manufacturer_id,
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_item == catalogue_item


def test_create_with_missing_mandatory_properties(
    test_helpers, catalogue_category_repository_mock, catalogue_item_service
):
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
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

    with pytest.raises(MissingMandatoryCatalogueItemProperty) as exc:
        catalogue_item_service.create(
            CatalogueItemPostRequestSchema(
                catalogue_category_id=catalogue_category.id,
                name="Catalogue Item A",
                description="This is Catalogue Item A",
                properties=[
                    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                ],
                manufacturer_id=str(ObjectId()),
            ),
        )

    assert (
        str(exc.value)
        == f"Missing mandatory catalogue item property: '{catalogue_category.catalogue_item_properties[1].name}'"
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_with_with_invalid_value_type_for_string_property(
    test_helpers, catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with invalid value type for a string catalogue item property.

    Verify that the `create` method properly handles a catalogue item with invalid value type for a string catalogue
    item property, checks that the catalogue category exists and that it is a leaf category, checks that there are no
    missing mandatory catalogue item properties, finds invalid value type for a string catalogue item property, and does
    not create the catalogue item.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

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
                manufacturer_id=str(ObjectId()),
            ),
        )

    assert (
        str(exc.value)
        == f"Invalid value type for catalogue item property '{catalogue_category.catalogue_item_properties[2].name}'. "
        "Expected type: string."
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_with_with_invalid_value_type_for_number_property(
    test_helpers, catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with invalid value type for a number catalogue item property.

    Verify that the `create` method properly handles a catalogue item with invalid value type for a number catalogue
    item property, checks that the catalogue category exists and that it is a leaf category, checks that there are no
    missing mandatory catalogue item properties, finds invalid value type for a number catalogue item property, and does
    not create the catalogue item.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

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
                manufacturer_id=str(ObjectId()),
            )
        )
    assert (
        str(exc.value)
        == f"Invalid value type for catalogue item property '{catalogue_category.catalogue_item_properties[0].name}'. "
        "Expected type: number."
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_create_with_with_invalid_value_type_for_boolean_property(
    test_helpers, catalogue_category_repository_mock, catalogue_item_service
):
    """
    Test creating a catalogue item with invalid value type for a boolean catalogue item property.

    Verify that the `create` method properly handles a catalogue item with invalid value type for a boolean catalogue
    item property, checks that the catalogue category exists and that it is a leaf category, checks that there are no
    missing mandatory catalogue item properties, finds invalid value type for a boolean catalogue item property, and
    does not create the catalogue item.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

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
                manufacturer_id=str(ObjectId()),
            )
        )
    assert (
        str(exc.value)
        == f"Invalid value type for catalogue item property '{catalogue_category.catalogue_item_properties[1].name}'. "
        "Expected type: boolean."
    )
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


def test_delete(catalogue_item_repository_mock, catalogue_item_service):
    """
    Test deleting a catalogue item.

    Verify that the `delete` method properly handles the deletion of a catalogue item by ID.
    """
    catalogue_item_id = str(ObjectId)

    catalogue_item_service.delete(catalogue_item_id)

    catalogue_item_repository_mock.delete.assert_called_once_with(catalogue_item_id)


def test_get(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
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
        manufacturer_id=str(ObjectId()),
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, catalogue_item)

    retrieved_catalogue_item = catalogue_item_service.get(catalogue_item.id)

    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item.id)
    assert retrieved_catalogue_item == catalogue_item


def test_get_with_non_existent_id(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
    """
    Test getting a catalogue item with a non-existent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue item with a non-existent ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, None)

    retrieved_catalogue_item = catalogue_item_service.get(catalogue_item_id)

    assert retrieved_catalogue_item is None
    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)


def test_list(catalogue_item_repository_mock, catalogue_item_service):
    """
    Test listing catalogue items

    Verify that the `list` method properly calls the repository function with any passed filters
    """

    catalogue_category_id = MagicMock()

    result = catalogue_item_service.list(catalogue_category_id=catalogue_category_id)

    catalogue_item_repository_mock.list.assert_called_once_with(catalogue_category_id)
    assert result == catalogue_item_repository_mock.list.return_value


def test_update(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
    """
    Test updating a catalogue item.

    Verify that the `update` method properly handles the catalogue item to be updated.
    """
    # pylint: disable=duplicate-code
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
        "manufacturer_id": str(ObjectId()),
    }
    # pylint: enable=duplicate-code
    full_catalogue_item_info = {
        **catalogue_item_info,
        "name": "Catalogue Item B",
        "description": "This is Catalogue Item B",
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            name="Catalogue Item A",
            description="This is Catalogue Item A",
            **catalogue_item_info,
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(name=catalogue_item.name, description=catalogue_item.description),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_with_nonexistent_id(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
    """
    Test updating a catalogue item with a non-existent ID.

    Verify that the `update` method properly handles the catalogue category to be updated with a non-existent ID.
    """
    # Mock `get` to return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, None)

    catalogue_item_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        catalogue_item_service.update(catalogue_item_id, CatalogueItemPatchRequestSchema(properties=[]))
    assert str(exc.value) == f"No catalogue item found with ID: {catalogue_item_id}"


def test_update_change_catalogue_category_id_same_defined_properties_without_supplied_properties(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test moving a catalogue item to another catalogue category that has the same defined catalogue item properties when
    no properties are supplied.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
        "manufacturer_id": str(ObjectId()),
    }
    full_catalogue_item_info = {
        **catalogue_item_info,
        "catalogue_category_id": str(ObjectId()),
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            catalogue_category_id=str(ObjectId()),
            **catalogue_item_info,
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id, CatalogueItemPatchRequestSchema(catalogue_category_id=catalogue_item.catalogue_category_id)
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_change_catalogue_category_id_same_defined_properties_with_supplied_properties(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test moving a catalogue item to another catalogue category that has the same defined catalogue item properties when
    properties are supplied.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
    }
    full_catalogue_item_info = {
        **catalogue_item_info,
        "catalogue_category_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            catalogue_category_id=str(ObjectId()),
            properties=[
                Property(name="Property A", value=1, unit="mm"),
                Property(name="Property B", value=True),
                Property(name="Property C", value="1x1x1", unit="cm"),
            ],
            **catalogue_item_info,
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            properties=[{"name": prop.name, "value": prop.value} for prop in catalogue_item.properties],
        ),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_change_catalogue_category_id_different_defined_properties_without_supplied_properties(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test moving a catalogue item to another catalogue category that has different defined catalogue item properties when
    no properties are supplied.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            catalogue_category_id=str(ObjectId()),
            **catalogue_item_info,
        ),
    )
    catalogue_category_id = str(ObjectId())
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            name="Category A",
            code="category-a",
            is_leaf=True,
            path="/category-a",
            parent_path="/",
            parent_id=None,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="boolean", mandatory=True),
            ],
        ),
    )

    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(catalogue_category_id=catalogue_category_id),
        )
    assert str(exc.value) == "Invalid value type for catalogue item property 'Property A'. Expected type: boolean."


def test_update_change_catalogue_category_id_different_defined_properties_with_supplied_properties(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test moving a catalogue item to another catalogue category that has different defined catalogue item properties when
    properties are supplied.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
    }
    full_catalogue_item_info = {
        **catalogue_item_info,
        "catalogue_category_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            catalogue_category_id=str(ObjectId()),
            properties=[{"name": "Property A", "value": True}],
            **catalogue_item_info,
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(
            catalogue_category_id=catalogue_item.catalogue_category_id,
            properties=[{"name": prop.name, "value": prop.value} for prop in catalogue_item.properties],
        ),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_with_nonexistent_catalogue_category_id(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test updating a catalogue item with a non-existent catalogue category ID.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, CatalogueItemOut(**catalogue_item_info))
    # Mock `get` to not return a catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, None)

    catalogue_category_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(catalogue_category_id=catalogue_category_id),
        )
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"


def test_update_with_existent_manufacturer_id(
    test_helpers, catalogue_item_repository_mock, manufacturer_repository_mock, catalogue_item_service
):
    """
    Test updating manufacturer id to an existing id
    """
    # pylint: disable=duplicate-code
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    # pylint: enable=duplicate-code
    full_catalogue_item_info = {
        **catalogue_item_info,
        "manufacturer_id": str(ObjectId()),
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            manufacturer_id=str(ObjectId()),
            **catalogue_item_info,
        ),
    )

    # Mock `get` to return a manufacturer
    test_helpers.mock_get(
        manufacturer_repository_mock,
        ManufacturerOut(
            id=catalogue_item.manufacturer_id,
            name="Manufacturer A",
            code="manufacturer-a",
            url="https://example.com",
            address=AddressSchema(
                building_number="1",
                street_name="Example Street",
                town="Oxford",
                county="Oxfordshire",
                country="United Kingdom",
                postcode="OX1 2AB",
            ),
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(manufacturer_id=catalogue_item.manufacturer_id),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_with_nonexistent_manufacturer_id(
    test_helpers, manufacturer_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test updating a catalogue item with a non-existent manufacturer id
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, CatalogueItemOut(**catalogue_item_info))
    # Mock `get` to not return a catalogue category
    test_helpers.mock_get(manufacturer_repository_mock, None)

    manufacturer_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(manufacturer_id=manufacturer_id),
        )
    assert str(exc.value) == f"No manufacturer found with ID: {manufacturer_id}"


def test_update_change_catalogue_category_id_non_leaf_catalogue_category(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test moving a catalogue item to a non-leaf catalogue category.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, CatalogueItemOut(**catalogue_item_info))
    catalogue_category_id = str(ObjectId())
    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            name="Category A",
            code="category-a",
            is_leaf=False,
            path="/category-a",
            parent_path="/",
            parent_id=None,
            catalogue_item_properties=[],
        ),
    )
    # pylint: enable=duplicate-code

    with pytest.raises(NonLeafCategoryError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(catalogue_category_id=catalogue_category_id),
        )
    assert str(exc.value) == "Cannot add catalogue item to a non-leaf catalogue category"


def test_update_add_non_mandatory_property(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test adding a non-mandatory catalogue item property and a value.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    full_catalogue_item_info = {
        **catalogue_item_info,
        "properties": [{"name": "Property A", "value": 20, "unit": "mm"}] + catalogue_item_info["properties"],
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(
            properties=[{"name": prop.name, "value": prop.value} for prop in catalogue_item.properties]
        ),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_remove_non_mandatory_property(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test removing a non-mandatory catalogue item property and its value.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    full_catalogue_item_info = {**catalogue_item_info, "properties": catalogue_item_info["properties"][-2:]}
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(
            properties=[{"name": prop.name, "value": prop.value} for prop in catalogue_item.properties]
        ),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_remove_mandatory_property(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test removing a mandatory catalogue item property and its value.
    """
    full_catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**full_catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )

    with pytest.raises(MissingMandatoryCatalogueItemProperty) as exc:
        catalogue_item_service.update(
            catalogue_item.id,
            CatalogueItemPatchRequestSchema(
                properties=[{"name": prop.name, "value": prop.value} for prop in catalogue_item.properties[:2]]
            ),
        )
    assert str(exc.value) == f"Missing mandatory catalogue item property: '{catalogue_item.properties[2].name}'"


def test_update_change_property_value(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test updating a value of a property.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }
    full_catalogue_item_info = {
        **catalogue_item_info,
        "properties": [{"name": "Property A", "value": 1, "unit": "mm"}] + catalogue_item_info["properties"][-2:],
    }
    catalogue_item = CatalogueItemOut(**full_catalogue_item_info)

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
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
        ),
    )
    # Mock `update` to return the updated catalogue item
    test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

    updated_catalogue_item = catalogue_item_service.update(
        catalogue_item.id,
        CatalogueItemPatchRequestSchema(
            properties=[{"name": prop.name, "value": prop.value} for prop in catalogue_item.properties]
        ),
    )

    catalogue_item_repository_mock.update.assert_called_once_with(
        catalogue_item.id, CatalogueItemIn(**full_catalogue_item_info)
    )
    assert updated_catalogue_item == catalogue_item


def test_update_change_value_for_string_property_invalid_type(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test changing the value of a string property to an invalid type.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_item_info["catalogue_category_id"],
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
        ),
    )

    properties = [{"name": prop["name"], "value": prop["value"]} for prop in catalogue_item_info["properties"]]
    properties[2]["value"] = True
    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(properties=properties),
        )
    assert str(exc.value) == "Invalid value type for catalogue item property 'Property C'. Expected type: string."


def test_update_change_value_for_number_property_invalid_type(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test changing the value of a number property to an invalid type.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_item_info["catalogue_category_id"],
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
        ),
    )

    properties = [{"name": prop["name"], "value": prop["value"]} for prop in catalogue_item_info["properties"]]
    properties[0]["value"] = "20"
    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(properties=properties),
        )
    assert str(exc.value) == "Invalid value type for catalogue item property 'Property A'. Expected type: number."


def test_update_change_value_for_boolean_property_invalid_type(
    test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
):
    """
    Test changing the value of a boolean property to an invalid type.
    """
    catalogue_item_info = {
        "id": str(ObjectId()),
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "manufacturer_id": str(ObjectId()),
        "properties": [
            {"name": "Property A", "value": 20, "unit": "mm"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        ],
    }

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(**catalogue_item_info),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_item_info["catalogue_category_id"],
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
        ),
    )

    properties = [{"name": prop["name"], "value": prop["value"]} for prop in catalogue_item_info["properties"]]
    properties[1]["value"] = "False"
    with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
        catalogue_item_service.update(
            catalogue_item_info["id"],
            CatalogueItemPatchRequestSchema(properties=properties),
        )
    assert str(exc.value) == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
