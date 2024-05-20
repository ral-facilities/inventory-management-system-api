"""
End-to-End tests for the Usage status router
"""

from test.conftest import add_ids_to_properties
from test.e2e.mock_schemas import (
    SYSTEM_POST_A,
    USAGE_STATUS_POST_A,
    USAGE_STATUS_POST_A_EXPECTED,
    USAGE_STATUS_POST_B,
    USAGE_STATUS_POST_B_EXPECTED,
    USAGE_STATUS_POST_C,
    USAGE_STATUS_POST_C_EXPECTED,
    USAGE_STATUS_POST_D,
    USAGE_STATUS_POST_D_EXPECTED,
)
from test.e2e.test_item import (
    CATALOGUE_CATEGORY_POST_A,
    CATALOGUE_ITEM_POST_A,
    ITEM_POST,
    MANUFACTURER_POST,
)

from bson import ObjectId

USAGE_STATUSES_EXPECTED = [
    USAGE_STATUS_POST_A_EXPECTED,
    USAGE_STATUS_POST_B_EXPECTED,
    USAGE_STATUS_POST_C_EXPECTED,
    USAGE_STATUS_POST_D_EXPECTED,
]


def test_create_usage_status(test_client):
    """Test creating a usage status"""
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)

    assert response.status_code == 201
    assert response.json() == USAGE_STATUS_POST_A_EXPECTED


def test_create_usage_status_with_duplicate_name(test_client):
    """Test creating a usage status with a duplicate name"""

    test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)

    assert response.status_code == 409
    assert response.json()["detail"] == "A usage status with the same value already exists"


def test_get_usage_statuses(test_client):
    """
    Test getting a list of usage statuses
    """
    test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_B)
    test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_C)
    test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_D)

    response = test_client.get("/v1/usage-statuses")

    assert response.status_code == 200
    assert response.json() == USAGE_STATUSES_EXPECTED


def test_get_usage_statuses_when_no_usage_statuses(test_client):
    """
    Test getting a list of usage statuses
    """

    response = test_client.get("/v1/usage-statuses")

    assert response.status_code == 200
    assert response.json() == []


def test_get_usage_status_with_id(test_client):
    """Test getting a usage status by ID"""
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)

    response = test_client.get(f"/v1/usage-statuses/{response.json()['id']}")

    assert response.status_code == 200
    assert response.json() == USAGE_STATUS_POST_A_EXPECTED


def test_get_usage_status_with_invalid_id(test_client):
    """Test getting a usage status with an invalid id"""

    response = test_client.get("/v1/usage-statuses/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Usage status not found"


def test_get_usage_status_with_nonexistent_id(test_client):
    """Test getting a usage-statuses with an nonexistent id"""

    response = test_client.get(f"/v1/usage-statuses/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Usage status not found"


def test_delete(test_client):
    """Test deleting a usage status"""

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status = response.json()

    response = test_client.delete(f"/v1/usage-statuses/{usage_status['id']}")
    assert response.status_code == 204


def test_delete_with_an_invalid_id(test_client):
    """Test trying to delete a usage_status with an invalid ID"""

    response = test_client.delete("/v1/usage-statuses/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Usage status not found"


def test_delete_with_a_non_existent_id(test_client):
    """Test trying to delete a usage status with a non-existent ID"""

    response = test_client.delete(f"/v1/usage-statuses/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Usage status not found"


def test_delete_usage_status_that_is_a_part_of_item(test_client):
    """Test trying to delete a usage status that is a part of a Item"""
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)

    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "20x15x10"},
            ],
        ),
    }

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/items", json=item_post)

    response = test_client.delete(f"/v1/usage-statuses/{usage_status_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "The specified usage status is a part of an Item"
