"""
End-to-End tests for the Catalogue Item Property Template router
"""

import json

import pytest

from inventory_management_system_api.core.database import get_database

# Load in the property templates data
with open("./data/catalogue_item_property_templates.json", "r", encoding="utf-8") as file:
    property_templates_data = json.load(file)
    PROPERTY_TEMPLATES = [
        {
            "_id": template["_id"]["$oid"],
            "name": template["name"],
            "type": template["type"],
            "unit": template["unit"],
            "mandatory": template["mandatory"],
            "allowed_values": template["allowed_values"],
        }
        for template in property_templates_data
    ]
PROPERTY_TEMPLATES_EXPECTED = [
    {
        "id": template["_id"],
        "name": template["name"],
        "type": template["type"],
        "unit": template["unit"],
        "mandatory": template["mandatory"],
        "allowed_values": template["allowed_values"],
    }
    for template in PROPERTY_TEMPLATES
]


@pytest.fixture(name="add_property_templates_to_database", autouse=True, scope="session")
def fixture_add_catalogue_item_property_templates_to_database():
    """
    Fixture to add catalogue item property templates to the catalogue item property templates collection in the
    database before any tests in this file run
    """
    property_templates_collection = get_database().catalogue_item_property_templates
    property_templates_collection.delete_many({})
    property_templates_collection.insert_many(PROPERTY_TEMPLATES)
    yield


def test_get_catalogue_item_property_templates(test_client):
    """
    Test getting a list of catalogue item property templates
    """

    response = test_client.get("/v1/catalogue-item-property-templates")

    assert response.status_code == 200
    assert response.json() == PROPERTY_TEMPLATES_EXPECTED
