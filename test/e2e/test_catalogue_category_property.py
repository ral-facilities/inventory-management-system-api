"""
End-to-End tests for the properties endpoint of the catalogue category router
"""

from test.conftest import add_ids_to_properties
from test.e2e.mock_schemas import SYSTEM_POST_A
from typing import Optional
from unittest.mock import ANY

import pytest
from bson import ObjectId
from fastapi import Response
from fastapi.testclient import TestClient

EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST = {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}
EXISTING_CATALOGUE_CATEGORY_PROPERTY_EXPECTED = {**EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST, "allowed_values": None}
EXISTING_PROPERTY_EXPECTED = {"name": "Property A", "unit": "mm", "value": 20}

# pylint:disable=duplicate-code
CATALOGUE_CATEGORY_POST_A = {
    "name": "Category A",
    "is_leaf": True,
    "catalogue_item_properties": [EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST],
}

CATALOGUE_ITEM_POST_A = {
    "name": "Catalogue Item A",
    "description": "This is Catalogue Item A",
    "cost_gbp": 129.99,
    "days_to_replace": 2.0,
    "drawing_link": "https://drawing-link.com/",
    "item_model_number": "abc123",
    "is_obsolete": False,
    "properties": [{"name": "Property A", "value": 20}],
}

MANUFACTURER_POST = {
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

ITEM_POST = {
    "is_defective": False,
    "usage_status": 0,
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "serial_number": "xyz123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
    "properties": [{"name": "Property A", "value": 20}],
}

# pylint:enable=duplicate-code

CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY = {"name": "Property B", "type": "number", "unit": "mm", "mandatory": False}
CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY_EXPECTED = {
    **CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY,
    "allowed_values": None,
}

NEW_CATALOGUE_ITEM_PROPERTY_NON_MANDATORY_EXPECTED = CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY_EXPECTED
NEW_PROPERTY_NON_MANDATORY_EXPECTED = {"name": "Property B", "unit": "mm", "value": None}

CATALOGUE_ITEM_PROPERTY_POST_MANDATORY = {
    "name": "Property B",
    "type": "number",
    "unit": "mm",
    "mandatory": True,
    "default_value": 42,
}
CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED = {
    "name": "Property B",
    "type": "number",
    "unit": "mm",
    "mandatory": True,
    "allowed_values": None,
}

NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED = CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED
NEW_PROPERTY_MANDATORY_EXPECTED = {"name": "Property B", "unit": "mm", "value": 42}


class CreateDSL:
    """Base class for create tests"""

    test_client: TestClient
    catalogue_category: dict
    catalogue_item: dict
    item: dict

    _catalogue_item_post_response: Response
    catalogue_item_property: dict

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""
        self.test_client = test_client

    def post_catalogue_category_and_items(self):
        """Posts a catalogue category, catalogue item and item for create tests to act on"""

        # pylint:disable=duplicate-code
        response = self.test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
        self.catalogue_category = response.json()

        response = self.test_client.post("/v1/systems", json=SYSTEM_POST_A)
        system_id = response.json()["id"]

        response = self.test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
        manufacturer_id = response.json()["id"]

        catalogue_item_post = {
            **CATALOGUE_ITEM_POST_A,
            "catalogue_category_id": self.catalogue_category["id"],
            "manufacturer_id": manufacturer_id,
            "properties": add_ids_to_properties(
                self.catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
            ),
        }
        response = self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)
        self.catalogue_item = response.json()
        catalogue_item_id = self.catalogue_item["id"]

        item_post = {
            **ITEM_POST,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
            "properties": add_ids_to_properties(
                self.catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]
            ),
        }
        response = self.test_client.post("/v1/items", json=item_post)
        self.item = response.json()
        # pylint:enable=duplicate-code

    def post_non_leaf_catalogue_category(self):
        """Posts a non leaf catalogue category"""
        response = self.test_client.post(
            "/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_A, "is_leaf": False}
        )
        self.catalogue_category = response.json()

    def post_catalogue_item_property(self, catalogue_item_property_post, catalogue_category_id: Optional[str] = None):
        """Posts a catalogue item property to the catalogue category"""

        self._catalogue_item_post_response = self.test_client.post(
            f"/v1/catalogue-categories/{
                catalogue_category_id if catalogue_category_id else self.catalogue_category['id']
            }/properties",
            json=catalogue_item_property_post,
        )

    def check_catalogue_item_property_response_success(self, catalogue_item_property_expected):
        """Checks the response of posting a catalogue item property succeeded as expected"""

        assert self._catalogue_item_post_response.status_code == 201
        self.catalogue_item_property = self._catalogue_item_post_response.json()
        assert self.catalogue_item_property == {**catalogue_item_property_expected, "id": ANY}

    def check_catalogue_item_property_response_failed_with_message(self, status_code, detail):
        """Checks the response of posting a catalogue item property failed as expected"""
        assert self._catalogue_item_post_response.status_code == status_code
        assert self._catalogue_item_post_response.json()["detail"] == detail

    def check_catalogue_item_property_response_failed_with_validation_message(self, status_code, message):
        """Checks the response of posting a catalogue item property failed as expected with a pydantic validation
        message"""
        assert self._catalogue_item_post_response.status_code == status_code
        assert self._catalogue_item_post_response.json()["detail"][0]["msg"] == message

    def check_catalogue_category_updated(self, catalogue_item_property_expected):
        """Checks the catalogue category is updated correctly with the new property"""

        new_catalogue_category = self.test_client.get(
            f"/v1/catalogue-categories/{self.catalogue_category['id']}"
        ).json()

        assert new_catalogue_category["catalogue_item_properties"] == add_ids_to_properties(
            [*self.catalogue_category["catalogue_item_properties"], self.catalogue_item_property],
            [EXISTING_CATALOGUE_CATEGORY_PROPERTY_EXPECTED, catalogue_item_property_expected],
        )

    def check_catalogue_item_updated(self, property_expected):
        """Checks the catalogue item is updated correctly with the new property"""

        new_catalogue_item = self.test_client.get(f"/v1/catalogue-items/{self.catalogue_item['id']}").json()

        assert new_catalogue_item["properties"] == add_ids_to_properties(
            [*self.catalogue_category["catalogue_item_properties"], self.catalogue_item_property],
            [EXISTING_PROPERTY_EXPECTED, property_expected],
        )

    def check_item_updated(self, property_expected):
        """Checks the item is updated correctly with the new property"""

        new_item = self.test_client.get(f"/v1/items/{self.item['id']}").json()
        assert new_item["properties"] == add_ids_to_properties(
            [*self.catalogue_category["catalogue_item_properties"], self.catalogue_item_property],
            [EXISTING_PROPERTY_EXPECTED, property_expected],
        )


class TestCreate(CreateDSL):
    """Tests for creating a property at the catalogue category level"""

    def test_create_non_mandatory_property(self):
        """
        Test adding a non-mandatory property to an already existing catalogue category, catalogue item and item
        """

        self.post_catalogue_category_and_items()
        self.post_catalogue_item_property(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY)

        self.check_catalogue_item_property_response_success(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY_EXPECTED)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_NON_MANDATORY_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_NON_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_NON_MANDATORY_EXPECTED)

    def test_create_mandatory_property(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item
        """

        self.post_catalogue_category_and_items()
        self.post_catalogue_item_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY)

        self.check_catalogue_item_property_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

    def test_create_property_with_non_existent_catalogue_category_id(self):
        """Test adding a property when the specified catalogue category doesn't exist"""

        self.post_catalogue_item_property(
            CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY, catalogue_category_id=str(ObjectId())
        )
        self.check_catalogue_item_property_response_failed_with_message(404, "Catalogue category not found")

    def test_create_property_with_invalid_catalogue_category_id(self):
        """Test adding a property when given an invalid catalogue category id"""

        self.post_catalogue_item_property(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY, catalogue_category_id="invalid")
        self.check_catalogue_item_property_response_failed_with_message(404, "Catalogue category not found")

    def test_create_mandatory_property_without_default_value(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item without
        a default value
        """

        self.post_catalogue_category_and_items()
        self.post_catalogue_item_property(
            {
                "name": "Property B",
                "type": "number",
                "unit": "mm",
                "mandatory": True,
            }
        )
        self.check_catalogue_item_property_response_failed_with_message(
            422, "Cannot add a mandatory property without a default value"
        )

    def test_create_mandatory_property_with_invalid_default_value(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item without
        a default value
        """

        self.post_catalogue_category_and_items()
        self.post_catalogue_item_property(
            {
                "name": "Property B",
                "type": "number",
                "unit": "mm",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": [1, 2, 3]},
                "default_value": 42,
            }
        )
        self.check_catalogue_item_property_response_failed_with_validation_message(
            422, "Value error, default_value is not one of the allowed_values"
        )

    def test_create_mandatory_property_with_invalid_default_value_type(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a default value with an invalid type
        """

        self.post_catalogue_category_and_items()
        self.post_catalogue_item_property(
            {"name": "Property B", "type": "number", "unit": "mm", "mandatory": True, "default_value": "wrong_type"}
        )
        self.check_catalogue_item_property_response_failed_with_validation_message(
            422, "Value error, default_value must be the same type as the property itself"
        )

    def test_create_property_non_leaf_catalogue_category(self):
        """
        Test adding a property to an non leaf catalogue category
        """

        self.post_non_leaf_catalogue_category()
        self.post_catalogue_item_property(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY)
        self.check_catalogue_item_property_response_failed_with_message(
            422, "Cannot add a property to a non-leaf catalogue category"
        )
