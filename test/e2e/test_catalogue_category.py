# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue category router.
"""

from test.conftest import add_ids_to_properties
from test.e2e.conftest import replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import (
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES_EXPECTED,
    CREATED_MODIFIED_VALUES_EXPECTED)
from test.e2e.test_unit import UNIT_POST_A
from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM,
    CATALOGUE_CATEGORY_GET_DATA_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_GET_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM,
    CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT,
    UNIT_POST_DATA_MM)
from typing import Optional
from unittest.mock import ANY

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import Response

from inventory_management_system_api.core.consts import \
    BREADCRUMBS_TRAIL_MAX_LENGTH


class CreateDSL:
    """Base class for create tests"""

    test_client: TestClient

    _post_response: Response

    unit_value_id_dict: dict[str, str]

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""

        self.test_client = test_client
        self.unit_value_id_dict = {}

    def post_unit(self, unit_post_data: dict):
        """Posts a unit with the given data and stores the value and id in a dictionary for lookup later

        :param unit_post_data: Dictionary containing the unit data that should be posted
        """

        post_response = self.test_client.post("/v1/units", json=unit_post_data)
        self.unit_value_id_dict[unit_post_data["value"]] = post_response.json()["id"]

    def add_unit_value_and_id(self, unit_value: str, unit_id: str):
        """Stores a unit value and id inside the `unit_value_id_dict` for tests that need to have a
        non-existent or invalid unit id"""

        self.unit_value_id_dict[unit_value] = unit_id

    def post_catalogue_category(self, catalogue_category_data: dict) -> Optional[str]:
        """Posts a catalogue category with the given data and returns the id of the created catalogue category if
        successful

        :param catalogue_category_data: Dictionary containing the basic catalogue category data as would be required
                                        for a CatalogueCategoryPostSchema but with any unit_id's replaced by the
                                        'unit' value in its properties as the ids will be added automatically
        :return: ID of the created catalogue category (or None if not successful)
        """

        # Replace any unit values with unit ids
        if "properties" in catalogue_category_data and catalogue_category_data["properties"]:
            new_properties = []
            for prop in catalogue_category_data["properties"]:
                new_property = {**prop}
                if "unit" in prop:
                    if prop["unit"] is not None:
                        new_property["unit_id"] = self.unit_value_id_dict[prop["unit"]]
                    else:
                        new_property["unit_id"] = None
                    del new_property["unit"]
                new_properties.append(new_property)
            catalogue_category_data = {**catalogue_category_data, "properties": new_properties}

        self._post_response = self.test_client.post("/v1/catalogue-categories", json=catalogue_category_data)

        return self._post_response.json()["id"] if self._post_response.status_code == 201 else None

    def post_leaf_catalogue_category_with_allowed_values(self, property_type: str, allowed_values_post_data: dict):
        """Utility method that posts a leaf catalogue category with a property named 'property' of a given type with
        a given set of allowed values"""

        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY,
                "properties": [
                    {
                        "name": "property",
                        "type": property_type,
                        "mandatory": False,
                        "allowed_values": allowed_values_post_data,
                    }
                ],
            }
        )

    def check_post_catalogue_category_success(self, expected_catalogue_category_get_data: dict):
        """Checks that a prior call to 'post_catalogue_category' gave a successful response with the expected data
        returned"""

        assert self._post_response.status_code == 201
        assert self._post_response.json() == expected_catalogue_category_get_data

    def check_post_catalogue_category_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'post_catalogue_category' gave a failed response with the expected code and
        error message"""

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"] == detail

    def check_post_catalogue_category_failed_with_validation_message(self, status_code: int, message: str):
        """Checks that a prior call to 'post_catalogue_category' gave a failed response with the expected code and
        pydantic validation error message"""

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category"""

    def test_create_non_leaf_with_only_required_values_provided(self):
        """Test creating a non-leaf catalogue category with only required values provided"""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)

    def test_create_non_leaf_with_properties(self):
        """Test creating a non-leaf catalogue category with properties provided (ensures they are ignored)"""

        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT],
            }
        )
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)

    def test_create_with_valid_parent_id(self):
        """Test creating a catalogue category with a valid parent id"""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.check_post_catalogue_category_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )

    def test_create_with_non_leaf_parent(self):
        """Test creating a catalogue category with a non-leaf parent"""

        parent_id = self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "is_leaf": True}
        )
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        # TODO: Why is this a 409????
        self.check_post_catalogue_category_failed_with_message(
            409, "Adding a catalogue category to a leaf parent catalogue category is not allowed"
        )

    def test_create_with_non_existent_parent_id(self):
        """Test creating a catalogue category with a non-existent parent id"""

        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": str(ObjectId())}
        )
        self.check_post_catalogue_category_failed_with_message(
            422, "The specified parent catalogue category does not exist"
        )

    def test_create_with_invalid_parent_id(self):
        """Test creating a catalogue category with an invalid parent id"""

        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": "invalid-id"}
        )
        self.check_post_catalogue_category_failed_with_message(
            422, "The specified parent catalogue category does not exist"
        )

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a catalogue category with the same name as another within the parent catalogue category"""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        # 2nd post should be the duplicate
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.check_post_catalogue_category_failed_with_message(
            409, "A catalogue category with the same name already exists within the parent catalogue category"
        )

    def test_create_leaf_with_only_required_values_provided(self):
        """Test creating a leaf catalogue category with only required values provided"""

        self.post_catalogue_category({**CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY, "is_leaf": True})
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_LEAF_REQUIRED_VALUES_ONLY)

    def test_create_leaf_with_properties(self):
        """Test creating a leaf catalogue category with some properties provided"""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM)
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM)

    def test_create_leaf_with_properties_with_non_existent_unit_id(self):
        """Test creating a leaf catalogue category with a property with a non-existent unit id provided"""

        self.add_unit_value_and_id("mm", str(ObjectId()))
        self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM)
        self.check_post_catalogue_category_failed_with_message(422, "The specified unit does not exist")

    def test_create_leaf_with_properties_with_invalid_unit_id(self):
        """Test creating a leaf catalogue category with a property with an invalid unit id provided"""

        self.add_unit_value_and_id("mm", "invalid-id")
        self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM)
        self.check_post_catalogue_category_failed_with_message(422, "The specified unit does not exist")

    def test_create_leaf_with_duplicate_properties(self):
        """Test creating a leaf catalogue category with some properties provided"""

        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM,
                "properties": [
                    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT,
                    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT,
                ],
            }
        )
        self.check_post_catalogue_category_failed_with_message(
            422, f"Duplicate property name: {CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT["name"]}"
        )

    def test_create_leaf_with_property_with_invalid_type(self):
        """Test creating a leaf catalogue category with a property with an invalid type provided"""

        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM,
                "properties": [
                    {**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT, "type": "invalid-type"}
                ],
            }
        )
        self.check_post_catalogue_category_failed_with_validation_message(
            422, "Input should be 'string', 'number' or 'boolean'"
        )

    def test_create_leaf_with_boolean_property_with_unit(self):
        """Test creating a leaf catalogue category with a boolean property with a unit"""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM,
                "properties": [{**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT, "unit": "mm"}],
            }
        )
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, Unit not allowed for boolean property "
            f"'{CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY_WITHOUT_UNIT['name']}'",
        )

    def test_create_leaf_property_with_invalid_allowed_values_type(self):
        """Test creating a leaf catalogue category with a property with an invalid allowed values type"""

        self.post_leaf_catalogue_category_with_allowed_values("string", {"type": "invalid-type"})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Input tag 'invalid-type' found using 'type' does not match any of the expected tags: 'list'",
        )

    def test_create_leaf_property_with_empty_allowed_values_list(self):
        """Test creating a leaf catalogue category with a property with an allowed values list that is empty"""

        self.post_leaf_catalogue_category_with_allowed_values("string", {"type": "list", "values": []})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "List should have at least 1 item after validation, not 0",
        )

    def test_create_leaf_with_string_property_with_allowed_values_list_invalid_value(self):
        """Test creating a leaf catalogue category with a string property with an allowed values list with an invalid
        number value in it"""

        self.post_leaf_catalogue_category_with_allowed_values("string", {"type": "list", "values": ["1", "2", 3, "4"]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself",
        )

    def test_create_leaf_with_string_property_with_allowed_values_list_duplicate_value(self):
        """Test creating a leaf catalogue category with a string property with an allowed values list with a duplicate
        string value in it"""

        # Capitalisation is different as it shouldn't matter for this test
        self.post_leaf_catalogue_category_with_allowed_values(
            "string", {"type": "list", "values": ["value1", "value2", "Value1", "value3"]}
        )
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: Value1",
        )

    def test_create_leaf_with_number_property_with_allowed_values_list_invalid_value(self):
        """Test creating a leaf catalogue category with a number property with an allowed values list with an invalid
        number value in it"""

        self.post_leaf_catalogue_category_with_allowed_values("number", {"type": "list", "values": [1, 2, "3", 4]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself",
        )

    def test_create_leaf_with_number_property_with_allowed_values_list_duplicate_value(self):
        """Test creating a leaf catalogue category with a number property with an allowed values list with a duplicate
        number value in it"""

        self.post_leaf_catalogue_category_with_allowed_values("number", {"type": "list", "values": [1, 2, 1, 3]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: 1",
        )

    def test_create_leaf_with_boolean_property_with_allowed_values_list(self):
        """Test creating a leaf catalogue category with a boolean property with an allowed values list"""

        self.post_leaf_catalogue_category_with_allowed_values("boolean", {"type": "list", "values": [True, False]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values not allowed for a boolean property 'property'",
        )


class GetDSL(CreateDSL):
    """Base class for get tests"""

    _get_response: Response

    def get_catalogue_category(self, catalogue_category_id: str):
        """Gets a system with the given id"""

        self._get_response = self.test_client.get(f"/v1/catalogue-categories/{catalogue_category_id}")

    def check_get_catalogue_category_success(self, expected_catalogue_category_get_data: dict):
        """Checks that a prior call to 'get_catalogue_category' gave a successful response with the expected data returned"""

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_catalogue_category_get_data

    def check_get_catalogue_category_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'get_catalogue_category' gave a failed response with the expected code and error message"""

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a catalogue category"""

    def test_get(self):
        """Test getting a catalogue category"""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM)
        self.get_catalogue_category(catalogue_category_id)
        self.check_get_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_LEAF_WITH_PROPERTIES_NO_PARENT_MM)

    def test_get_with_non_existent_id(self):
        """Test getting a catalogue category with a non-existent id"""

        self.get_catalogue_category(str(ObjectId()))
        self.check_get_catalogue_category_failed_with_message(404, "Catalogue category not found")

    def test_get_with_invalid_id(self):
        """Test getting a catalogue category with an invalid id"""

        self.get_catalogue_category("invalid-id")
        self.check_get_catalogue_category_failed_with_message(404, "Catalogue category not found")


# TODO: Abstract this and the following tests as they are the same for systems only with different names
class GetBreadcrumbsDSL(GetDSL):
    """Base class for breadcrumbs tests"""

    _get_response: Response

    _posted_catalogue_categories_get_data: list[dict]

    @pytest.fixture(autouse=True)
    def setup_breadcrumbs_dsl(self):
        """Setup fixtures"""

        self._posted_catalogue_categories_get_data = []

    def post_nested_catalogue_categories(self, number: int) -> list[Optional[str]]:
        """Posts the given number of nested catalogue categories where each successive one has the previous as its parent

        :param number: Number of catalogue categories to create
        :return: List of ids of the created catalogue categories
        """

        parent_id = None
        for i in range(0, number):
            catalogue_category_id = self.post_catalogue_category(
                {
                    **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
                    "name": f"Catalogue Category {i}",
                    "parent_id": parent_id,
                }
            )
            self._posted_catalogue_categories_get_data.append(self._post_response.json())
            parent_id = catalogue_category_id

        return [catalogue_category["id"] for catalogue_category in self._posted_catalogue_categories_get_data]

    def get_catalogue_category_breadcrumbs(self, catalogue_category_id: str):
        """Gets a catalogue category's breadcrumbs with the given id"""

        self._get_response = self.test_client.get(f"/v1/catalogue-categories/{catalogue_category_id}/breadcrumbs")

    def get_last_catalogue_category_breadcrumbs(self):
        """Gets the last catalogue category posted's breadcrumbs"""

        self.get_catalogue_category_breadcrumbs(self._post_response.json()["id"])

    def check_get_catalogue_categories_breadcrumbs_success(self, expected_trail_length: int, expected_full_trail: bool):
        """Checks that a prior call to 'get_catalogue_category_breadcrumbs' gave a successful response with the
        expected data returned
        """

        assert self._get_response.status_code == 200
        assert self._get_response.json() == {
            "trail": [
                [catalogue_category["id"], catalogue_category["name"]]
                # When the expected trail length is < the number of systems posted, only use the last
                for catalogue_category in self._posted_catalogue_categories_get_data[
                    (len(self._posted_catalogue_categories_get_data) - expected_trail_length) :
                ]
            ],
            "full_trail": expected_full_trail,
        }

    def check_get_catalogue_categories_breadcrumbs_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'get_catalogue_category_breadcrumbs' gave a failed response with the expected
        code and error message"""

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting a system's breadcrumbs"""

    def test_get_breadcrumbs_when_no_parent(self):
        """Test getting a system's breadcrumbs when the system has no parent"""

        self.post_nested_catalogue_categories(1)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(expected_trail_length=1, expected_full_trail=True)

    def test_get_breadcrumbs_when_trail_length_less_than_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail should be less than the maximum trail
        length"""

        self.post_nested_catalogue_categories(BREADCRUMBS_TRAIL_MAX_LENGTH - 1)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH - 1, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail should be equal to the maximum trail
        length"""

        self.post_nested_catalogue_categories(BREADCRUMBS_TRAIL_MAX_LENGTH)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_greater_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail exceeds the maximum trail length"""

        self.post_nested_catalogue_categories(BREADCRUMBS_TRAIL_MAX_LENGTH + 1)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=False
        )

    def test_get_breadcrumbs_with_non_existent_id(self):
        """Test getting a system's breadcrumbs when given a non-existent system id"""

        self.get_catalogue_category_breadcrumbs(str(ObjectId()))
        self.check_get_catalogue_categories_breadcrumbs_failed_with_message(404, "Catalogue category not found")

    def test_get_breadcrumbs_with_invalid_id(self):
        """Test getting a system's breadcrumbs when given an invalid system id"""

        self.get_catalogue_category_breadcrumbs("invalid_id")
        self.check_get_catalogue_categories_breadcrumbs_failed_with_message(404, "Catalogue category not found")


class ListDSL(GetBreadcrumbsDSL):
    """Base class for list tests"""

    def get_catalogue_categories(self, filters: dict):
        """Gets a list catalogue categories with the given filters"""

        self._get_response = self.test_client.get("/v1/catalogue-categories", params=filters)

    def post_test_catalogue_category_with_child(self) -> list[dict]:
        """Posts a catalogue category with a single child and returns their expected responses when returned by the
        list endpoint"""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )

        return [
            CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id},
        ]

    def check_get_catalogue_categories_success(self, expected_systems_get_data: list[dict]):
        """Checks that a prior call to 'get_catalogue_categories' gave a successful response with the expected data
        returned"""

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_systems_get_data


class TestList(ListDSL):
    """Tests for getting a list of catalogue categories"""

    def test_list_with_no_filters(self):
        """Test getting a list of all catalogue categories with no filters provided

        Posts a catalogue category with a child and expects both to be returned.
        """

        catalogue_categories = self.post_test_catalogue_category_with_child()
        self.get_catalogue_categories(filters={})
        self.check_get_catalogue_categories_success(catalogue_categories)

    def test_list_with_parent_id_filter(self):
        """Test getting a list of all catalogue categories with a parent_id filter provided

        Posts a catalogue category with a child and then filter using the parent_id expecting only the second
        catalogue category to be returned.
        """

        catalogue_categories = self.post_test_catalogue_category_with_child()
        self.get_catalogue_categories(filters={"parent_id": catalogue_categories[1]["parent_id"]})
        self.check_get_catalogue_categories_success([catalogue_categories[1]])

    def test_list_with_null_parent_id_filter(self):
        """Test getting a list of all catalogue categories with a parent_id filter of "null" provided

        Posts a catalogue category with a child and then filter using a parent_id of "null" expecting only
        the first parent catalogue category to be returned.
        """

        catalogue_categories = self.post_test_catalogue_category_with_child()
        self.get_catalogue_categories(filters={"parent_id": "null"})
        self.check_get_catalogue_categories_success([catalogue_categories[0]])

    def test_list_with_parent_id_filter_with_no_matching_results(self):
        """Test getting a list of all systems with a parent_id filter that returns no results"""

        self.get_catalogue_categories(filters={"parent_id": str(ObjectId())})
        self.check_get_catalogue_categories_success([])

    def test_list_with_invalid_parent_id_filter(self):
        """Test getting a list of all systems with an invalid parent_id filter returns no results"""

        self.get_catalogue_categories(filters={"parent_id": "invalid-id"})
        self.check_get_catalogue_categories_success([])

# TODO: Add update tests and use UpdateDSL here
class DeleteDSL(GetBreadcrumbsDSL):
    """Base class for delete tests"""

    _delete_response: Response

    def delete_catalogue_category(self, system_id: str):
        """Deletes a catalogue_category with the given id"""

        self._delete_response = self.test_client.delete(f"/v1/catalogue-categories/{system_id}")

    def check_delete_catalogue_category_success(self):
        """Checks that a prior call to 'delete_catalogue_category' gave a successful response with the expected data returned"""

        assert self._delete_response.status_code == 204

    def check_delete_catalogue_category_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'delete_catalogue_category' gave a failed response with the expected code and error
        message"""

        assert self._delete_response.status_code == status_code
        assert self._delete_response.json()["detail"] == detail

class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue category"""

    def test_delete(self):
        """Test deleting a catalogue category"""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.delete_catalogue_category(catalogue_category_id)
        self.check_delete_catalogue_category_success()

        self.get_catalogue_category(catalogue_category_id)
        self.check_get_catalogue_category_failed_with_message(404, "Catalogue category not found")

    def test_delete_with_child_catalogue_category(self):
        """Test deleting a catalogue category with a child catalogue category"""

        catalogue_category_ids = self.post_nested_catalogue_categories(2)
        self.delete_catalogue_category(catalogue_category_ids[0])
        # TODO: Should this be 409?
        self.check_delete_catalogue_category_failed_with_message(409, "Catalogue category has child elements and cannot be deleted")

    def test_delete_with_child_item(self):
        """Test deleting a catalogue category with a child catalogue item"""

        # pylint:disable=fixme
        # TODO: THIS SHOULD BE CLEANED UP IN FUTURE
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY)

        # Create a child catalogue item
        # pylint: disable=duplicate-code
        response = self.test_client.post("/v1/manufacturers", json={
            "name": "Manufacturer D",
            "url": "http://example.com/",
            "address": {
                "address_line": "1 Example Street",
                "town": "Oxford",
                "county": "Oxfordshire",
                "country": "United Kingdom",
                "postcode": "OX1 2AB",
            },
            "telephone": "0932348348",
        })
        manufacturer_id = response.json()["id"]

        catalogue_item_post = {
            "name": "Catalogue Item A",
            "description": "This is Catalogue Item A",
            "cost_gbp": 129.99,
            "days_to_replace": 2.0,
            "is_obsolete": False,
            "catalogue_category_id": catalogue_category_id,
            "manufacturer_id": manufacturer_id,
            "properties": [],
        }
        self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)
        # pylint: enable=duplicate-code

        self.delete_catalogue_category(catalogue_category_id)
        # TODO: Should this be 409?
        self.check_delete_catalogue_category_failed_with_message(409, "Catalogue category has child elements and cannot be deleted")

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent catalogue category"""

        self.delete_catalogue_category(str(ObjectId()))
        self.check_delete_catalogue_category_failed_with_message(404, "Catalogue category not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a catalogue category with an invalid id"""

        self.delete_catalogue_category("invalid_id")
        self.check_delete_catalogue_category_failed_with_message(404, "Catalogue category not found")

# CATALOGUE_CATEGORY_POST_A = {"name": "Category A", "is_leaf": False}
# CATALOGUE_CATEGORY_POST_A_EXPECTED = {
#     **CATALOGUE_CATEGORY_POST_A,
#     **CREATED_MODIFIED_VALUES_EXPECTED,
#     "id": ANY,
#     "code": "category-a",
#     "parent_id": None,
#     "properties": [],
# }

# # To be posted as a child of the above - leaf with parent
# CATALOGUE_CATEGORY_POST_B = {
#     "name": "Category B",
#     "is_leaf": True,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "boolean", "mandatory": True},
#     ],
# }
# CATALOGUE_CATEGORY_POST_B_EXPECTED = {
#     **CATALOGUE_CATEGORY_POST_B,
#     **CREATED_MODIFIED_VALUES_EXPECTED,
#     "id": ANY,
#     "code": "category-b",
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False, "allowed_values": None},
#         {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True, "allowed_values": None},
#     ],
# }

# # Leaf with no parent
# CATALOGUE_CATEGORY_POST_C = {
#     "name": "Category C",
#     "is_leaf": True,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
#     ],
# }
# CATALOGUE_CATEGORY_POST_C_EXPECTED = {
#     **CATALOGUE_CATEGORY_POST_C,
#     **CREATED_MODIFIED_VALUES_EXPECTED,
#     "id": ANY,
#     "code": "category-c",
#     "parent_id": None,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False, "allowed_values": None},
#         {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True, "allowed_values": None},
#     ],
# }

# # pylint: disable=duplicate-code
# MANUFACTURER = {
#     "name": "Manufacturer D",
#     "url": "http://example.com/",
#     "address": {
#         "address_line": "1 Example Street",
#         "town": "Oxford",
#         "county": "Oxfordshire",
#         "country": "United Kingdom",
#         "postcode": "OX1 2AB",
#     },
#     "telephone": "0932348348",
# }
# # pylint: enable=duplicate-code

# CATALOGUE_ITEM_POST_A = {
#     "name": "Catalogue Item A",
#     "description": "This is Catalogue Item A",
#     "cost_gbp": 129.99,
#     "days_to_replace": 2.0,
#     "is_obsolete": False,
#     "properties": [{"name": "Property B", "value": False}],
# }


# def _post_nested_catalogue_categories(test_client, entities: list[dict]):
#     """Utility function for posting a set of mock catalogue categories where each successive entity should
#     be the parent of the next"""

#     categories = []
#     parent_id = None
#     for entity in entities:
#         system = test_client.post("/v1/catalogue-categories", json={**entity, "parent_id": parent_id}).json()
#         parent_id = system["id"]
#         categories.append(system)

#     return (*categories,)


# def _post_catalogue_categories(test_client):
#     """Utility function for posting all mock systems defined at the top of this file"""

#     units, _ = _post_units(test_client)

#     (category_a, category_b, *_) = _post_nested_catalogue_categories(
#         test_client,
#         [
#             CATALOGUE_CATEGORY_POST_A,
#             {
#                 **CATALOGUE_CATEGORY_POST_B,
#                 "properties": replace_unit_values_with_ids_in_properties(
#                     CATALOGUE_CATEGORY_POST_B["properties"], units
#                 ),
#             },
#         ],
#     )
#     (category_c, *_) = _post_nested_catalogue_categories(
#         test_client,
#         [
#             {
#                 **CATALOGUE_CATEGORY_POST_C,
#                 "properties": replace_unit_values_with_ids_in_properties(
#                     CATALOGUE_CATEGORY_POST_C["properties"], units
#                 ),
#             }
#         ],
#     )

#     return category_a, category_b, category_c


# def _post_n_catalogue_categories(test_client, number):
#     """Utility function to post a given number of nested catalogue categories (all based on system A)"""
#     return _post_nested_catalogue_categories(
#         test_client,
#         [
#             {
#                 **CATALOGUE_CATEGORY_POST_A,
#                 "name": f"Category {i}",
#             }
#             for i in range(0, number)
#         ],
#     )


# def _post_units(test_client):
#     """Utility function for posting all mock units defined at the top of this file"""

#     response = test_client.post("/v1/units", json=UNIT_POST_A)

#     unit_mm = response.json()

#     units = [unit_mm]

#     unit_value_to_id = {unit_mm["value"]: unit_mm["id"]}
#     return units, unit_value_to_id


# def test_partial_update_catalogue_category_change_name(test_client):
#     """
#     Test changing the name of a catalogue category.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

#     catalogue_category_patch = {"name": "Category B"}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **CATALOGUE_CATEGORY_POST_A_EXPECTED,
#         **catalogue_category_patch,
#         "code": "category-b",
#     }


# def test_partial_update_catalogue_category_change_capitalisation_of_name(test_client):
#     """
#     Test changing the capitalisation of the name of a catalogue category.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

#     catalogue_category_patch = {"name": "CaTeGoRy A"}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **CATALOGUE_CATEGORY_POST_A_EXPECTED,
#         **catalogue_category_patch,
#     }


# def test_partial_update_catalogue_category_change_name_duplicate(test_client):
#     """
#     Test changing the name of a catalogue category to a name that already exists.
#     """
#     test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

#     units, _ = _post_units(test_client)

#     response = test_client.post(
#         "/v1/catalogue-categories",
#         json={
#             **CATALOGUE_CATEGORY_POST_B,
#             "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
#         },
#     )

#     catalogue_category_patch = {"name": "Category A"}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 409
#     assert (
#         response.json()["detail"]
#         == "A catalogue category with the same name already exists within the parent catalogue category"
#     )


# def test_partial_update_catalogue_category_change_valid_parameters_when_has_child_catalogue_categories(test_client):
#     """
#     Test changing valid parameters of a catalogue category which has child catalogue categories.
#     """
#     category_a, _, _ = _post_catalogue_categories(test_client)

#     catalogue_category_patch = {"name": "Category D"}
#     response = test_client.patch(f"/v1/catalogue-categories/{category_a['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **CATALOGUE_CATEGORY_POST_A_EXPECTED,
#         **catalogue_category_patch,
#         "code": "category-d",
#     }


# def test_partial_update_catalogue_category_change_valid_when_has_child_catalogue_items(test_client):
#     """
#     Test changing valid parameters of a catalogue category which has child catalogue items.
#     """

#     units, _ = _post_units(test_client)

#     response = test_client.post(
#         "/v1/catalogue-categories",
#         json={
#             **CATALOGUE_CATEGORY_POST_C,
#             "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
#         },
#     )

#     catalogue_category = response.json()
#     catalogue_item_post = {**CATALOGUE_ITEM_POST_A, "catalogue_category_id": catalogue_category["id"]}
#     test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_category_patch = {"name": "Category D"}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **CATALOGUE_CATEGORY_POST_C_EXPECTED,
#         **catalogue_category_patch,
#         "code": "category-d",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_CATEGORY_POST_C_EXPECTED["properties"],
#         ),
#     }


# def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf(test_client):
#     """
#     Test changing a catalogue category from non-leaf to leaf.
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     catalogue_category_patch = {
#         "is_leaf": True,
#         "properties": [
#             {
#                 "name": "Property A",
#                 "type": "number",
#                 "unit_id": unit_value_to_id["mm"],
#                 "unit": "mm",
#                 "mandatory": False,
#                 "allowed_values": None,
#             }
#         ],
#     }

#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     catalogue_category = response.json()
#     assert catalogue_category == {
#         **catalogue_category_post,
#         **{
#             **catalogue_category_patch,
#             "properties": add_ids_to_properties(
#                 catalogue_category["properties"],
#                 catalogue_category_patch["properties"],
#             ),
#         },
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "id": ANY,
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_without_properties(test_client):
#     """
#     Test changing a catalogue category from non-leaf to leaf without supplying any properties.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {"is_leaf": True}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **catalogue_category_post,
#         **catalogue_category_patch,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "id": ANY,
#         "properties": [],
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_has_child_catalogue_categories(test_client):
#     """
#     Test changing a catalogue category with child catalogue categories from non-leaf to leaf.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_id = response.json()["id"]
#     catalogue_category_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_id}
#     test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {
#         "is_leaf": True,
#         "properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
#     }
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


# def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf(test_client):
#     """
#     Test changing a catalogue category from leaf to non-leaf.
#     """
#     _, unit_value_to_id = _post_units(test_client)
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": [
#             {
#                 "name": "Property A",
#                 "type": "number",
#                 "unit": "mm",
#                 "unit_id": unit_value_to_id["mm"],
#                 "mandatory": False,
#             }
#         ],
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {"is_leaf": False}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **catalogue_category_post,
#         **catalogue_category_patch,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "id": ANY,
#         "properties": [],
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_has_child_catalogue_items(test_client):
#     """
#     Test changing a catalogue category with child catalogue items from leaf to non-leaf.
#     """
#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
#     catalogue_category = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     # pylint: enable=duplicate-code
#     test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_category_patch = {"is_leaf": False}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category['id']}", json=catalogue_category_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


# def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_with_properties(test_client):
#     """
#     Test changing a catalogue category from leaf to non-leaf while also changing its properties.
#     """
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {
#         "is_leaf": False,
#         "properties": [{"name": "Property B", "type": "boolean", "mandatory": True}],
#     }
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **catalogue_category_post,
#         **catalogue_category_patch,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "id": ANY,
#         "properties": [],
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_change_parent_id(test_client):
#     """
#     Test moving a catalogue category to another parent catalogue category.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_a_id = response.json()["id"]

#     units, _ = _post_units(test_client)

#     catalogue_category_post = {
#         "name": "Category B",
#         "is_leaf": True,
#         "parent_id": catalogue_category_a_id,
#         "properties": replace_unit_values_with_ids_in_properties([CATALOGUE_CATEGORY_POST_B["properties"][0]], units),
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_b_id = response.json()["id"]

#     catalogue_category_patch = {"parent_id": None}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     catalogue_category = response.json()
#     assert catalogue_category == {
#         **{
#             **catalogue_category_post,
#             "properties": add_ids_to_properties(
#                 catalogue_category["properties"],
#                 [CATALOGUE_CATEGORY_POST_B_EXPECTED["properties"][0]],
#             ),
#         },
#         **catalogue_category_patch,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "id": ANY,
#         "code": "category-b",
#     }


# def test_partial_update_catalogue_category_change_parent_id_to_child_id(test_client):
#     """
#     Test updating a catalogue categories's parent_id to be the id of one of its children
#     """
#     nested_categories = _post_n_catalogue_categories(test_client, 4)

#     # Attempt to move first into one of its children
#     response = test_client.patch(
#         f"/v1/catalogue-categories/{nested_categories[0]['id']}", json={"parent_id": nested_categories[3]["id"]}
#     )

#     assert response.status_code == 422
#     assert response.json()["detail"] == "Cannot move a catalogue category to one of its own children"


# def test_partial_update_catalogue_category_change_parent_id_has_child_catalogue_categories(test_client):
#     """
#     Test moving a catalogue category with child categories to another parent catalogue category.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_a_id = response.json()["id"]
#     catalogue_category_b_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_a_id}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_b_post)
#     catalogue_category_b_id = response.json()["id"]
#     catalogue_category_post = {"name": "Category C", "is_leaf": False, "parent_id": catalogue_category_b_id}
#     test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {"parent_id": None}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **catalogue_category_b_post,
#         **catalogue_category_patch,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "properties": [],
#         "id": ANY,
#         "code": "category-b",
#     }


# def test_partial_update_catalogue_category_change_parent_id_has_child_catalogue_items(test_client):
#     """
#     Test moving a catalogue category with child catalogue items to another parent catalogue category.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_a_id = response.json()["id"]
#     catalogue_category_b_post = {"name": "Category B", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_b_post)
#     catalogue_category_b_id = response.json()["id"]
#     catalogue_category_post = {
#         "name": "Category C",
#         "is_leaf": True,
#         "parent_id": catalogue_category_b_id,
#         "properties": [
#             {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#             {"name": "Property B", "type": "boolean", "mandatory": True},
#         ],
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_c_id = response.json()["id"]

#     catalogue_item_post = {**CATALOGUE_ITEM_POST_A, "catalogue_category_id": catalogue_category_c_id}
#     test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_category_patch = {"parent_id": catalogue_category_a_id}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     assert response.json() == {
#         **catalogue_category_b_post,
#         **catalogue_category_patch,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "properties": [],
#         "id": ANY,
#         "code": "category-b",
#     }


# def test_partial_update_catalogue_category_change_parent_id_duplicate_name(test_client):
#     """
#     Test moving a catalogue category to another parent catalogue category in which a category with the same name already
#     exists.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
#     catalogue_category_c_id = response.json()["id"]

#     catalogue_category_post = {"name": "Category B", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_b_id = response.json()["id"]

#     catalogue_category_post = {"name": "Category C", "is_leaf": False, "parent_id": catalogue_category_b_id}
#     test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {"parent_id": catalogue_category_b_id}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_c_id}", json=catalogue_category_patch)

#     assert response.status_code == 409
#     assert (
#         response.json()["detail"]
#         == "A catalogue category with the same name already exists within the parent catalogue category"
#     )


# def test_partial_update_catalogue_category_change_parent_id_leaf_parent_catalogue_category(test_client):
#     """
#     Test moving a catalogue category to a leaf parent catalogue category.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
#     catalogue_category_c_id = response.json()["id"]

#     catalogue_category_post = {"name": "Category B", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
#     catalogue_category_b_id = response.json()["id"]

#     catalogue_category_patch = {"parent_id": catalogue_category_c_id}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Adding a catalogue category to a leaf parent catalogue category is not allowed"


# def test_partial_update_catalogue_category_change_parent_id_invalid_id(test_client):
#     """
#     Test changing the parent ID of a catalogue category to an invalid ID.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {"parent_id": "invalid"}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified parent catalogue category does not exist"


# def test_partial_update_catalogue_category_change_parent_id_non_existent_id(test_client):
#     """
#     Test changing the parent ID of a catalogue category to a non-existent ID.
#     """
#     catalogue_category_post = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     catalogue_category_patch = {"parent_id": str(ObjectId())}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified parent catalogue category does not exist"


# def test_partial_update_catalogue_category_add_property(test_client):
#     """
#     Test adding a property.
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {
#             "name": "Property A",
#             "type": "number",
#             "unit": "mm",
#             "unit_id": unit_value_to_id["mm"],
#             "mandatory": False,
#             "allowed_values": None,
#         }
#     ]
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties.append({"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None})
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     properties[1]["unit"] = None
#     catalogue_category = response.json()
#     assert catalogue_category == {
#         **catalogue_category_post,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
#         "id": ANY,
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_remove_property(test_client):
#     """
#     Test removing a property.
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {
#             "name": "Property A",
#             "type": "number",
#             "unit": "mm",
#             "unit_id": unit_value_to_id["mm"],
#             "mandatory": False,
#             "allowed_values": None,
#         },
#         {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
#     ]
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties.pop(0)
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     properties[0]["unit"] = None
#     catalogue_category = response.json()
#     assert catalogue_category == {
#         **catalogue_category_post,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
#         "id": ANY,
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_modify_property(test_client):
#     """
#     Test modifying a property.
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {
#             "name": "Property A",
#             "type": "number",
#             "unit": "mm",
#             "unit_id": unit_value_to_id["mm"],
#             "mandatory": False,
#             "allowed_values": None,
#         },
#         {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
#     ]
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties[1]["name"] = "Property C"
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     properties[1]["unit"] = None
#     catalogue_category = response.json()
#     assert catalogue_category == {
#         **catalogue_category_post,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
#         "id": ANY,
#         "code": "category-a",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_modify_property_to_have_allowed_values_list(test_client):
#     """
#     Test modifying properties to have a list of allowed values
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_value_to_id["mm"], "mandatory": False},
#         {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
#     ]
#     catalogue_category_post = {
#         **CATALOGUE_CATEGORY_POST_B,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties[0]["allowed_values"] = {"type": "list", "values": [2, 4, 6]}
#     properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green"]}
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 200
#     catalogue_category = response.json()
#     assert catalogue_category == {
#         **catalogue_category_post,
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#         "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
#         "id": ANY,
#         "code": "category-b",
#         "parent_id": None,
#     }


# def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_number(
#     test_client,
# ):
#     """
#     Test modifying properties to have a number property containing an allowed_values list with an
#     invalid number
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_value_to_id["mm"], "mandatory": False},
#         {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
#     ]
#     catalogue_category_post = {
#         **CATALOGUE_CATEGORY_POST_B,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties[0]["allowed_values"] = {"type": "list", "values": [2, "4", 6]}
#     properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green"]}
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert (
#         response.json()["detail"][0]["msg"]
#         == "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself"
#     )


# def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_string(
#     test_client,
# ):
#     """
#     Test modifying properties to have a string property containing an allowed_values list with an
#     invalid string
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_value_to_id["mm"], "mandatory": False},
#         {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
#     ]
#     catalogue_category_post = {
#         **CATALOGUE_CATEGORY_POST_B,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties[0]["allowed_values"] = {"type": "list", "values": [2, 4, 6]}
#     properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green", 6]}
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert (
#         response.json()["detail"][0]["msg"]
#         == "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself"
#     )


# def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_duplicate_number(
#     test_client,
# ):
#     """
#     Test modifying properties to have a number property containing an allowed_values list with a
#     duplicate number value
#     """
#     properties = [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
#     ]
#     catalogue_category_post = {
#         **CATALOGUE_CATEGORY_POST_B,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties[0]["allowed_values"] = {"type": "list", "values": [42, 10.2, 12, 42]}
#     properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green"]}
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert (
#         response.json()["detail"][0]["msg"]
#         == "Value error, allowed_values of type 'list' contains a duplicate value: 42"
#     )


# def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_duplicate_string(
#     test_client,
# ):
#     """
#     Test modifying properties to have a string property containing an allowed_values list with a
#     duplicate string value
#     """
#     properties = [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
#     ]
#     catalogue_category_post = {
#         **CATALOGUE_CATEGORY_POST_B,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     properties[0]["allowed_values"] = {"type": "list", "values": [2, 4, 6]}
#     properties[1]["allowed_values"] = {
#         "type": "list",
#         "values": ["value1", "value2", "value3", "value2"],
#     }
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert (
#         response.json()["detail"][0]["msg"]
#         == "Value error, allowed_values of type 'list' contains a duplicate value: value2"
#     )


# def test_partial_update_catalogue_category_change_properties_has_child_catalogue_items(test_client):
#     """
#     Test changing the properties when a catalogue category has child catalogue items.
#     """
#     # pylint: disable=duplicate-code

#     units, _ = _post_units(test_client)
#     response = test_client.post(
#         "/v1/catalogue-categories",
#         json={
#             **CATALOGUE_CATEGORY_POST_C,
#             "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_C["properties"], units),
#         },
#     )
#     catalogue_category = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     # pylint: enable=duplicate-code
#     test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_category_patch = {"properties": [{"name": "Property B", "type": "string", "mandatory": False}]}
#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category['id']}", json=catalogue_category_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


# def test_partial_update_catalogue_category_invalid_unit_id(test_client):
#     """
#     Test modifying a property when there is an invalid unit ID.
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {
#             "name": "Property A",
#             "type": "number",
#             "unit": "mm",
#             "unit_id": unit_value_to_id["mm"],
#             "mandatory": False,
#             "allowed_values": None,
#         },
#         {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
#     ]
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     # invalid unit data
#     unit_cm = {
#         "id": "invalid",
#         "value": "cm",
#         "code": "cm",
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#     }
#     properties[0]["unit_id"] = unit_cm["id"]
#     properties[0]["unit"] = unit_cm["value"]
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified unit does not exist"


# def test_partial_update_catalogue_category_non_existent_unit_id(test_client):
#     """
#     Test modifying a property when there is an non existent unit ID.
#     """

#     _, unit_value_to_id = _post_units(test_client)

#     properties = [
#         {
#             "name": "Property A",
#             "type": "number",
#             "unit": "mm",
#             "unit_id": unit_value_to_id["mm"],
#             "mandatory": False,
#             "allowed_values": None,
#         },
#         {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
#     ]
#     catalogue_category_post = {
#         "name": "Category A",
#         "is_leaf": True,
#         "properties": properties,
#     }
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

#     # invalid unit data
#     unit_cm = {
#         "id": str(ObjectId()),
#         "value": "cm",
#         "code": "cm",
#         **CREATED_MODIFIED_VALUES_EXPECTED,
#     }
#     properties[0]["unit_id"] = unit_cm["id"]
#     properties[0]["unit"] = unit_cm["value"]
#     catalogue_category_patch = {"properties": properties}
#     response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified unit does not exist"


# def test_partial_update_catalogue_category_invalid_id(test_client):
#     """
#     Test updating a catalogue category with an invalid ID.
#     """
#     catalogue_category_patch = {"name": "Category A", "is_leaf": False}

#     response = test_client.patch("/v1/catalogue-categories/invalid", json=catalogue_category_patch)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Catalogue category not found"


# def test_partial_update_catalogue_category_non_existent_id(test_client):
#     """
#     Test updating a catalogue category with a non-existent ID.
#     """
#     catalogue_category_patch = {"name": "Category A", "is_leaf": False}

#     response = test_client.patch(f"/v1/catalogue-categories/{str(ObjectId())}", json=catalogue_category_patch)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Catalogue category not found"


# def test_partial_update_catalogue_items_to_have_duplicate_property_names(test_client):
#     """
#     Test updating a catalogue category to have duplicate property names
#     """

#     units, unit_value_to_id = _post_units(test_client)
#     response = test_client.post(
#         "/v1/catalogue-categories",
#         json={
#             **CATALOGUE_CATEGORY_POST_C,
#             "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_C["properties"], units),
#         },
#     )
#     catalogue_category_id = response.json()["id"]

#     catalogue_category_patch = {
#         "properties": [
#             {"name": "Duplicate", "type": "number", "unit_id": unit_value_to_id["mm"], "mandatory": False},
#             {"name": "Duplicate", "type": "boolean", "unit": None, "mandatory": True},
#         ]
#     }

#     response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == (
#         f"Duplicate property name: {catalogue_category_patch['properties'][0]['name']}"
#     )
