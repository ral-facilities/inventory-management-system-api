"""
End-to-End tests for the Usage status router
"""

from test.e2e.mock_schemas import (
    USAGE_STATUS_POST_A,
    USAGE_STATUS_POST_A_EXPECTED,
    USAGE_STATUS_POST_B,
    USAGE_STATUS_POST_B_EXPECTED,
    USAGE_STATUS_POST_C,
    USAGE_STATUS_POST_C_EXPECTED,
    USAGE_STATUS_POST_D,
    USAGE_STATUS_POST_D_EXPECTED,
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
    assert response.json()["detail"] == "A usage status with the same name already exists"


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
