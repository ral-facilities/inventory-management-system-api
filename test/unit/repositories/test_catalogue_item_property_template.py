"""
Unit tests for the `CatalogueItemPropertyTemplateRepo` repository
"""

from bson import ObjectId
from inventory_management_system_api.core.custom_object_id import CustomObjectId

from inventory_management_system_api.models.catalogue_item_property_template import CatalogueItemPropertyTemplateOut


PROPERTY_TEMPLATE_A_INFO = {
    "name": "Material",
    "type": "string",
    "unit": None,
    "mandatory": False,
    "allowed_values": {"type": "list", "values": ["Fused Silica", "(N)BK-7", "KzFS", "SF6"]},
}

PROPERTY_TEMPLATE_B_INFO = {
    "name": "Diameter",
    "type": "number",
    "unit": "mm",
    "mandatory": True,
    "allowed_values": None,
}


def test_list(test_helpers, database_mock, catalogue_item_property_template_repository):
    """
    Test getting catalogue item property templates
    Verify that the `list` method properly handles the retrieval of catalogue item property templates without filters
    """
    property_template_a = CatalogueItemPropertyTemplateOut(id=str(ObjectId()), **PROPERTY_TEMPLATE_A_INFO)
    property_template_b = CatalogueItemPropertyTemplateOut(id=str(ObjectId()), **PROPERTY_TEMPLATE_B_INFO)

    # Mock `find` to return a list of catalogue item property template documents
    test_helpers.mock_find(
        database_mock.catalogue_item_property_templates,
        [
            {"_id": CustomObjectId(property_template_a.id), **PROPERTY_TEMPLATE_A_INFO},
            {"_id": CustomObjectId(property_template_b.id), **PROPERTY_TEMPLATE_B_INFO},
        ],
    )

    retrieved_catalogue_item_property_templates = catalogue_item_property_template_repository.list()

    database_mock.catalogue_item_property_templates.find.assert_called_once_with()
    assert retrieved_catalogue_item_property_templates == [property_template_a, property_template_b]
