"""
Module providing test fixtures for the e2e tests.
"""

from typing import Optional
from test.conftest import VALID_ACCESS_TOKEN

import pytest
from fastapi.testclient import TestClient

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.main import app


@pytest.fixture(name="test_client")
def fixture_test_client() -> TestClient:
    """
    Fixture for creating a test client for the application.

    :return: The test client.
    """
    return TestClient(app, headers={"Authorization": f"Bearer {VALID_ACCESS_TOKEN}"})


@pytest.fixture(name="cleanup_database_collections", autouse=True)
def fixture_cleanup_database_collections():
    """
    Fixture to clean up the collections in the test database after the session finishes.
    """
    database = get_database()
    yield
    database.catalogue_categories.delete_many({})
    database.catalogue_items.delete_many({})
    database.items.delete_many({})
    database.manufacturers.delete_many({})
    database.systems.delete_many({})
    database.units.delete_many({})
    database.usage_statuses.delete_many({})


def replace_unit_values_with_ids_in_properties(properties_without_ids: list[dict], units: Optional[list]) -> list[dict]:
    """
    Replaces unit values with unit IDs in the given properties based on matching unit values from a
    provided list of units. If a matching unit value is found in the units list, the corresponding unit
    ID is assigned to the property. If no units list is provided, the unit values in properties remain
    unchanged.

    :param properties_without_ids: The list of properties without IDs. Each property is a dictionary
                                   that may contain a 'unit' key with a unit value that needs to be
                                   replaced by the unit ID.
    :param units: The list of units. Each unit is a dictionary containing 'id' and 'value' keys, where
                  ID is the unique identifier for the unit and 'value' is the unit value to match
                  against the properties. If None, no unit replacement occurs.
    :return: The list of properties with the unit value replaced by the unit ID where applicable.
    """
    properties = []
    if units is None:
        units = []
    unit_id = None

    for property_without_id in properties_without_ids:
        # Shallow copy to avoid modifying the property_without_id dictionary
        property_without_id = {**property_without_id}
        if property_without_id.get("unit") is not None:
            if property_without_id.get("unit_id") is None:
                for unit in units:
                    if property_without_id["unit"] == unit["value"]:
                        unit_id = unit["id"]
                        break
            else:
                unit_id = property_without_id["unit_id"]

            property_without_id["unit_id"] = unit_id

        if "unit" in property_without_id:
            del property_without_id["unit"]

        properties.append(property_without_id)

    return properties
