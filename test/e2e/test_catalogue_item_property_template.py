"""
End-to-End tests for the Catalogue Item Property Template router
"""

from test.e2e.mock_schemas import CREATED_MODIFIED_VALUES_EXPECTED
from unittest.mock import ANY

from bson import ObjectId

PROPERTY_TEMPLATE_POST_A = {
    "name": "Material",
    "type": "string",
    "unit": None,
    "mandatory": False,
    "allowed_values": {"type": "list", "values": ["Fused Silica", "(N)BK-7", "KzFS", "SF6"]},
}

PROPERTY_TEMPLATE_POST_A_EXPECTED = {
    **PROPERTY_TEMPLATE_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "material",
    "id": ANY,
}

PROPERTY_TEMPLATE_POST_B = {
    "name": "Coating",
    "type": "string",
    "unit": None,
    "mandatory": False,
    "allowed_values": {"type": "list", "values": ["Dielectric", "Protected Gold", "Aluminum", "Enhanced Silver"]},
}

PROPERTY_TEMPLATE_POST_B_EXPECTED = {
    **PROPERTY_TEMPLATE_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "coating",
    "id": ANY,
}

PROPERTY_TEMPLATE_POST_C = {
    "name": "Diameter",
    "type": "number",
    "unit": "mm",
    "mandatory": True,
}

PROPERTY_TEMPLATE_POST_C_EXPECTED = {
    **PROPERTY_TEMPLATE_POST_C,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "diameter",
    "id": ANY,
    "allowed_values": None,
}

PROPERTY_TEMPLATE_POST_D = {
    "name": "Dimension",
    "type": "number",
    "unit": "mm",
    "mandatory": True,
}

PROPERTY_TEMPLATE_POST_D_EXPECTED = {
    **PROPERTY_TEMPLATE_POST_D,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "dimension",
    "id": ANY,
    "allowed_values": None,
}

PROPERTY_TEMPLATES_EXPECTED = [
    PROPERTY_TEMPLATE_POST_A_EXPECTED,
    PROPERTY_TEMPLATE_POST_B_EXPECTED,
    PROPERTY_TEMPLATE_POST_C_EXPECTED,
    PROPERTY_TEMPLATE_POST_D_EXPECTED,
]


def test_create_catalogue_item_property_template(test_client):
    """Test creating a catalogue item property template"""
    response = test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_A)

    assert response.status_code == 201
    assert response.json() == PROPERTY_TEMPLATE_POST_A_EXPECTED


def test_create_catalogue_item_property_template_with_duplicate_name(test_client):
    """Test creating a catalogue item property template with a duplicate name"""

    test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_A)
    response = test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_A)

    assert response.status_code == 409
    assert response.json()["detail"] == "A catalogue item property template with the same name has been found"


def test_get_catalogue_item_property_templates(test_client):
    """
    Test getting a list of catalogue item property templates
    """
    test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_A)
    test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_B)
    test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_C)
    test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_D)

    response = test_client.get("/v1/catalogue-item-property-templates")

    assert response.status_code == 200
    assert response.json() == PROPERTY_TEMPLATES_EXPECTED


def test_get_catalogue_item_property_templates_when_no_templates(test_client):
    """
    Test getting a list of catalogue item property templates
    """

    response = test_client.get("/v1/catalogue-item-property-templates")

    assert response.status_code == 200
    assert response.json() == []


def test_get_catalogue_item_property_template_with_id(test_client):
    """Test getting a catalogue item property template by ID"""
    response = test_client.post("/v1/catalogue-item-property-templates", json=PROPERTY_TEMPLATE_POST_A)

    response = test_client.get(f"/v1/catalogue-item-property-templates/{response.json()['id']}")

    assert response.status_code == 200
    assert response.json() == PROPERTY_TEMPLATE_POST_A_EXPECTED


def test_get_catalogue_item_property_template_with_invalid_id(test_client):
    """Test getting a catalogue item property template with an invalid id"""

    response = test_client.get("/v1/catalogue-item-property-templates/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item property template not found"


def test_get_catalogue_item_property_template_with_nonexistent_id(test_client):
    """Test getting a catalogue item property template with an nonexistent id"""

    response = test_client.get(f"/v1/catalogue-item-property-templates/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item property template not found"
