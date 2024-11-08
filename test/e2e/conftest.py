"""
Module providing test fixtures for the e2e tests.
"""

from datetime import datetime
from test.mock_data import VALID_ACCESS_TOKEN
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from httpx import Response

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
                                   that may contain a `unit` key with a unit value that needs to be
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


class E2ETestHelpers:
    """
    A utility class containing common helper methods for e2e tests

    This class provides a set of static methods that encapsulate common functionality frequently used in the e2e tests
    """

    @staticmethod
    def check_created_and_modified_times_updated_correctly(post_response: Response, new_response: Response):
        """Checks that an updated entity has a `created_time` that is the same as its original, but an `updated_time`
        that is newer

        :param post_response: Original response for the entity post request
        :param new_response: Updated response for the entity patch/get request
        """

        original_data = post_response.json()
        updated_data = new_response.json()

        assert original_data["created_time"] == updated_data["created_time"]
        assert datetime.fromisoformat(updated_data["modified_time"]) > datetime.fromisoformat(
            original_data["modified_time"]
        )

    @staticmethod
    def replace_unit_values_with_ids_in_properties(data: dict, unit_value_id_dict: dict[str, str]) -> dict:
        """Inserts unit IDs into some data that may have a 'properties' list within it while removing the unit value.

        :param data: Dictionary of data that could have a 'properties' value within it.
        :param unit_value_id_dict: Dictionary of unit value and ID pairs for unit ID lookups.
        :return: The data with any needed unit IDs inserted.
        """

        if "properties" in data and data["properties"]:
            new_properties = []
            for prop in data["properties"]:
                new_property = {**prop}
                if "unit" in prop:
                    if prop["unit"] is not None:
                        new_property["unit_id"] = unit_value_id_dict[prop["unit"]]
                    else:
                        new_property["unit_id"] = None
                    del new_property["unit"]
                new_properties.append(new_property)
            return {**data, "properties": new_properties}
        return data

    @staticmethod
    def add_unit_ids_to_properties(data: dict, unit_value_id_dict: dict[str, str]) -> dict:
        """Inserts unit IDs into some data that may have a 'properties' list within it.

        :param data: Dictionary of data that could have a 'properties' value within it.
        :param unit_value_id_dict: Dictionary of unit value and ID pairs for unit ID lookups.
        :return: The data with any needed unit IDs inserted.
        """

        if "properties" in data and data["properties"]:
            new_properties = []
            for prop in data["properties"]:
                new_property = {**prop}
                if "unit" in prop:
                    if prop["unit"] is not None:
                        new_property["unit_id"] = unit_value_id_dict[prop["unit"]]
                    else:
                        new_property["unit_id"] = None
                new_properties.append(new_property)
            return {**data, "properties": new_properties}
        return data

    @staticmethod
    def replace_property_names_with_ids_in_properties(data: dict, property_name_id_dict: dict[str, str]) -> dict:
        """Inserts property IDs into some data that may have a 'properties' list within it while removing the property
        name.

        :param data: Dictionary of data that could have a 'properties' value within it.
        :param property_name_id_dict: Dictionary of property name and ID pairs for property ID lookups.
        :return: The data with any needed property IDs inserted.
        """

        if "properties" in data and data["properties"]:
            new_properties = []
            for prop in data["properties"]:
                new_property = {**prop}
                new_property["id"] = property_name_id_dict[prop["name"]]
                del new_property["name"]
                new_properties.append(new_property)
            return {**data, "properties": new_properties}
        return data

    @staticmethod
    def add_property_ids_to_properties(data: dict, property_name_id_dict: dict[str, str]) -> dict:
        """Inserts property IDs into some data that may have a 'properties' list within it.

        :param data: Dictionary of data that could have a 'properties' value within it.
        :param property_name_id_dict: Dictionary of property name and ID pairs for property ID lookups.
        :return: The data with any needed property IDs inserted.
        """

        if "properties" in data and data["properties"]:
            new_properties = []
            for prop in data["properties"]:
                new_property = {**prop}
                new_property["id"] = property_name_id_dict[prop["name"]]
                new_properties.append(new_property)
            return {**data, "properties": new_properties}
        return data
