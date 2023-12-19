"""
Unit tests for the `CatalogueCategoryService` service.
"""
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    ChildrenElementsExistError,
    DuplicateCatalogueItemPropertyNameError,
    LeafCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    CatalogueItemProperty,
)
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPatchRequestSchema,
    CatalogueCategoryPostRequestSchema
)


def test_create(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category.

    Verify that the `create` method properly handles the catalogue category to be created, generates the code,
    and calls the repository's create method.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `create` to return the created catalogue category
    test_helpers.mock_create(catalogue_category_repository_mock, catalogue_category)

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(
            name=catalogue_category.name,
            is_leaf=catalogue_category.is_leaf,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )

    # pylint: disable=duplicate-code
    catalogue_category_repository_mock.create.assert_called_once_with(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_category == catalogue_category


def test_create_with_parent_id(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category with a parent ID.

    Verify that the `create` method properly handles a catalogue category with a parent ID.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=True,
        parent_id=str(ObjectId()),
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the parent catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.parent_id,
            name="Category A",
            code="category-a",
            is_leaf=False,
            parent_id=None,
            catalogue_item_properties=[],
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `create` to return the created catalogue category
    test_helpers.mock_create(catalogue_category_repository_mock, catalogue_category)

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(
            name=catalogue_category.name,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties],
        )
    )

    # pylint: disable=duplicate-code
    catalogue_category_repository_mock.create.assert_called_once_with(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties],
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_category == catalogue_category


def test_create_with_whitespace_name(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test creating a catalogue category name containing leading/trailing/consecutive whitespaces.

    Verify that the `create` method trims the whitespace from the category name and handles it correctly.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="    Category   A         ",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `create` to return the created catalogue category
    test_helpers.mock_create(catalogue_category_repository_mock, catalogue_category)

    created_catalogue_category = catalogue_category_service.create(
        CatalogueCategoryPostRequestSchema(
            name=catalogue_category.name,
            is_leaf=catalogue_category.is_leaf,
            catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties],
        )
    )

    # pylint: disable=duplicate-code
    catalogue_category_repository_mock.create.assert_called_once_with(
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties],
        )
    )
    # pylint: enable=duplicate-code
    assert created_catalogue_category == catalogue_category


def test_create_with_leaf_parent_catalogue_category(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test creating a catalogue category in a leaf parent catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        parent_id=str(ObjectId()),
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return the parent catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.parent_id,
            name="Category A",
            code="category-a",
            is_leaf=True,
            parent_id=None,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
                CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            ],
        ),
    )
    # pylint: enable=duplicate-code

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


def test_create_with_duplicate_property_names(catalogue_category_service):
    """
    Test trying to create a catalogue category with duplicate catalogue item property names
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Property A", type="boolean", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    with pytest.raises(DuplicateCatalogueItemPropertyNameError) as exc:
        # pylint: disable=duplicate-code
        catalogue_category_service.create(
            CatalogueCategoryPostRequestSchema(
                name=catalogue_category.name,
                is_leaf=catalogue_category.is_leaf,
                catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties],
            )
        )
        # pylint: enable=duplicate-code
    assert str(exc.value) == (
        f"Duplicate catalogue item property name: {catalogue_category.catalogue_item_properties[0].name}"
    )


def test_delete(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test deleting a catalogue category.

    Verify that the `delete` method properly handles the deletion of a catalogue category by ID.
    """
    catalogue_category_id = str(ObjectId())

    catalogue_category_service.delete(catalogue_category_id)

    catalogue_category_repository_mock.delete.assert_called_once_with(catalogue_category_id)


def test_get(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
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
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return a catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

    retrieved_catalogue_category = catalogue_category_service.get(catalogue_category.id)

    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)
    assert retrieved_catalogue_category == catalogue_category


def test_get_with_nonexistent_id(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test getting a catalogue category with a nonexistent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with a nonexistent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `get` to not return a catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, None)

    retrieved_catalogue_category = catalogue_category_service.get(catalogue_category_id)

    assert retrieved_catalogue_category is None
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)


def test_get_breadcrumbs(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test getting breadcrumbs for a catalogue category

    Verify that the `get_breadcrumbs` method properly handles the retrieval of a System
    """
    catalogue_category_id = str(ObjectId)
    breadcrumbs = MagicMock()

    # Mock `get` to return breadcrumbs
    test_helpers.mock_get_breadcrumbs(catalogue_category_repository_mock, breadcrumbs)

    retrieved_breadcrumbs = catalogue_category_service.get_breadcrumbs(catalogue_category_id)

    catalogue_category_repository_mock.get_breadcrumbs.assert_called_once_with(catalogue_category_id)
    assert retrieved_breadcrumbs == breadcrumbs


def test_list(catalogue_category_repository_mock, catalogue_category_service):
    """
    Test listing catalogue categories.

    Verify that the `list` method properly calls the repository function with any passed filters
    """

    parent_id = MagicMock()

    result = catalogue_category_service.list(parent_id=parent_id)

    catalogue_category_repository_mock.list.assert_called_once_with(parent_id)
    assert result == catalogue_category_repository_mock.list.return_value


def test_update(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test updating a catalogue category.

    Verify that the `update` method properly handles the catalogue category to be updated.
    """
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[],
    )

    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name="Category A",
            code="category-a",
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        ),
    )
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    updated_catalogue_category = catalogue_category_service.update(
        catalogue_category.id, CatalogueCategoryPatchRequestSchema(name=catalogue_category.name)
    )

    # pylint: disable=duplicate-code
    catalogue_category_repository_mock.update.assert_called_once_with(
        catalogue_category.id,
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        ),
    )
    # pylint: enable=duplicate-code
    assert updated_catalogue_category == catalogue_category


def test_update_with_nonexistent_id(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test updating a catalogue category with a non-existent ID.

    Verify that the `update` method properly handles the catalogue category to be updated with a non-existent ID.
    """
    # Mock `get` to not return a catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, None)

    catalogue_category_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_service.update(
            catalogue_category_id, CatalogueCategoryPatchRequestSchema(catalogue_item_properties=[])
        )
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"


def test_update_change_parent_id(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
    """
    Test moving a catalogue category to another parent catalogue category.
    """

    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        parent_id=str(ObjectId()),
        catalogue_item_properties=[],
    )

    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=None,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        ),
    )
    # Mock `get` to return a parent catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=str(ObjectId()),
            name="Category A",
            code="category-a",
            is_leaf=False,
            parent_id=None,
            catalogue_item_properties=[],
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    updated_catalogue_category = catalogue_category_service.update(
        catalogue_category.id, CatalogueCategoryPatchRequestSchema(parent_id=catalogue_category.parent_id)
    )

    catalogue_category_repository_mock.update.assert_called_once_with(
        catalogue_category.id,
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        ),
    )
    assert updated_catalogue_category == catalogue_category


def test_update_change_parent_id_leaf_parent_catalogue_category(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Testing moving a catalogue category to a leaf parent catalogue category.
    """
    catalogue_category_b_id = str(ObjectId())
    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_b_id,
            name="Category B",
            code="category-b",
            is_leaf=False,
            parent_id=None,
            catalogue_item_properties=[],
        ),
    )
    catalogue_category_a_id = str(ObjectId())
    # Mock `get` to return a parent catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_b_id,
            name="Category A",
            code="category-a",
            is_leaf=True,
            parent_id=None,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
                CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            ],
        ),
    )
    # pylint: enable=duplicate-code

    with pytest.raises(LeafCategoryError) as exc:
        catalogue_category_service.update(
            catalogue_category_b_id, CatalogueCategoryPatchRequestSchema(parent_id=catalogue_category_a_id)
        )
    assert str(exc.value) == "Cannot add catalogue category to a leaf parent catalogue category"


def test_update_change_from_leaf_to_non_leaf_when_no_children(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test changing a catalogue category from leaf to non-leaf when the category doesn't have any children
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock so no child elements found
    catalogue_category_repository_mock.has_child_elements.return_value = False

    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=True,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
                CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            ],
        ),
    )
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    updated_catalogue_category = catalogue_category_service.update(
        catalogue_category.id, CatalogueCategoryPatchRequestSchema(is_leaf=False)
    )

    catalogue_category_repository_mock.update.assert_called_once_with(
        catalogue_category.id,
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=catalogue_category.catalogue_item_properties,
        ),
    )
    assert updated_catalogue_category == catalogue_category


def test_update_change_catalogue_item_properties_when_no_children(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test updating a catalogue category's item properties when it has no children

    Verify that the `update` method properly handles the catalogue category to be updated.
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
        ],
    )
    # pylint: enable=duplicate-code

    # Mock so no child elements found
    catalogue_category_repository_mock.has_child_elements.return_value = False

    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[catalogue_category.catalogue_item_properties[1]],
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    updated_catalogue_category = catalogue_category_service.update(
        catalogue_category.id,
        CatalogueCategoryPatchRequestSchema(
            catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties]
        ),
    )

    catalogue_category_repository_mock.update.assert_called_once_with(
        catalogue_category.id,
        CatalogueCategoryIn(
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties],
        ),
    )
    assert updated_catalogue_category == catalogue_category


def test_update_change_from_leaf_to_non_leaf_when_has_children(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test changing a catalogue category from leaf to non-leaf when the category has children
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        catalogue_item_properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock so child elements found
    catalogue_category_repository_mock.has_child_elements.return_value = True

    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=True,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[
                CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
                CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
            ],
        ),
    )
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    with pytest.raises(ChildrenElementsExistError) as exc:
        catalogue_category_service.update(catalogue_category.id, CatalogueCategoryPatchRequestSchema(is_leaf=False))

    catalogue_category_repository_mock.update.assert_not_called()
    assert (
        str(exc.value)
        == f"Catalogue category with ID {str(catalogue_category.id)} has child elements and cannot be updated"
    )


def test_update_change_catalogue_item_properties_when_has_children(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test updating a catalogue category's item properties when it has children

    Verify that the `update` method properly handles the catalogue category to be updated.
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
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[catalogue_category.catalogue_item_properties[1]],
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    with pytest.raises(ChildrenElementsExistError) as exc:
        catalogue_category_service.update(
            catalogue_category.id,
            CatalogueCategoryPatchRequestSchema(
                catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties]
            ),
        )

    catalogue_category_repository_mock.update.assert_not_called()
    assert (
        str(exc.value)
        == f"Catalogue category with ID {str(catalogue_category.id)} has child elements and cannot be updated"
    )


def test_update_properties_to_have_duplicate_names(
    test_helpers, catalogue_category_repository_mock, catalogue_category_service
):
    """
    Test that checks that trying to update catalogue item properties so that the names are duplicated is not allowed

    Verify the `update` method properly handles the catalogue category to be updated
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[
            CatalogueItemProperty(name="Duplicate", type="number", unit="mm", mandatory=False),
            CatalogueItemProperty(name="Duplicate", type="boolean", mandatory=True),
        ],
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category.id,
            name=catalogue_category.name,
            code=catalogue_category.code,
            is_leaf=catalogue_category.is_leaf,
            parent_id=catalogue_category.parent_id,
            catalogue_item_properties=[catalogue_category.catalogue_item_properties[1]],
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `update` to return the updated catalogue category
    test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

    with pytest.raises(DuplicateCatalogueItemPropertyNameError) as exc:
        catalogue_category_service.update(
            catalogue_category.id,
            CatalogueCategoryPatchRequestSchema(
                catalogue_item_properties=[prop.model_dump() for prop in catalogue_category.catalogue_item_properties]
            ),
        )

    catalogue_category_repository_mock.update.assert_not_called()
    assert str(exc.value) == (
        f"Duplicate catalogue item property name: {catalogue_category.catalogue_item_properties[0].name}"
    )
