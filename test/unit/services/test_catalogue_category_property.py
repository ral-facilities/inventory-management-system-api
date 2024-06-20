"""
Unit tests for the `CatalogueCategoryPropertyService` service.
"""

from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW
from test.unit.services.test_catalogue_category import UNIT_A
from unittest.mock import ANY, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import InvalidActionError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import (
    AllowedValues,
    CatalogueCategoryOut,
    CatalogueCategoryPropertyIn,
    CatalogueCategoryPropertyOut,
)
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.models.unit import UnitOut
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPropertyPatchSchema,
    CatalogueCategoryPropertyPostSchema,
)

# pylint:disable=too-many-locals
# pylint:disable=too-many-arguments


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
@pytest.mark.parametrize(
    "mandatory,default_value",
    [(False, None), (True, 42)],
    ids=["non_mandatory_without_default_value", "mandatory_with_default_value"],
)
def test_create(
    mongodb_client_mock,
    mandatory,
    default_value,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    unit_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category level

    Verify that the `create` method properly handles the property to be created and propagates the changes
    downwards through catalogue items and items for a non-mandatory property without a default value, and a mandatory
    property with a default value
    """
    catalogue_category_id = str(ObjectId())
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    property_post = CatalogueCategoryPropertyPostSchema(
        name="Property A", type="number", unit_id=unit.id, mandatory=mandatory, default_value=default_value
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    # Mock `get` to return the unit
    test_helpers.mock_get(unit_repository_mock, unit)

    created_property = catalogue_category_property_service.create(catalogue_category_id, property_post)

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.create_property.assert_called_once_with(
        catalogue_category_id,
        ANY,
        session=session,
    )

    expected_property_in = CatalogueCategoryPropertyIn(**{**property_post.model_dump(), "unit": unit.value})

    # Property insertion into catalogue category
    inserted_property_in = catalogue_category_repository_mock.create_property.call_args_list[0][0][1]
    assert inserted_property_in.model_dump() == {
        **expected_property_in.model_dump(),
        "id": ANY,
    }

    # Property
    expected_property_in = PropertyIn(
        id=str(expected_property_in.id),
        name=expected_property_in.name,
        value=property_post.default_value,
        unit=unit.value,
        unit_id=unit.id,
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
    assert created_property == catalogue_category_repository_mock.create_property.return_value


def test_create_mandatory_property_without_default_value(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    unit_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category

    Verify that the `create` method raises an InvalidActionError when the property being created is mandatory but
    doesn't have a default_value
    """
    catalogue_category_id = str(ObjectId())
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    property_post = CatalogueCategoryPropertyPostSchema(
        name="Property A", type="number", unit_id=unit.id, mandatory=True
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    # Mock `get` to return the unit
    test_helpers.mock_get(unit_repository_mock, unit)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, property_post)
    assert str(exc.value) == "Cannot add a mandatory property without a default value"

    # Ensure no updates
    catalogue_category_repository_mock.create_property.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()


def test_create_non_existent_unit_id(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    unit_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category with a non existent unit id
    """
    catalogue_category_id = str(ObjectId())
    unit_id = str(ObjectId())
    property_post = CatalogueCategoryPropertyPostSchema(
        name="Property A", type="number", unit_id=unit_id, mandatory=False
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    # Mock `get` to not return a unit
    test_helpers.mock_get(unit_repository_mock, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, property_post)
    assert str(exc.value) == f"No unit found with ID: {unit_id}"

    # Ensure no updates
    catalogue_category_repository_mock.create_property.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()


def test_create_mandatory_property_with_missing_catalogue_category(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    unit_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category

    Verify that the `create` method raises an MissingRecordError when the catalogue category with the given
    catalogue_category_id doesn't exist
    """
    catalogue_category_id = str(ObjectId())
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    property_post = CatalogueCategoryPropertyPostSchema(
        name="Property A", type="number", unit_id=unit.id, mandatory=False
    )
    stored_catalogue_category = None

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    # Mock `get` to return the unit
    test_helpers.mock_get(unit_repository_mock, unit)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, property_post)
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"

    # Ensure no updates
    catalogue_category_repository_mock.create_property.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()


def test_create_mandatory_property_with_non_leaf_catalogue_category(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    unit_repository_mock,
    catalogue_category_property_service,
):
    """
    Test creating a property at the catalogue category

    Verify that the `create` method raises an InvalidActionError when the catalogue category for the given id
    is not a leaf
    """
    catalogue_category_id = str(ObjectId())
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    property_post = CatalogueCategoryPropertyPostSchema(
        name="Property A", type="number", unit_id=unit.id, mandatory=False
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    # Mock `get` to return the unit
    test_helpers.mock_get(unit_repository_mock, unit)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.create(catalogue_category_id, property_post)
    assert str(exc.value) == "Cannot add a property to a non-leaf catalogue category"

    # Ensure no updates
    catalogue_category_repository_mock.create_property.assert_not_called()
    catalogue_item_repository_mock.insert_property_to_all_matching.assert_not_called()
    item_repository_mock.insert_property_to_all_in.assert_not_called()


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
def test_update(
    mongodb_client_mock,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method properly handles the property to be created and propagates the changes
    downwards through catalogue items (This test supplies both name and allowed_values)
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
    )
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100]),
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.update_property.assert_called_once_with(
        catalogue_category_id,
        property_id,
        CatalogueCategoryPropertyIn(**{**stored_property.model_dump(), **property_patch.model_dump()}),
        session=session,
    )

    # Catalogue items update
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_called_once_with(
        property_id, property_patch.name, session=session
    )

    # Items update
    item_repository_mock.update_names_of_all_properties_with_id.assert_called_once_with(
        property_id, property_patch.name, session=session
    )

    # Final output
    assert updated_property == catalogue_category_repository_mock.update_property.return_value


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
def test_update_category_only(
    mongodb_client_mock,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method properly handles an update that doesn't require any propagation through
    catalogue items and items (in this case only modifying the allowed_values)
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
    )
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100]),
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.update_property.assert_called_once_with(
        catalogue_category_id,
        property_id,
        CatalogueCategoryPropertyIn(
            **{**stored_property.model_dump(), **property_patch.model_dump(exclude_unset=True)}
        ),
        session=session,
    )

    # Ensure changes aren't propagated
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()

    # Final output
    assert updated_property == catalogue_category_repository_mock.update_property.return_value


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
def test_update_with_no_changes_allowed_values_none(
    mongodb_client_mock,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method properly handles the property to be created and propagates the changes
    downwards through catalogue items (in this case passing allowed_values as None when the database
    model also uses None)
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(allowed_values=None)
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=None,
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.update_property.assert_called_once_with(
        catalogue_category_id,
        property_id,
        CatalogueCategoryPropertyIn(
            **{**stored_property.model_dump(), **property_patch.model_dump(exclude_unset=True)}
        ),
        session=session,
    )

    # Ensure changes aren't propagated
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()

    # Final output
    assert updated_property == catalogue_category_repository_mock.update_property.return_value


def test_update_with_missing_catalogue_category(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method raises a MissingRecordError when the catalogue category with the given
    catalogue_category_id doesn't exist
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
    )
    stored_catalogue_category = None

    # Mock the stored catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"

    # Ensure no updates actually called
    catalogue_category_repository_mock.update_property.assert_not_called()
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


def test_update_with_missing_property(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method raises a MissingRecordError when the property with the given
    property_id doesn't exist
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
    )
    # pylint: disable=duplicate-code
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=str(ObjectId()),
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100]),
    )
    # pylint: enable=duplicate-code
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
    assert str(exc.value) == f"No property found with ID: {property_id}"

    # Ensure no updates actually called
    catalogue_category_repository_mock.update_property.assert_not_called()
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


def test_update_allowed_values_from_none_to_value(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
    from None to a value
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
    )
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=None,
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
    assert str(exc.value) == "Cannot add allowed_values to an existing property"

    # Ensure no updates actually called
    catalogue_category_repository_mock.update_property.assert_not_called()
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


def test_update_allowed_values_from_value_to_none(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
    from a value to None
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(name="Property Name", allowed_values=None)
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100]),
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
    assert str(exc.value) == "Cannot remove allowed_values from an existing property"

    # Ensure no updates actually called
    catalogue_category_repository_mock.update_property.assert_not_called()
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


def test_update_allowed_values_removing_element(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
    to have one fewer element
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000]}
    )
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100, 500, 1000, 2000]),
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
    assert (
        str(exc.value)
        == "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
    )

    # Ensure no updates actually called
    catalogue_category_repository_mock.update_property.assert_not_called()
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


def test_update_allowed_values_modifying_element(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
    by changing one element
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
    )
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100, 500, 1200, 2000]),
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
    assert (
        str(exc.value)
        == "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
    )

    # Ensure no updates actually called
    catalogue_category_repository_mock.update_property.assert_not_called()
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


@patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
def test_update_adding_allowed_values(
    mongodb_client_mock,
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_category_property_service,
):
    """
    Test updating a property at the catalogue category level

    Verify that the `update` method allows an allowed_values list to be extended
    """
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_patch = CatalogueCategoryPropertyPatchSchema(
        allowed_values={"type": "list", "values": [100, 500, 1000, 2000, 3000, 4000]}
    )
    unit = UnitOut(id=str(ObjectId()), **UNIT_A)
    stored_property = CatalogueCategoryPropertyOut(
        id=property_id,
        name="Property A",
        type="number",
        unit_id=unit.id,
        unit=unit.value,
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[100]),
    )
    stored_catalogue_category = CatalogueCategoryOut(
        id=catalogue_category_id,
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[stored_property],
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )

    # Mock the stored catalogue category to one without a property with the same name
    test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

    updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

    # Start of transaction
    session = mongodb_client_mock.start_session.return_value.__enter__.return_value
    catalogue_category_repository_mock.update_property.assert_called_once_with(
        catalogue_category_id,
        property_id,
        CatalogueCategoryPropertyIn(
            **{**stored_property.model_dump(), **property_patch.model_dump(exclude_unset=True)}
        ),
        session=session,
    )

    # Ensure changes aren't propagated
    catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
    item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()

    # Final output
    assert updated_property == catalogue_category_repository_mock.update_property.return_value
