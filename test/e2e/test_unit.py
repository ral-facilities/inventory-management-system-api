"""
End-to-End tests for the Unit router
"""

import json

import pytest

from inventory_management_system_api.core.database import get_database

# Load in the units data
with open("./data/units.json", "r", encoding="utf-8") as file:
    UNITS = json.load(file)
UNITS_EXPECTED = [{"id": unit["_id"], "value": unit["value"]} for unit in UNITS]


@pytest.fixture(name="add_units_to_database", autouse=True, scope="session")
def fixture_add_units_to_database():
    """
    Fixture to add units to the units collection in the database before any tests in this file run
    """
    units_collection = get_database().units
    units_collection.delete_many({})
    units_collection.insert_many(UNITS)
    yield


def test_get_units(test_client):
    """
    Test getting a list of Units
    """

    response = test_client.get("/v1/units")

    assert response.status_code == 200
    assert response.json() == UNITS_EXPECTED
