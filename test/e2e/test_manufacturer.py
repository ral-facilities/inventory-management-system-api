"""
End-to-End tests for the manufacturer router.
"""

from test.conftest import add_ids_to_properties
from test.e2e.mock_schemas import CREATED_MODIFIED_VALUES_EXPECTED
from unittest.mock import ANY

from bson import ObjectId

MANUFACTURER_A_POST = {
    "name": "Manufacturer A",
    "url": "http://example.com/",
    "address": {
        "address_line": "1 Example Street",
        "town": "Oxford",
        "county": "Oxfordshire",
        "country": "United Kingdom",
        "postcode": "OX1 2AB",
    },
    "telephone": "0932348348",
}

MANUFACTURER_A_POST_EXPECTED = {
    **MANUFACTURER_A_POST,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "manufacturer-a",
}

MANUFACTURER_B_POST = {
    "name": "Manufacturer B",
    "url": "http://example.com/",
    "address": {
        "address_line": "1 Example Street",
        "town": "Oxford",
        "county": "Oxfordshire",
        "country": "United Kingdom",
        "postcode": "OX1 2AB",
    },
    "telephone": "05940545",
}

MANUFACTURER_B_POST_EXPECTED = {
    **MANUFACTURER_B_POST,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "manufacturer-b",
}

MANUFACTURER_POST_REQUIRED_ONLY = {
    "name": "Manufacturer A",
    "address": {
        "address_line": "1 Example Street",
        "country": "United Kingdom",
        "postcode": "OX1 2AB",
    },
}

MANUFACTURER_POST_REQUIRED_ONLY_EXPECTED = {
    **MANUFACTURER_POST_REQUIRED_ONLY,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "manufacturer-a",
    "url": None,
    "address": {**MANUFACTURER_POST_REQUIRED_ONLY["address"], "town": None, "county": None},
    "telephone": None,
}


def test_create_manufacturer(test_client):
    """Test creating a manufacturer"""

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)

    assert response.status_code == 201
    assert response.json() == MANUFACTURER_A_POST_EXPECTED


def test_create_manufacturer_with_only_mandatory_fields(test_client):
    """Test creating a manufacturer with only mandatory fields"""
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST_REQUIRED_ONLY)

    print(response.json())

    assert response.status_code == 201
    assert response.json() == MANUFACTURER_POST_REQUIRED_ONLY_EXPECTED


def test_check_duplicate_name_within_manufacturer(test_client):
    """Test creating a manufactuer with a duplicate name"""

    test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)

    assert response.status_code == 409
    assert response.json()["detail"] == "A manufacturer with the same name has been found"


def test_list(test_client):
    """Test getting all manufacturers"""

    test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)
    test_client.post("/v1/manufacturers", json=MANUFACTURER_B_POST)

    response = test_client.get("/v1/manufacturers")

    assert response.status_code == 200

    manufacturers = list(response.json())

    assert len(manufacturers) == 2
    assert manufacturers[0] == MANUFACTURER_A_POST_EXPECTED
    assert manufacturers[1] == MANUFACTURER_B_POST_EXPECTED


def test_list_when_no_manufacturers(test_client):
    """Test trying to get all manufacturers when there are none in the databse"""

    response = test_client.get("/v1/manufacturers")

    assert response.status_code == 200
    manufacturers = list(response.json())
    assert not manufacturers


def test_get_manufacturer_with_id(test_client):
    """Test getting a manufacturer by ID"""
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)

    response = test_client.get(f"/v1/manufacturers/{response.json()['id']}")

    assert response.status_code == 200
    assert response.json() == MANUFACTURER_A_POST_EXPECTED


def test_get_manufacturer_with_invalid_id(test_client):
    """Test getting a manufacturer with an invalid id"""

    response = test_client.get("/v1/manufacturers/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Manufacturer not found"


def test_get_manufactuer_with_nonexistent_id(test_client):
    """Test getting a manufacturer with an nonexistent id"""

    response = test_client.get(f"/v1/manufacturers/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Manufacturer not found"


def test_update(test_client):
    """Test updating a manufacturer"""

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)

    manufacturer_patch = {
        "name": "Manufacturer B",
        "url": "http://test.co.uk/",
        "address": {"address_line": "2 My Avenue"},
        "telephone": "07569585584",
    }
    response = test_client.patch(f"/v1/manufacturers/{response.json()['id']}", json=manufacturer_patch)

    assert response.status_code == 200
    assert response.json() == {
        **MANUFACTURER_A_POST_EXPECTED,
        **manufacturer_patch,
        "address": {**MANUFACTURER_A_POST["address"], **manufacturer_patch["address"]},
        "code": "manufacturer-b",
    }


def test_partial_address_update(test_client):
    """Test updating a manufacturer's address"""

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)

    manufacturer_patch = {
        "address": {
            "town": "test",
        }
    }
    response = test_client.patch(f"/v1/manufacturers/{response.json()['id']}", json=manufacturer_patch)

    assert response.status_code == 200
    assert response.json() == {
        **MANUFACTURER_A_POST_EXPECTED,
        "address": {**MANUFACTURER_A_POST["address"], **manufacturer_patch["address"]},
    }


def test_update_with_invalid_id(test_client):
    """Test trying to update a manufacturer with an invalid ID"""

    response = test_client.patch("/v1/manufacturers/invalid", json=MANUFACTURER_A_POST)

    assert response.status_code == 404
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_update_with_nonexistent_id(test_client):
    """Test trying to update a manufacturer with a non-existent ID"""
    response = test_client.patch(f"/v1/manufacturers/{str(ObjectId())}", json=MANUFACTURER_A_POST)

    assert response.status_code == 404
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_update_duplicate_name(test_client):
    """Test updating a manufacturer with a duplicate name"""

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)
    test_client.post("/v1/manufacturers", json=MANUFACTURER_B_POST)

    manufacturer_patch = {"name": "Manufacturer B"}
    response = test_client.patch(f"/v1/manufacturers/{response.json()['id']}", json=manufacturer_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "A manufacturer with the same name has been found"


def test_delete(test_client):
    """Test deleting a manufacturer"""

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)
    manufacturer = response.json()

    response = test_client.delete(f"/v1/manufacturers/{manufacturer['id']}")
    assert response.status_code == 204


def test_delete_with_an_invalid_id(test_client):
    """Test trying to delete a manufacturer with an invalid ID"""

    response = test_client.delete("/v1/manufacturers/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_delete_with_a_non_existent_id(test_client):
    """Test trying to delete a manufacturer with a non-existent ID"""

    response = test_client.delete(f"/v1/manufacturers/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_delete_manufacturer_that_is_a_part_of_catalogue_item(test_client):
    """Test trying to delete a manufacturer that is a part of a Catalogue Item"""
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_A_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        "name": "Catalogue Item A",
        "catalogue_category_id": catalogue_category["id"],
        "description": "This is Catalogue Item A",
        "cost_gbp": 129.99,
        "days_to_replace": 2.0,
        "drawing_link": "https://drawing-link.com/",
        "item_model_number": "abc123",
        "is_obsolete": False,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20},
                {"name": "Property B", "value": False},
            ],
        ),
        "manufacturer_id": manufacturer_id,
    }
    # pylint: enable=duplicate-code
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.delete(f"/v1/manufacturers/{manufacturer_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "The specified manufacturer is a part of a Catalogue Item"
