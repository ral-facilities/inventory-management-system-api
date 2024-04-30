"""
Unit tests for the `CatalogueCategoryPropertyService` service.
"""

from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW
from unittest.mock import ANY, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    InvalidActionError, MissingRecordError)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn, CatalogueCategoryOut, CatalogueItemPropertyIn,
    CatalogueItemPropertyOut)
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.schemas.catalogue_category import \
    CatalogueItemPropertyPostRequestSchema

# pylint:disable=too-many-locals
# pylint:disable=too-many-arguments


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
def test_create(
    mongodb_client_mock,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category level

    Verify that the `create` method properly handles the property to be created and propagates the changes
    downwards through catalogue items and items for a non-mandatory property
    """
    catalogue_category_id = str(ObjectId())
    catalogue_item_property = CatalogueItemPropertyPostRequestSchema(
        name="Property A", type="number", unit="mm", mandatory=False
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    created_catalogue_item_property = catalogue_category_property_service.create(
        catalogue_category_id, catalogue_item_property
    )

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.update.assert_called_once_with(
        catalogue_category_id,
        ANY,
        session=session,
    )

    expected_catalogue_item_property_in = CatalogueItemPropertyIn(**catalogue_item_property.model_dump())
    expected_catalogue_item_properties_in = [
        CatalogueItemPropertyIn(**prop.model_dump()) for prop in stored_catalogue_category.catalogue_item_properties
    ] + [expected_catalogue_item_property_in]
    expected_catalogue_category_in = CatalogueCategoryIn(
        **{**stored_catalogue_category.model_dump(), "catalogue_item_properties": expected_catalogue_item_properties_in}
    )

    # Catalogue category update
    update_catalogue_category_in = catalogue_category_repository_mock.update.call_args_list[0][0][1]
    assert update_catalogue_category_in.model_dump() == {
        **expected_catalogue_category_in.model_dump(),
        "catalogue_item_properties": [
            {**prop.model_dump(), "id": ANY} for prop in expected_catalogue_item_properties_in
        ],
    }

    # Property
    expected_property_in = PropertyIn(
        id=str(expected_catalogue_item_property_in.id),
        name=expected_catalogue_item_property_in.name,
        value=catalogue_item_property.default_value,
        unit=expected_catalogue_item_property_in.unit,
    )

    # Catalogue items update
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_called_once_with(
        catalogue_category_id, ANY, session=session
    )
    insert_property_to_all_matching_property_in = (
        catalogue_item_repository_mock.insert_property_to_all_matching.call_args_list[0][0][1]
    )
    assert insert_property_to_all_matching_property_in.model_dump() == {
        **expected_property_in.model_dump(),
        "id": ANY,
    }

    # Catalogue category update
    catalogue_item_repository_mock.list_ids.assert_called_once_with(catalogue_category_id, session=session)
    item_repository_mock.insert_property_to_all_in.assert_called_once_with(
        catalogue_item_repository_mock.list_ids.return_value, ANY, session=session
    )
    insert_property_to_all_in_property_in = item_repository_mock.insert_property_to_all_in.call_args_list[0][0][1]
    assert insert_property_to_all_in_property_in.model_dump() == {
        **expected_property_in.model_dump(),
        "id": ANY,
    }

    # Final output
    assert created_catalogue_item_property.model_dump() == {
        **CatalogueItemPropertyOut(**expected_catalogue_item_property_in.model_dump()).model_dump(),
        "id": ANY,
    }


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
def test_create_mandatory_property(
    mongodb_client_mock,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category level

    Verify that the `create` method properly handles the property to be created and propagates the changes
    downwards through catalogue items and items for a mandatory property with a default value
    """
    catalogue_category_id = str(ObjectId())
    catalogue_item_property = CatalogueItemPropertyPostRequestSchema(
        name="Property A", type="number", unit="mm", mandatory=True, default_value=40
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    created_catalogue_item_property = catalogue_category_property_service.create(
        catalogue_category_id, catalogue_item_property
    )

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.update.assert_called_once_with(
        catalogue_category_id,
        ANY,
        session=session,
    )

    expected_catalogue_item_property_in = CatalogueItemPropertyIn(**catalogue_item_property.model_dump())
    expected_catalogue_item_properties_in = [
        CatalogueItemPropertyIn(**prop.model_dump()) for prop in stored_catalogue_category.catalogue_item_properties
    ] + [expected_catalogue_item_property_in]
    expected_catalogue_category_in = CatalogueCategoryIn(
        **{**stored_catalogue_category.model_dump(), "catalogue_item_properties": expected_catalogue_item_properties_in}
    )

    # Catalogue category update
    update_catalogue_category_in = catalogue_category_repository_mock.update.call_args_list[0][0][1]
    assert update_catalogue_category_in.model_dump() == {
        **expected_catalogue_category_in.model_dump(),
        "catalogue_item_properties": [
            {**prop.model_dump(), "id": ANY} for prop in expected_catalogue_item_properties_in
        ],
    }

    # Property
    expected_property_in = PropertyIn(
        id=str(expected_catalogue_item_property_in.id),
        name=expected_catalogue_item_property_in.name,
        value=catalogue_item_property.default_value,
        unit=expected_catalogue_item_property_in.unit,
    )

    # Catalogue items update
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_called_once_with(
        catalogue_category_id, ANY, session=session
    )
    insert_property_to_all_matching_property_in = (
        catalogue_item_repository_mock.insert_property_to_all_matching.call_args_list[0][0][1]
    )
    assert insert_property_to_all_matching_property_in.model_dump() == {
        **expected_property_in.model_dump(),
        "id": ANY,
    }

    # Catalogue category update
    catalogue_item_repository_mock.list_ids.assert_called_once_with(catalogue_category_id, session=session)
    item_repository_mock.insert_property_to_all_in.assert_called_once_with(
        catalogue_item_repository_mock.list_ids.return_value, ANY, session=session
    )
    insert_property_to_all_in_property_in = item_repository_mock.insert_property_to_all_in.call_args_list[0][0][1]
    assert insert_property_to_all_in_property_in.model_dump() == {
        **expected_property_in.model_dump(),
        "id": ANY,
    }

    # Final output
    assert created_catalogue_item_property.model_dump() == {
        **CatalogueItemPropertyOut(**expected_catalogue_item_property_in.model_dump()).model_dump(),
        "id": ANY,
    }


def test_create_mandatory_property_without_default_value(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category

    Verify that the `create` method raises an InvalidActionError when the property being created is mandatory but
    doesn't have a default_value
    """
    catalogue_category_id = str(ObjectId())
    catalogue_item_property = CatalogueItemPropertyPostRequestSchema(
        name="Property A", type="number", unit="mm", mandatory=True
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        catalogue_item_properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, catalogue_item_property)
    assert str(exc.value) == "Cannot add a mandatory property without a default value"

    # Ensure no updates
    catalogue_category_repository_mock.update.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()


def test_create_mandatory_property_with_missing_catalogue_category(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category

    Verify that the `create` method raises an MissingRecordError when the catalogue category with the given
    catalogue_category_id doesn't exist
    """
    catalogue_category_id = str(ObjectId())
    catalogue_item_property = CatalogueItemPropertyPostRequestSchema(
        name="Property A", type="number", unit="mm", mandatory=False
    )
    stored_catalogue_category = None

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, catalogue_item_property)
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"

    # Ensure no updates
    catalogue_category_repository_mock.update.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()


def test_create_mandatory_property_with_non_leaf_catalogue_category(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category

    Verify that the `create` method raises an InvalidActionError when the catalogue category for the given id
    is not a leaf
    """
    catalogue_category_id = str(ObjectId())
    catalogue_item_property = CatalogueItemPropertyPostRequestSchema(
        name="Property A", type="number", unit="mm", mandatory=False
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        catalogue_item_properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, catalogue_item_property)
    assert str(exc.value) == "Cannot add a property to a non-leaf catalogue category"

    # Ensure no updates
    catalogue_category_repository_mock.update.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()
