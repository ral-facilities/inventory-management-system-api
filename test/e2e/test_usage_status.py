"""
End-to-End tests for the Usage status router
"""

import json

import pytest

from inventory_management_system_api.core.database import get_database

# Load in the usage statuses data
with open("./data/usage_statuses.json", "r", encoding="utf-8") as file:
    usage_statuses_data = json.load(file)
    USAGE_STATUSES = [{"_id": usage_status["_id"]["$oid"], "value": usage_status["value"]} for usage_status in usage_statuses_data]
USAGE_STATUSES_EXPECTED = [{"id": usage_status["_id"], "value": usage_status["value"]} for usage_status in USAGE_STATUSES]


@pytest.fixture(name="add_usage_statuses_to_database", autouse=True, scope="session")
def fixture_add_usage_statuses_to_database():
    """
    Fixture to add usage statuses to the usage_statuses collection in the database before any tests in this file run
    """
    usage_statuses_collection = get_database().usage_statuses
    usage_statuses_collection.delete_many({})
    usage_statuses_collection.insert_many(USAGE_STATUSES)
    yield


def test_get_usage_statuses(test_client):
    """
    Test getting a list of Usage statuses
    """

    response = test_client.get("/v1/usage_statuses")

    assert response.status_code == 200
    assert response.json() == USAGE_STATUSES_EXPECTED
