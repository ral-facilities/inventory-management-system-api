"""
End-to-End tests for the properties endpoint of the catalogue category router
"""

from test.conftest import add_ids_to_properties
from test.e2e.conftest import replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import SYSTEM_POST_A, USAGE_STATUS_POST_A
from test.e2e.test_unit import UNIT_POST_A
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
    "properties": [EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST],
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
    "usage_status": "New",
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
    "default_value": 20,
}
CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED = {
    "name": "Property B",
    "type": "number",
    "unit": "mm",
    "mandatory": True,
    "allowed_values": None,
}

NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED = CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED
NEW_PROPERTY_MANDATORY_EXPECTED = {"name": "Property B", "unit": "mm", "value": 20}

CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES = {
    **CATALOGUE_ITEM_PROPERTY_POST_MANDATORY,
    "allowed_values": {"type": "list", "values": [10, 20, 30]},
}
CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED = {
    **NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED,
    "allowed_values": {"type": "list", "values": [10, 20, 30]},
}
NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_ALLOWED_VALUES_EXPECTED = (
    CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED
)

CATALOGUE_ITEM_PROPERTY_PATCH = {
    "name": "New property name",
    "allowed_values": {"type": "list", "values": [10, 20, 30, 40]},
}

CATALOGUE_ITEM_PROPERTY_PATCH_EXPECTED = {
    **CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED,
    **CATALOGUE_ITEM_PROPERTY_PATCH,
}

NEW_CATALOGUE_ITEM_PROPERTY_PATCH_EXPECTED = CATALOGUE_ITEM_PROPERTY_PATCH_EXPECTED
NEW_PROPERTY_PATCH_EXPECTED = {"name": "New property name", "unit": "mm", "value": 20}

CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY = {
    "allowed_values": {"type": "list", "values": [10, 20, 30, 40]},
}
CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY_EXPECTED = {
    **CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED,
    **CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY,
}


class CreateDSL:
    """Base class for create tests"""

    test_client: TestClient
    catalogue_category: dict
    catalogue_item: dict
    item: dict
    units: list[dict]

    _catalogue_item_post_response: Response
    property: dict

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""

        self.test_client = test_client
        self.units = []

    def post_catalogue_category_and_items(self):
        """Posts a catalogue category, catalogue item and item for create tests to act on"""

        # pylint:disable=duplicate-code

        response = self.test_client.post("/v1/units", json=UNIT_POST_A)
        unit_mm = response.json()

        self.units = [unit_mm]

        response = self.test_client.post(
            "/v1/catalogue-categories",
            json={
                **CATALOGUE_CATEGORY_POST_A,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_A["properties"], self.units
                ),
            },
        )

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
                self.catalogue_category["properties"],
                CATALOGUE_ITEM_POST_A["properties"],
            ),
        }
        response = self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)
        self.catalogue_item = response.json()
        catalogue_item_id = self.catalogue_item["id"]

        response = self.test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
        usage_status_id = response.json()["id"]
        item_post = {
            **ITEM_POST,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
            "usage_status_id": usage_status_id,
            "properties": add_ids_to_properties(self.catalogue_category["properties"], ITEM_POST["properties"]),
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

    def post_property(self, property_post, catalogue_category_id: Optional[str] = None):
        """Posts a property to the catalogue category"""

        property_post = replace_unit_values_with_ids_in_properties([property_post], self.units)[0]
        self._catalogue_item_post_response = self.test_client.post(
            "/v1/catalogue-categories/"
            f"{catalogue_category_id if catalogue_category_id else self.catalogue_category['id']}/properties",
            json=property_post,
        )

    def check_property_post_response_success(self, property_expected):
        """Checks the response of posting a property succeeded as expected"""

        assert self._catalogue_item_post_response.status_code == 201
        self.property = self._catalogue_item_post_response.json()

        assert self.property == {**property_expected, "id": ANY, "unit_id": ANY}

    def check_property_post_response_failed_with_message(self, status_code, detail):
        """Checks the response of posting a property failed as expected"""

        assert self._catalogue_item_post_response.status_code == status_code
        assert self._catalogue_item_post_response.json()["detail"] == detail

    def check_property_post_response_failed_with_validation_message(self, status_code, message):
        """Checks the response of posting a property failed as expected with a pydantic validation
        message"""

        assert self._catalogue_item_post_response.status_code == status_code
        assert self._catalogue_item_post_response.json()["detail"][0]["msg"] == message

    def check_catalogue_category_updated(self, property_expected):
        """Checks the catalogue category is updated correctly with the new property"""

        new_catalogue_category = self.test_client.get(
            f"/v1/catalogue-categories/{self.catalogue_category['id']}"
        ).json()

        assert new_catalogue_category["properties"] == add_ids_to_properties(
            [*self.catalogue_category["properties"], self.property],
            [
                EXISTING_CATALOGUE_CATEGORY_PROPERTY_EXPECTED,
                property_expected,
            ],
        )

    def check_catalogue_item_updated(self, property_expected):
        """Checks the catalogue item is updated correctly with the new property"""

        new_catalogue_item = self.test_client.get(f"/v1/catalogue-items/{self.catalogue_item['id']}").json()

        assert new_catalogue_item["properties"] == add_ids_to_properties(
            [*self.catalogue_category["properties"], self.property],
            [EXISTING_PROPERTY_EXPECTED, property_expected],
        )

    def check_item_updated(self, property_expected):
        """Checks the item is updated correctly with the new property"""

        new_item = self.test_client.get(f"/v1/items/{self.item['id']}").json()
        assert new_item["properties"] == add_ids_to_properties(
            [*self.catalogue_category["properties"], self.property],
            [EXISTING_PROPERTY_EXPECTED, property_expected],
        )


class TestCreate(CreateDSL):
    """Tests for creating a property at the catalogue category level"""

    def test_create_non_mandatory_property(self):
        """
        Test adding a non-mandatory property to an already existing catalogue category, catalogue item and item
        """

        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY)

        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY_EXPECTED)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_NON_MANDATORY_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_NON_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_NON_MANDATORY_EXPECTED)

    def test_create_non_mandatory_property_with_no_unit(self):
        """
        Test adding a non-mandatory property to an already existing catalogue category, catalogue item and item
        with no unit
        """

        self.post_catalogue_category_and_items()
        self.post_property({**CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY, "unit": None})

        self.check_property_post_response_success({**CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY_EXPECTED, "unit": None})
        self.check_catalogue_category_updated({**NEW_CATALOGUE_ITEM_PROPERTY_NON_MANDATORY_EXPECTED, "unit": None})
        self.check_catalogue_item_updated({**NEW_PROPERTY_NON_MANDATORY_EXPECTED, "unit": None})
        self.check_item_updated({**NEW_PROPERTY_NON_MANDATORY_EXPECTED, "unit": None})

    def test_create_mandatory_property(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item
        """

        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY)

        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

    def test_create_mandatory_property_with_allowed_values_list(self):
        """
        Test adding a mandatory property with an allowed values list to an already existing catalogue category,
        catalogue item and item (ensures the default_value is allowed)
        """

        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)

        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_ALLOWED_VALUES_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

    def test_create_property_with_non_existent_catalogue_category_id(self):
        """Test adding a property when the specified catalogue category id is invalid"""

        self.post_property(
            CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY,
            catalogue_category_id=str(ObjectId()),
        )
        self.check_property_post_response_failed_with_message(404, "Catalogue category not found")

    def test_create_property_with_invalid_catalogue_category_id(self):
        """Test adding a property when given an invalid catalogue category id"""

        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY, catalogue_category_id="invalid")
        self.check_property_post_response_failed_with_message(404, "Catalogue category not found")

    def test_create_property_with_invalid_unit_id(self):
        """Test adding a property when given an invalid unit id"""

        self.post_catalogue_category_and_items()

        self.post_property({**CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY, "unit_id": "invalid"})
        self.check_property_post_response_failed_with_message(422, "The specified unit does not exist")

    def test_create_property_with_non_existent_unit_id(self):
        """Test adding a property when the specified unit id is invalid"""

        self.post_catalogue_category_and_items()

        self.post_property({**CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY, "unit_id": str(ObjectId())})
        self.check_property_post_response_failed_with_message(422, "The specified unit does not exist")

    def test_create_mandatory_property_without_default_value(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item without
        a default value
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "number",
                "unit": "mm",
                "mandatory": True,
            }
        )
        self.check_property_post_response_failed_with_message(
            422, "Cannot add a mandatory property without a default value"
        )

    def test_create_mandatory_property_with_invalid_default_value_boolean_int(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item without
        with a default value that is a boolean value while the type of the property is an int (this can cause an
        issue if not implemented property as boolean is a subclass of int - technically also applies to other
        endpoints' type checks but they occur in the same place in code anyway)
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "number",
                "unit": "mm",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": [1, 2, 3]},
                "default_value": True,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422, "Value error, default_value must be the same type as the property itself"
        )

    def test_create_mandatory_property_with_invalid_default_value_not_in_allowed_values_list(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with a
        default value that is excluded by an allowed_values list
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "number",
                "unit": "mm",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": [1, 2, 3]},
                "default_value": 42,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422, "Value error, default_value is not one of the allowed_values"
        )

    def test_create_mandatory_property_with_invalid_default_value_type(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a default value with an invalid type
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "number",
                "unit": "mm",
                "mandatory": True,
                "default_value": "wrong_type",
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422, "Value error, default_value must be the same type as the property itself"
        )

    def test_create_mandatory_property_with_invalid_allowed_values_list_number(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a number type and an allowed_values list with an invalid number
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "number",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": [2, "4", 6]},
                "default_value": False,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_create_mandatory_property_with_invalid_allowed_values_list_string(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a string type and an allowed_values list with an invalid number
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "string",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": ["red", "green", 6]},
                "default_value": False,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_create_mandatory_property_with_invalid_allowed_values_list_duplicate_number(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a number type and an allowed_values list with a duplicate number value in it
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "number",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": [42, 10.2, 12, 42]},
                "default_value": False,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422, "Value error, allowed_values of type 'list' contains a duplicate value: 42"
        )

    def test_create_mandatory_property_with_invalid_allowed_values_list_duplicate_string(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a string type and an allowed_values list with a duplicate string value in it
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "string",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": ["value1", "value2", "value3", "Value2"]},
                "default_value": False,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422, "Value error, allowed_values of type 'list' contains a duplicate value: Value2"
        )

    def test_create_mandatory_property_with_boolean_allowed_values_list(self):
        """
        Test adding a mandatory property to an already existing catalogue category, catalogue item and item with
        a boolean type and an allowed values list is rejected appropriately
        """

        self.post_catalogue_category_and_items()
        self.post_property(
            {
                "name": "Property B",
                "type": "boolean",
                "mandatory": True,
                "allowed_values": {"type": "list", "values": [1, 2, 3]},
                "default_value": False,
            }
        )
        self.check_property_post_response_failed_with_validation_message(
            422, "Value error, allowed_values not allowed for a boolean property 'Property B'"
        )

    def test_create_property_non_leaf_catalogue_category(self):
        """
        Test adding a property to an non leaf catalogue category
        """

        self.post_non_leaf_catalogue_category()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_NON_MANDATORY)
        self.check_property_post_response_failed_with_message(
            422, "Cannot add a property to a non-leaf catalogue category"
        )

    def test_create_property_with_duplicate_name(self):
        """
        Test adding a mandatory property with a name equal to one already existing
        """

        self.post_catalogue_category_and_items()
        self.post_property(EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST)
        self.check_property_post_response_failed_with_message(422, "Duplicate property name: Property A")


class UpdateDSL(CreateDSL):
    """Base class for update tests (inherits CreateDSL to gain access to posts)"""

    _catalogue_item_patch_response: Response

    def patch_property(
        self,
        property_patch,
        catalogue_category_id: Optional[str] = None,
        property_id: Optional[str] = None,
    ):
        """Patches a posted property"""
        self._catalogue_item_patch_response = self.test_client.patch(
            "/v1/catalogue-categories/"
            f"{catalogue_category_id if catalogue_category_id else self.catalogue_category['id']}"
            "/properties/"
            f"{property_id if property_id else self.property['id']}",
            json=property_patch,
        )

    def check_property_patch_response_success(self, property_expected):
        """Checks the response of patching a property succeeded as expected"""

        assert self._catalogue_item_patch_response.status_code == 200
        self.property = self._catalogue_item_patch_response.json()
        assert self.property == {**property_expected, "id": ANY, "unit_id": ANY}

    def check_property_patch_response_failed_with_message(self, status_code, detail):
        """Checks the response of patching a property failed as expected"""

        assert self._catalogue_item_patch_response.status_code == status_code
        assert self._catalogue_item_patch_response.json()["detail"] == detail


class TestUpdate(UpdateDSL):
    """Tests for updating a property at the catalogue category level"""

    def test_update(self):
        """
        Test updating a property at the catalogue category level
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH)

        # Check updated correctly down the tree
        self.check_property_patch_response_success(CATALOGUE_ITEM_PROPERTY_PATCH_EXPECTED)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_PATCH_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_PATCH_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_PATCH_EXPECTED)

    def test_update_category_only(self):
        """
        Test updating a property at the catalogue category level but with an update that should leave the catalogue
        items and items alone (i.e. only updating the allowed values)
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY)

        # Check updated correctly
        self.check_property_patch_response_success(CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY_EXPECTED)
        self.check_catalogue_category_updated(CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY_EXPECTED)
        # These are testing values are the same as they should have been prior to the patch (NEW_ is only there from
        # the create tests)
        self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

    def test_update_category_no_changes_allowed_values_none(self):
        """
        Test updating a property at the catalogue category level but with an update that shouldn't change anything
        (in this case also passing allowed_values as None and keeping it None on the patch request)
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY)
        self.check_property_post_response_success(NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED)

        # Patch the property
        self.patch_property({"name": CATALOGUE_ITEM_PROPERTY_POST_MANDATORY["name"], "allowed_values": None})

        # Check updated correctly
        self.check_property_patch_response_success(NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED)
        # These are testing values are the same as they should have been prior to the patch (NEW_ is only there from
        # the create tests)
        self.check_catalogue_category_updated(NEW_CATALOGUE_ITEM_PROPERTY_MANDATORY_EXPECTED)
        self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
        self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

    def test_update_non_existent_catalogue_category_id(self):
        """
        Test updating a property at the catalogue category level when the specified catalogue category doesn't exist
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH, catalogue_category_id=str(ObjectId()))

        # Check
        self.check_property_patch_response_failed_with_message(404, "Catalogue category not found")

    def test_update_invalid_catalogue_category_id(self):
        """
        Test updating a property at the catalogue category level when the specified catalogue category id is invalid
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH, catalogue_category_id="invalid")

        # Check
        self.check_property_patch_response_failed_with_message(404, "Catalogue category not found")

    def test_update_non_existent_property_id(self):
        """
        Test updating a property at the catalogue category level when the specified property doesn't
        exist in the specified catalogue category
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH, property_id=str(ObjectId()))

        # Check
        self.check_property_patch_response_failed_with_message(404, "Catalogue item property not found")

    def test_update_invalid_property_id(self):
        """
        Test updating a property at the catalogue category level when the specified catalogue item id is invalid
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH, property_id="invalid")

        # Check
        self.check_property_patch_response_failed_with_message(404, "Catalogue item property not found")

    def test_updating_property_to_have_duplicate_name(self):
        """
        Test updating a property to have a name matching another already existing one
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property({"name": EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST["name"]})
        self.check_property_patch_response_failed_with_message(422, "Duplicate property name: Property A")

    def test_updating_property_allowed_values_from_none_to_value(self):
        """
        Test updating a property to have a allowed_values when it was initially None
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_EXPECTED)

        # Patch the property
        self.patch_property(CATALOGUE_ITEM_PROPERTY_PATCH_ALLOWED_VALUES_ONLY)
        self.check_property_patch_response_failed_with_message(422, "Cannot add allowed_values to an existing property")

    def test_updating_property_allowed_values_from_value_to_none(self):
        """
        Test updating a property to have no allowed_values when it initially had
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property({"allowed_values": None})
        self.check_property_patch_response_failed_with_message(
            422, "Cannot remove allowed_values from an existing property"
        )

    def test_updating_property_removing_allowed_values_list(self):
        """
        Test updating a property to remove an element from an allowed values list
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(
            {
                "allowed_values": {
                    "type": "list",
                    # Remove a single value
                    "values": CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"][0:-1],
                }
            }
        )
        self.check_property_patch_response_failed_with_message(
            422, "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
        )

    def test_updating_property_modifying_allowed_values_list(self):
        """
        Test updating a property to modify a value in an allowed values list
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(
            {
                "allowed_values": {
                    "type": "list",
                    # Change only the last value
                    "values": [
                        *CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"][0:-1],
                        42,
                    ],
                }
            }
        )
        self.check_property_patch_response_failed_with_message(
            422, "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
        )

    def test_updating_property_allowed_values_list_adding_with_different_type(self):
        """
        Test updating a property to add a value to an allowed values list but with a different type to the rest
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(
            {
                "allowed_values": {
                    "type": "list",
                    # Change only the last value
                    "values": [
                        *CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"],
                        "different type",
                    ],
                }
            }
        )
        self.check_property_patch_response_failed_with_message(
            422, "allowed_values of type 'list' must only contain values of the same type as the property itself"
        )

    def test_updating_property_allowed_values_list_adding_duplicate_value(self):
        """
        Test updating a property to add a duplicate value to an allowed values list
        """

        # Setup by creating a property to update
        self.post_catalogue_category_and_items()
        self.post_property(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
        self.check_property_post_response_success(CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

        # Patch the property
        self.patch_property(
            {
                "allowed_values": {
                    "type": "list",
                    # Change only the last value
                    "values": [
                        *CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"],
                        CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"][0],
                    ],
                }
            }
        )
        self.check_property_patch_response_failed_with_message(
            422,
            "allowed_values of type 'list' contains a duplicate value: "
            f"{CATALOGUE_ITEM_PROPERTY_POST_MANDATORY_ALLOWED_VALUES['allowed_values']['values'][0]}",
        )
