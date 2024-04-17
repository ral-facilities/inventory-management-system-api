"""
Unit tests for the `CatalogueItemPropertyTemplateService` service
"""

from unittest.mock import MagicMock
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW

from bson import ObjectId

from inventory_management_system_api.models.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateIn,
    CatalogueItemPropertyTemplateOut,
)
from inventory_management_system_api.schemas.catalogue_item_property_template import (
    CatalogueItemPropertyTemplatePostRequestSchema,
)


def test_create(
    test_helpers,
    catalogue_item_property_template_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    catalogue_item_property_template_service,
):
    """
    Testing creating a catalogue item property template
    """
    # pylint: disable=duplicate-code

    catalogue_item_property_template = CatalogueItemPropertyTemplateOut(
        id=str(ObjectId()),
        name="Material",
        code="material",
        type="string",
        unit=None,
        mandatory=False,
        allowed_values=None,
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )
    # pylint: enable=duplicate-code

    # Mock `create` to return the created catalogue item property template
    test_helpers.mock_create(catalogue_item_property_template_repository_mock, catalogue_item_property_template)

    created_catalogue_item_property_template = catalogue_item_property_template_service.create(
        CatalogueItemPropertyTemplatePostRequestSchema(
            name=catalogue_item_property_template.name,
            type=catalogue_item_property_template.type,
            unit=catalogue_item_property_template.unit,
            mandatory=catalogue_item_property_template.mandatory,
            allowed_values=catalogue_item_property_template.allowed_values,
        )
    )
    catalogue_item_property_template_repository_mock.create.assert_called_once_with(
        CatalogueItemPropertyTemplateIn(
            name=catalogue_item_property_template.name,
            code=catalogue_item_property_template.code,
            type=catalogue_item_property_template.type,
            unit=catalogue_item_property_template.unit,
            mandatory=catalogue_item_property_template.mandatory,
            allowed_values=catalogue_item_property_template.allowed_values,
        )
    )
    assert created_catalogue_item_property_template == catalogue_item_property_template


def test_get(
    test_helpers,
    catalogue_item_property_template_repository_mock,
    catalogue_item_property_template_service,
):
    """Test getting a catalogue_item_property_template by ID"""
    catalogue_item_property_template_id = str(ObjectId())
    catalogue_item_property_template = MagicMock()

    # Mock `get` to return a catalogue item property template
    test_helpers.mock_get(catalogue_item_property_template_repository_mock, catalogue_item_property_template)

    retrieved_catalogue_item_property_template = catalogue_item_property_template_service.get(
        catalogue_item_property_template_id
    )

    catalogue_item_property_template_repository_mock.get.assert_called_once_with(catalogue_item_property_template_id)
    assert retrieved_catalogue_item_property_template == catalogue_item_property_template


def test_get_with_nonexistent_id(
    test_helpers,
    catalogue_item_property_template_repository_mock,
    catalogue_item_property_template_service,
):
    """Test getting a catalogue item property template with an non-existent ID"""
    catalogue_item_property_template_id = str(ObjectId())
    test_helpers.mock_get(catalogue_item_property_template_repository_mock, None)

    # Mock `get` to return a catalogue item property template
    retrieved_manufacturer = catalogue_item_property_template_service.get(catalogue_item_property_template_id)

    assert retrieved_manufacturer is None
    catalogue_item_property_template_repository_mock.get.assert_called_once_with(catalogue_item_property_template_id)


def test_list(catalogue_item_property_template_repository_mock, catalogue_item_property_template_service):
    """
    Test listing catalogue item property templates
    Verify that the `list` method properly calls the repository function
    """
    result = catalogue_item_property_template_service.list()

    catalogue_item_property_template_repository_mock.list.assert_called_once_with()
    assert result == catalogue_item_property_template_repository_mock.list.return_value
