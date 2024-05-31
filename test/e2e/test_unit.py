"""
End-to-End tests for the Unit router
"""

from test.e2e.mock_schemas import CREATED_MODIFIED_VALUES_EXPECTED
from unittest.mock import ANY

from bson import ObjectId

UNIT_POST_A = {"value": "mm"}

UNIT_POST_A_EXPECTED = {
    **UNIT_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "mm",
    "id": ANY,
}

UNIT_POST_B = {"value": "cm"}

UNIT_POST_B_EXPECTED = {
    **UNIT_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "cm",
    "id": ANY,
}

UNIT_POST_C = {"value": "degrees"}

UNIT_POST_C_EXPECTED = {
    **UNIT_POST_C,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "degrees",
    "id": ANY,
}

UNIT_POST_D = {"value": "J/cm²"}

UNIT_POST_D_EXPECTED = {
    **UNIT_POST_D,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "j/cm²",
    "id": ANY,
}


UNITS_EXPECTED = [
    UNIT_POST_A_EXPECTED,
    UNIT_POST_B_EXPECTED,
    UNIT_POST_C_EXPECTED,
    UNIT_POST_D_EXPECTED,
]


def test_create_unit(test_client):
    """Test creating a unit"""

    response = test_client.post("/v1/units", json=UNIT_POST_A)

    assert response.status_code == 201
    assert response.json() == UNIT_POST_A_EXPECTED


def test_create_unit_with_duplicate_name(test_client):
    """Test creating a unit with a duplicate name"""

    test_client.post("/v1/units", json=UNIT_POST_A)
    response = test_client.post("/v1/units", json=UNIT_POST_A)

    assert response.status_code == 409
    assert response.json()["detail"] == "A unit with the same value already exists"


def test_get_units(test_client):
    """
    Test getting a list of units
    """

    test_client.post("/v1/units", json=UNIT_POST_A)
    test_client.post("/v1/units", json=UNIT_POST_B)
    test_client.post("/v1/units", json=UNIT_POST_C)
    test_client.post("/v1/units", json=UNIT_POST_D)

    response = test_client.get("/v1/units")

    assert response.status_code == 200
    assert response.json() == UNITS_EXPECTED


def test_get_units_when_no_units(test_client):
    """
    Test getting a list of units
    """

    response = test_client.get("/v1/units")

    assert response.status_code == 200
    assert response.json() == []


def test_get_unit_with_id(test_client):
    """Test getting a unit by ID"""

    response = test_client.post("/v1/units", json=UNIT_POST_A)

    response = test_client.get(f"/v1/units/{response.json()['id']}")

    assert response.status_code == 200
    assert response.json() == UNIT_POST_A_EXPECTED


def test_get_unit_with_invalid_id(test_client):
    """Test getting a unit with an invalid id"""

    response = test_client.get("/v1/units/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Unit not found"


def test_get_unit_with_non_existent_id(test_client):
    """Test getting a units with an non-existent id"""

    response = test_client.get(f"/v1/units/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Unit not found"


def test_delete(test_client):
    """Test deleting a unit"""

    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit = response.json()

    response = test_client.delete(f"/v1/units/{unit['id']}")
    assert response.status_code == 204


def test_delete_with_an_invalid_id(test_client):
    """Test trying to delete a unit with an invalid ID"""

    response = test_client.delete("/v1/units/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Unit not found"


def test_delete_with_a_non_existent_id(test_client):
    """Test trying to delete a unit with a non-existent ID"""

    response = test_client.delete(f"/v1/units/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Unit not found"


def test_delete_unit_that_is_a_part_of_catalogue_category(test_client):
    """Test trying to delete a unit that is a part of a Catalogue Category"""

    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    # pylint: disable=duplicate-code
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_mm["id"], "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.delete(f"/v1/units/{unit_mm['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "The specified unit is part of a Catalogue category"
