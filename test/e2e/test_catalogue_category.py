"""
End-to-End tests for the catalogue category router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code
# pylint: disable=too-many-public-methods

from test.e2e.conftest import E2ETestHelpers
from test.e2e.test_unit import CreateDSL as UnitCreateDSL
from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_GET_DATA_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
    UNIT_POST_DATA_MM,
)
from typing import Optional

import pytest
from bson import ObjectId
from httpx import Response

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH


class CreateDSL(UnitCreateDSL):
    """Base class for create tests."""

    _post_response_catalogue_category: Response

    def post_catalogue_category(self, catalogue_category_data: dict) -> Optional[str]:
        """
        Posts a catalogue category with the given data and returns the ID of the created catalogue category if
        successful.

        :param catalogue_category_data: Dictionary containing the basic catalogue category data as would be required
                                        for a `CatalogueCategoryPostSchema` but with any `unit_id`'s replaced by the
                                        `unit` value in its properties as the IDs will be added automatically.
        :return: ID of the created catalogue category (or `None` if not successful).
        """

        # Replace any unit values with unit IDs
        catalogue_category_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            catalogue_category_data, self.unit_value_id_dict
        )

        self._post_response_catalogue_category = self.test_client.post(
            "/v1/catalogue-categories", json=catalogue_category_data
        )

        return (
            self._post_response_catalogue_category.json()["id"]
            if self._post_response_catalogue_category.status_code == 201
            else None
        )

    def post_leaf_catalogue_category_with_allowed_values(
        self, property_type: str, allowed_values_post_data: dict
    ) -> None:
        """
        Utility method that posts a leaf catalogue category with a property named 'property' of a given type with
        a given set of allowed values.

        :param property_type: Type of the property to post.
        :param allowed_values_post_data: Dictionary containing the allowed values data as would be required for an
                                         `AllowedValuesSchema`.
        """

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

    def check_post_catalogue_category_success(self, expected_catalogue_category_get_data: dict) -> None:
        """
        Checks that a prior call to `post_catalogue_category` gave a successful response with the expected data
        returned.

        :param expected_catalogue_category_get_data: Dictionary containing the expected system data returned as would
                                                     be required for a `CatalogueCategorySchema`. Does not need
                                                     `unit_id`'s as they will be added automatically to check they are
                                                     as expected.
        """

        assert self._post_response_catalogue_category.status_code == 201
        assert self._post_response_catalogue_category.json() == E2ETestHelpers.add_unit_ids_to_properties(
            expected_catalogue_category_get_data, self.unit_value_id_dict
        )

    def check_post_catalogue_category_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `post_catalogue_category` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._post_response_catalogue_category.status_code == status_code
        assert self._post_response_catalogue_category.json()["detail"] == detail

    def check_post_catalogue_category_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_catalogue_category` gave a failed response with the expected code and
        pydantic validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._post_response_catalogue_category.status_code == status_code
        assert self._post_response_catalogue_category.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category."""

    def test_create_non_leaf_with_only_required_values_provided(self):
        """Test creating a non-leaf catalogue category with only required values provided."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)

    def test_create_non_leaf_with_properties(self):
        """Test creating a non-leaf catalogue category with properties provided (ensures they are ignored)."""

        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY],
            }
        )
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)

    def test_create_with_valid_parent_id(self):
        """Test creating a catalogue category with a valid parent ID."""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.check_post_catalogue_category_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )

    def test_create_with_leaf_parent(self):
        """Test creating a catalogue category with a leaf parent."""

        parent_id = self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "is_leaf": True}
        )
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.check_post_catalogue_category_failed_with_detail(
            409, "Adding a catalogue category to a leaf parent catalogue category is not allowed"
        )

    def test_create_with_non_existent_parent_id(self):
        """Test creating a catalogue category with a non-existent parent ID."""

        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": str(ObjectId())}
        )
        self.check_post_catalogue_category_failed_with_detail(
            422, "The specified parent catalogue category does not exist"
        )

    def test_create_with_invalid_parent_id(self):
        """Test creating a catalogue category with an invalid parent ID."""

        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": "invalid-id"}
        )
        self.check_post_catalogue_category_failed_with_detail(
            422, "The specified parent catalogue category does not exist"
        )

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a catalogue category with the same name as another within the parent catalogue category."""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        # 2nd post should be the duplicate
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )
        self.check_post_catalogue_category_failed_with_detail(
            409, "A catalogue category with the same name already exists within the parent catalogue category"
        )

    def test_create_leaf_with_only_required_values_provided(self):
        """Test creating a leaf catalogue category with only required values provided."""

        self.post_catalogue_category({**CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY, "is_leaf": True})
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_LEAF_REQUIRED_VALUES_ONLY)

    def test_create_leaf_with_properties(self):
        """Test creating a leaf catalogue category with some properties provided."""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)
        self.check_post_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)

    def test_create_leaf_with_properties_with_non_existent_unit_id(self):
        """Test creating a leaf catalogue category with a property with a non-existent unit ID provided."""

        self.add_unit_value_and_id("mm", str(ObjectId()))
        self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)
        self.check_post_catalogue_category_failed_with_detail(422, "The specified unit does not exist")

    def test_create_leaf_with_properties_with_invalid_unit_id(self):
        """Test creating a leaf catalogue category with a property with an invalid unit ID provided."""

        self.add_unit_value_and_id("mm", "invalid-id")
        self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)
        self.check_post_catalogue_category_failed_with_detail(422, "The specified unit does not exist")

    def test_create_leaf_with_duplicate_properties(self):
        """Test creating a leaf catalogue category with duplicate properties provided."""

        property_data = CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY

        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM, "properties": [property_data, property_data]}
        )
        self.check_post_catalogue_category_failed_with_detail(
            422, f"Duplicate property name: {CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY["name"]}"
        )

    def test_create_leaf_with_property_with_invalid_type(self):
        """Test creating a leaf catalogue category with a property with an invalid type provided."""

        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
                "properties": [{**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "type": "invalid-type"}],
            }
        )
        self.check_post_catalogue_category_failed_with_validation_message(
            422, "Input should be 'string', 'number' or 'boolean'"
        )

    def test_create_leaf_with_boolean_property_with_unit(self):
        """Test creating a leaf catalogue category with a boolean property with a unit."""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
                "properties": [{**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "unit": "mm"}],
            }
        )
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, Unit not allowed for boolean property "
            f"'{CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']}'",
        )

    def test_create_leaf_property_with_invalid_allowed_values_type(self):
        """Test creating a leaf catalogue category with a property with an invalid allowed values type."""

        self.post_leaf_catalogue_category_with_allowed_values("string", {"type": "invalid-type"})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Input tag 'invalid-type' found using 'type' does not match any of the expected tags: 'list'",
        )

    def test_create_leaf_property_with_empty_allowed_values_list(self):
        """Test creating a leaf catalogue category with a property with an allowed values list that is empty."""

        self.post_leaf_catalogue_category_with_allowed_values("string", {"type": "list", "values": []})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "List should have at least 1 item after validation, not 0",
        )

    def test_create_leaf_with_string_property_with_allowed_values_list_invalid_value(self):
        """Test creating a leaf catalogue category with a string property with an allowed values list with an invalid
        number value in it."""

        self.post_leaf_catalogue_category_with_allowed_values("string", {"type": "list", "values": ["1", "2", 3, "4"]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_create_leaf_with_string_property_with_allowed_values_list_duplicate_value(self):
        """Test creating a leaf catalogue category with a string property with an allowed values list with a duplicate
        string value in it."""

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
        number value in it."""

        self.post_leaf_catalogue_category_with_allowed_values("number", {"type": "list", "values": [1, 2, "3", 4]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_create_leaf_with_number_property_with_allowed_values_list_duplicate_value(self):
        """Test creating a leaf catalogue category with a number property with an allowed values list with a duplicate
        number value in it."""

        self.post_leaf_catalogue_category_with_allowed_values("number", {"type": "list", "values": [1, 2, 1, 3]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: 1",
        )

    def test_create_leaf_with_boolean_property_with_allowed_values_list(self):
        """Test creating a leaf catalogue category with a boolean property with an allowed values list."""

        self.post_leaf_catalogue_category_with_allowed_values("boolean", {"type": "list", "values": [True, False]})
        self.check_post_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values not allowed for a boolean property 'property'",
        )


class GetDSL(CreateDSL):
    """Base class for get tests."""

    _get_response_catalogue_category: Response

    def get_catalogue_category(self, catalogue_category_id: str) -> None:
        """
        Gets a catalogue category with the given ID.

        :param catalogue_category_id: ID of the catalogue category to be obtained.
        """

        self._get_response_catalogue_category = self.test_client.get(
            f"/v1/catalogue-categories/{catalogue_category_id}"
        )

    def check_get_catalogue_category_success(self, expected_catalogue_category_get_data: dict) -> None:
        """
        Checks that a prior call to `get_catalogue_category` gave a successful response with the expected data returned.

        :param expected_catalogue_category_get_data: Dictionary containing the expected catalogue category data returned
                                                     as would be required for a `CatalogueCategorySchema`. Does not need
                                                     unit IDs as they will be added automatically to check they are as
                                                     expected.
        """

        assert self._get_response_catalogue_category.status_code == 200
        assert self._get_response_catalogue_category.json() == E2ETestHelpers.add_unit_ids_to_properties(
            expected_catalogue_category_get_data, self.unit_value_id_dict
        )

    def check_get_catalogue_category_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `get_catalogue_category` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response_catalogue_category.status_code == status_code
        assert self._get_response_catalogue_category.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a catalogue category."""

    def test_get(self):
        """Test getting a catalogue category."""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)
        self.get_catalogue_category(catalogue_category_id)
        self.check_get_catalogue_category_success(CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)

    def test_get_with_non_existent_id(self):
        """Test getting a catalogue category with a non-existent ID."""

        self.get_catalogue_category(str(ObjectId()))
        self.check_get_catalogue_category_failed_with_detail(404, "Catalogue category not found")

    def test_get_with_invalid_id(self):
        """Test getting a catalogue category with an invalid ID."""

        self.get_catalogue_category("invalid-id")
        self.check_get_catalogue_category_failed_with_detail(404, "Catalogue category not found")


class GetBreadcrumbsDSL(GetDSL):
    """Base class for breadcrumbs tests."""

    _get_response_catalogue_category: Response

    _posted_catalogue_categories_get_data: list[dict]

    @pytest.fixture(autouse=True)
    def setup_catalogue_category_get_breadcrumbs_dsl(self):
        """Setup fixtures"""

        self._posted_catalogue_categories_get_data = []

    def post_nested_catalogue_categories(self, number: int) -> list[Optional[str]]:
        """Posts the given number of nested catalogue categories where each successive one has the previous as its
        parent.

        :param number: Number of catalogue categories to create.
        :return: List of IDs of the created catalogue categories.
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
            self._posted_catalogue_categories_get_data.append(self._post_response_catalogue_category.json())
            parent_id = catalogue_category_id

        return [catalogue_category["id"] for catalogue_category in self._posted_catalogue_categories_get_data]

    def get_catalogue_category_breadcrumbs(self, catalogue_category_id: str) -> None:
        """
        Gets a catalogue category's breadcrumbs with the given ID.

        :param catalogue_category_id: ID of the catalogue category to obtain the breadcrumbs of.
        """

        self._get_response_catalogue_category = self.test_client.get(
            f"/v1/catalogue-categories/{catalogue_category_id}/breadcrumbs"
        )

    def get_last_catalogue_category_breadcrumbs(self) -> None:
        """Gets the last catalogue category posted's breadcrumbs."""

        self.get_catalogue_category_breadcrumbs(self._post_response_catalogue_category.json()["id"])

    def check_get_catalogue_categories_breadcrumbs_success(
        self, expected_trail_length: int, expected_full_trail: bool
    ) -> None:
        """
        Checks that a prior call to 'get_catalogue_category_breadcrumbs' gave a successful response with the
        expected data returned.

        :param expected_trail_length: Expected length of the breadcrumbs trail.
        :param expected_full_trail: Whether the expected trail is a full trail or not.
        """

        assert self._get_response_catalogue_category.status_code == 200
        assert self._get_response_catalogue_category.json() == {
            "trail": [
                [catalogue_category["id"], catalogue_category["name"]]
                # When the expected trail length is < the number of systems posted, only use the last
                for catalogue_category in self._posted_catalogue_categories_get_data[
                    (len(self._posted_catalogue_categories_get_data) - expected_trail_length) :
                ]
            ],
            "full_trail": expected_full_trail,
        }

    def check_get_catalogue_categories_breadcrumbs_failed_with_detail(self, status_code: int, detail: str) -> None:
        """Checks that a prior call to `get_catalogue_category_breadcrumbs` gave a failed response with the expected
        code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response_catalogue_category.status_code == status_code
        assert self._get_response_catalogue_category.json()["detail"] == detail


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting a system's breadcrumbs."""

    def test_get_breadcrumbs_when_no_parent(self):
        """Test getting a system's breadcrumbs when the system has no parent."""

        self.post_nested_catalogue_categories(1)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(expected_trail_length=1, expected_full_trail=True)

    def test_get_breadcrumbs_when_trail_length_less_than_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail should be less than the maximum trail
        length."""

        self.post_nested_catalogue_categories(BREADCRUMBS_TRAIL_MAX_LENGTH - 1)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH - 1, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail should be equal to the maximum trail
        length."""

        self.post_nested_catalogue_categories(BREADCRUMBS_TRAIL_MAX_LENGTH)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_greater_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail exceeds the maximum trail length."""

        self.post_nested_catalogue_categories(BREADCRUMBS_TRAIL_MAX_LENGTH + 1)
        self.get_last_catalogue_category_breadcrumbs()
        self.check_get_catalogue_categories_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=False
        )

    def test_get_breadcrumbs_with_non_existent_id(self):
        """Test getting a system's breadcrumbs when given a non-existent system ID."""

        self.get_catalogue_category_breadcrumbs(str(ObjectId()))
        self.check_get_catalogue_categories_breadcrumbs_failed_with_detail(404, "Catalogue category not found")

    def test_get_breadcrumbs_with_invalid_id(self):
        """Test getting a system's breadcrumbs when given an invalid system ID."""

        self.get_catalogue_category_breadcrumbs("invalid_id")
        self.check_get_catalogue_categories_breadcrumbs_failed_with_detail(404, "Catalogue category not found")


class ListDSL(GetBreadcrumbsDSL):
    """Base class for list tests."""

    def get_catalogue_categories(self, filters: dict) -> None:
        """
        Gets a list of catalogue categories with the given filters.

        :param filters: Filters to use in the request.
        """

        self._get_response_catalogue_category = self.test_client.get("/v1/catalogue-categories", params=filters)

    def post_test_catalogue_category_with_child(self) -> list[dict]:
        """
        Posts a catalogue category with a single child and returns their expected responses when returned by the
        list endpoint.

        :return: List of dictionaries containing the expected catalogue category data returned from a get endpoint in
                 the form of a `CatalogueCategorySchema`.
        """

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id}
        )

        return [
            CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": parent_id},
        ]

    def check_get_catalogue_categories_success(self, expected_catalogue_categories_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_catalogue_categories` gave a successful response with the expected data
        returned.

        :param expected_catalogue_categories_get_data: List of dictionaries containing the expected catalogue category
                                                    data returned as would be required for `CatalogueCategorySchema`'s.
        """

        assert self._get_response_catalogue_category.status_code == 200
        assert self._get_response_catalogue_category.json() == expected_catalogue_categories_get_data


class TestList(ListDSL):
    """Tests for getting a list of catalogue categories."""

    def test_list_with_no_filters(self):
        """
        Test getting a list of all catalogue categories with no filters provided.

        Posts a catalogue category with a child and expects both to be returned.
        """

        catalogue_categories = self.post_test_catalogue_category_with_child()
        self.get_catalogue_categories(filters={})
        self.check_get_catalogue_categories_success(catalogue_categories)

    def test_list_with_parent_id_filter(self):
        """
        Test getting a list of all catalogue categories with a `parent_id` filter provided.

        Posts a catalogue category with a child and then filter using the `parent_id` expecting only the second
        catalogue category to be returned.
        """

        catalogue_categories = self.post_test_catalogue_category_with_child()
        self.get_catalogue_categories(filters={"parent_id": catalogue_categories[1]["parent_id"]})
        self.check_get_catalogue_categories_success([catalogue_categories[1]])

    def test_list_with_null_parent_id_filter(self):
        """
        Test getting a list of all catalogue categories with a `parent_id` filter of "null" provided.

        Posts a catalogue category with a child and then filter using a `parent_id` of "null" expecting only
        the first parent catalogue category to be returned.
        """

        catalogue_categories = self.post_test_catalogue_category_with_child()
        self.get_catalogue_categories(filters={"parent_id": "null"})
        self.check_get_catalogue_categories_success([catalogue_categories[0]])

    def test_list_with_parent_id_filter_with_no_matching_results(self):
        """Test getting a list of all catalogue categories with a `parent_id` filter that returns no results."""

        self.get_catalogue_categories(filters={"parent_id": str(ObjectId())})
        self.check_get_catalogue_categories_success([])

    def test_list_with_invalid_parent_id_filter(self):
        """Test getting a list of all categories with an invalid `parent_id` filter returns no results."""

        self.get_catalogue_categories(filters={"parent_id": "invalid-id"})
        self.check_get_catalogue_categories_success([])


# pylint:disable=fixme
# TODO: Look into abstracting this? It's the same as systems except for the names
class UpdateDSL(ListDSL):
    """Base class for update tests."""

    _patch_response_catalogue_category: Response

    def patch_catalogue_category(self, catalogue_category_id: str, catalogue_category_update_data: dict) -> None:
        """
        Updates a catalogue category with the given ID.

        :param catalogue_category_id: ID of the catalogue category to patch.
        :param catalogue_category_update_data: Dictionary containing the basic patch data as would be required for a
                                               `CatalogueCategoryPatchSchema` but with any `unit_id`'s replaced by the
                                               `unit` value in its properties as the ids will be added automatically.
        """

        # Replace any unit values with unit ids
        catalogue_category_update_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            catalogue_category_update_data, self.unit_value_id_dict
        )

        self._patch_response_catalogue_category = self.test_client.patch(
            f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_update_data
        )

    def post_child_catalogue_category(self) -> None:
        """Utility method that posts a child catalogue category for the last catalogue category posted."""

        # pylint:disable=fixme
        # TODO: Could change post_catalogue_category logic and use post_catalogue_category - right now a test like
        # test_partial_update_non_leaf_all_valid_values_when_has_child_catalogue_category wont work with that as it
        # will assert the created times based on the last _post_response_catalogue_category which will be the child so
        # have to bypass here
        # currently - may not be necessary if have custom test client instead & should be clearer after items
        self.test_client.post(
            "/v1/catalogue-categories",
            json={
                **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
                "parent_id": self._post_response_catalogue_category.json()["id"],
            },
        )

    def post_child_catalogue_item(self) -> None:
        """Utility method that posts a child catalogue item for the last catalogue category posted."""

        # Create a child catalogue item
        response = self.test_client.post(
            "/v1/manufacturers",
            json=MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
        )
        manufacturer_id = response.json()["id"]

        catalogue_item_post = {
            **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            "catalogue_category_id": self._post_response_catalogue_category.json()["id"],
            "manufacturer_id": manufacturer_id,
        }
        self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    def patch_properties_with_property_with_allowed_values(
        self, property_type: str, allowed_values_post_data: dict
    ) -> None:
        """
        Utility method that patches the last posted catalogue category to have a single property named 'property' of
        a given type with a given set of allowed values.

        :param property_type: Type of the property to patch.
        :param allowed_values_post_data: Dictionary containing the allowed values data as would be required for an
                                         `AllowedValuesSchema`.
        """

        self.patch_catalogue_category(
            self._post_response_catalogue_category.json()["id"],
            {
                "properties": [
                    {
                        "name": "property",
                        "type": property_type,
                        "mandatory": False,
                        "allowed_values": allowed_values_post_data,
                    }
                ],
            },
        )

    def check_patch_catalogue_category_response_success(self, expected_catalogue_category_get_data: dict) -> None:
        """
        Checks that a prior call to `patch_catalogue_category` gave a successful response with the expected data
        returned.

        :param expected_catalogue_category_get_data: Dictionary containing the expected catalogue category data returned
                                            as would be required for a `CatalogueCategorySchema`. Does not need unit IDs
                                            as they will be added automatically to check they are as expected.
        """

        assert self._patch_response_catalogue_category.status_code == 200
        assert self._patch_response_catalogue_category.json() == E2ETestHelpers.add_unit_ids_to_properties(
            expected_catalogue_category_get_data, self.unit_value_id_dict
        )

        E2ETestHelpers.check_created_and_modified_times_updated_correctly(
            self._post_response_catalogue_category, self._patch_response_catalogue_category
        )

    def check_patch_catalogue_category_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `patch_catalogue_category` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._patch_response_catalogue_category.status_code == status_code
        assert self._patch_response_catalogue_category.json()["detail"] == detail

    def check_patch_catalogue_category_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `patch_catalogue_category` gave a failed response with the expected code and
        pydantic validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._patch_response_catalogue_category.status_code == status_code
        assert self._patch_response_catalogue_category.json()["detail"][0]["msg"] == message


class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue category."""

    def test_partial_update_name(self):
        """Test updating every field of a system."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.patch_catalogue_category(catalogue_category_id, {"name": "New Name"})
        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "name": "New Name", "code": "new-name"}
        )

    def test_partial_update_parent_id(self):
        """Test updating the `parent_id` of a catalogue category."""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(
            CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B
        )

        self.patch_catalogue_category(catalogue_category_id, {"parent_id": parent_id})
        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B, "parent_id": parent_id}
        )

    def test_partial_update_parent_id_to_one_with_a_duplicate_name(self):
        """Test updating the `parent_id` of a catalogue category so that its name conflicts with one already in that
        other catalogue category."""

        # Catalogue category with child
        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        self.post_catalogue_category(
            {
                **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                "name": "Conflicting Name",
                "parent_id": parent_id,
            }
        )

        catalogue_category_id = self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "name": "Conflicting Name"}
        )

        self.patch_catalogue_category(catalogue_category_id, {"parent_id": parent_id})
        self.check_patch_catalogue_category_failed_with_detail(
            409, "A catalogue category with the same name already exists within the parent catalogue category"
        )

    def test_partial_update_parent_id_to_child_of_self(self):
        """Test updating the `parent_id` of a catalogue category to one of its own children."""

        catalogue_category_ids = self.post_nested_catalogue_categories(2)
        self.patch_catalogue_category(catalogue_category_ids[0], {"parent_id": catalogue_category_ids[1]})
        self.check_patch_catalogue_category_failed_with_detail(
            422, "Cannot move a catalogue category to one of its own children"
        )

    def test_partial_update_parent_id_to_leaf(self):
        """Test updating the `parent_id` of a catalogue category to the ID of a leaf catalogue category."""

        parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY)

        self.patch_catalogue_category(catalogue_category_id, {"parent_id": parent_id})
        self.check_patch_catalogue_category_failed_with_detail(
            409, "Adding a catalogue category to a leaf parent catalogue category is not allowed"
        )

    def test_partial_update_parent_id_to_non_existent(self):
        """Test updating the `parent_id` of a catalogue category to a non-existent catalogue category."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.patch_catalogue_category(catalogue_category_id, {"parent_id": str(ObjectId())})
        self.check_patch_catalogue_category_failed_with_detail(
            422, "The specified parent catalogue category does not exist"
        )

    def test_partial_update_parent_id_to_invalid_id(self):
        """Test updating the `parent_id` of a catalogue category to an invalid ID."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.patch_catalogue_category(catalogue_category_id, {"parent_id": "invalid-id"})
        self.check_patch_catalogue_category_failed_with_detail(
            422, "The specified parent catalogue category does not exist"
        )

    def test_partial_update_name_to_duplicate(self):
        """Test updating the name of a catalogue category to conflict with a pre-existing one."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(
            CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B
        )
        self.patch_catalogue_category(
            catalogue_category_id, {"name": CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A["name"]}
        )
        self.check_patch_catalogue_category_failed_with_detail(
            409, "A catalogue category with the same name already exists within the parent catalogue category"
        )

    def test_partial_update_name_capitalisation(self):
        """Test updating the capitalisation of the name of a catalogue category (to ensure it the check doesn't
        confuse with duplicates)."""

        catalogue_category_id = self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "name": "Test catalogue category"}
        )
        self.patch_catalogue_category(catalogue_category_id, {"name": "Test Catalogue Category"})
        self.check_patch_catalogue_category_response_success(
            {
                **CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
                "name": "Test Catalogue Category",
                "code": "test-catalogue-category",
            }
        )

    def test_partial_update_non_leaf_all_valid_values_when_no_children(self):
        """Test updating the all values of a non leaf catalogue category that can be modified when it has no
        children."""

        self.post_unit(UNIT_POST_DATA_MM)
        new_parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)

        self.patch_catalogue_category(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM, "parent_id": new_parent_id},
        )

        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM, "parent_id": new_parent_id}
        )

    def test_partial_update_non_leaf_to_leaf_without_properties(self):
        """Test updating a non-leaf catalogue category to a leaf catalogue category without any properties provided."""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)

        self.patch_catalogue_category(catalogue_category_id, {"is_leaf": True})

        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "is_leaf": True}
        )

    def test_partial_update_non_leaf_all_valid_values_when_has_child_catalogue_category(self):
        """Test updating the all values of a non leaf catalogue category that can be modified when it has a child
        catalogue category."""

        new_parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_child_catalogue_category()

        update_data = {"name": "New Name", "parent_id": new_parent_id}

        self.patch_catalogue_category(catalogue_category_id, update_data)

        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, **update_data, "code": "new-name"}
        )

    def test_partial_update_non_leaf_to_leaf_when_has_child_catalogue_category(self):
        """Test updating a non-leaf catalogue category to a leaf when it has a child catalogue category."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_child_catalogue_category()

        self.patch_catalogue_category(catalogue_category_id, {"is_leaf": True})

        self.check_patch_catalogue_category_failed_with_detail(
            409, "Catalogue category has child elements and cannot be updated"
        )

    def test_partial_update_leaf_all_valid_values_when_no_children(self):
        """Test updating the all values of a leaf catalogue category that can be modified when it has no children."""

        self.post_unit(UNIT_POST_DATA_MM)
        new_parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)

        # Properties not supplied, here, but they should have been removed in the end as going from leaf to non-leaf
        self.patch_catalogue_category(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": new_parent_id},
        )

        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": new_parent_id}
        )

    def test_partial_update_leaf_all_valid_values_when_has_child_catalogue_item(self):
        """Test updating the all values of a non leaf catalogue category that can be modified when it has a child
        catalogue item."""

        new_parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_child_catalogue_item()

        update_data = {"name": "New Name", "parent_id": new_parent_id}

        self.patch_catalogue_category(catalogue_category_id, update_data)

        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_NO_PROPERTIES, **update_data, "code": "new-name"}
        )

    def test_partial_update_leaf_to_non_leaf_when_has_child_catalogue_item(self):
        """Test updating a leaf catalogue category to a non-leaf when it has a child catalogue item."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_child_catalogue_item()

        self.patch_catalogue_category(catalogue_category_id, {"is_leaf": False})

        self.check_patch_catalogue_category_failed_with_detail(
            409, "Catalogue category has child elements and cannot be updated"
        )

    def test_partial_update_leaf_properties_when_has_child_catalogue_item(self):
        """Test updating a leaf catalogue category's properties when it has a child catalogue item."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_child_catalogue_item()

        self.patch_catalogue_category(catalogue_category_id, {"properties": []})

        self.check_patch_catalogue_category_failed_with_detail(
            409, "Catalogue category has child elements and cannot be updated"
        )

    def test_partial_update_leaf_to_non_leaf_with_properties(self):
        """Test updating a leaf catalogue category to a non-leaf catalogue category with properties provided (ensures
        they are ignored)."""

        self.post_unit(UNIT_POST_DATA_MM)
        new_parent_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)

        self.patch_catalogue_category(
            catalogue_category_id,
            {
                **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                "parent_id": new_parent_id,
                "properties": CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM["properties"],
            },
        )

        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": new_parent_id}
        )

    def test_partial_update_is_leaf_no_children(self):
        """Test updating the value of is_leaf for a catalogue category without any children."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.patch_catalogue_category(catalogue_category_id, {"is_leaf": True})
        self.check_patch_catalogue_category_response_success(
            {**CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "is_leaf": True}
        )

    def test_partial_update_is_leaf_with_child_catalogue_category(self):
        """Test updating the value of is_leaf for a catalogue category with a child catalogue category."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY, "parent_id": catalogue_category_id}
        )

        self.patch_catalogue_category(catalogue_category_id, {"is_leaf": True})
        self.check_patch_catalogue_category_failed_with_detail(
            409, "Catalogue category has child elements and cannot be updated"
        )

    def test_partial_update_leaf_properties(self):
        """Test updating a leaf catalogue category's properties."""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_catalogue_category(
            catalogue_category_id,
            {"properties": CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM["properties"]},
        )

        self.check_patch_catalogue_category_response_success(
            {
                **CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
                "properties": CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM["properties"],
            }
        )

    def test_partial_update_leaf_with_properties_with_non_existent_unit_id(self):
        """Test updating a leaf catalogue category's properties to have a property with a non-existent unit ID."""

        self.add_unit_value_and_id("mm", str(ObjectId()))
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_catalogue_category(
            catalogue_category_id, {"properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT]}
        )
        self.check_patch_catalogue_category_failed_with_detail(422, "The specified unit does not exist")

    def test_partial_update_leaf_with_properties_with_invalid_unit_id(self):
        """Test updating a leaf catalogue category's properties to have a property with an invalid unit ID provided."""

        self.add_unit_value_and_id("mm", "invalid-id")
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_catalogue_category(
            catalogue_category_id, {"properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT]}
        )
        self.check_patch_catalogue_category_failed_with_detail(422, "The specified unit does not exist")

    def test_partial_update_leaf_with_duplicate_properties(self):
        """Test updating a leaf catalogue category with duplicate properties provided."""

        property_data = CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_catalogue_category(catalogue_category_id, {"properties": [property_data, property_data]})
        self.check_patch_catalogue_category_failed_with_detail(
            422, f"Duplicate property name: {CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY["name"]}"
        )

    def test_partial_update_leaf_with_property_with_invalid_type(self):
        """Test updating a leaf catalogue category's properties to have a property with an invalid type provided."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_catalogue_category(
            catalogue_category_id,
            {
                "properties": [{**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "type": "invalid-type"}],
            },
        )
        self.check_patch_catalogue_category_failed_with_validation_message(
            422, "Input should be 'string', 'number' or 'boolean'"
        )

    def test_partial_update_leaf_with_boolean_property_with_unit(self):
        """Test updating a leaf catalogue category's properties to have a boolean property with a unit."""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_catalogue_category(
            catalogue_category_id,
            {
                "properties": [{**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "unit": "mm"}],
            },
        )
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Value error, Unit not allowed for boolean property "
            f"'{CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']}'",
        )

    def test_partial_update_leaf_property_with_invalid_allowed_values_type(self):
        """Test updating a leaf catalogue category's properties to have a property with an invalid allowed values
        type."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_properties_with_property_with_allowed_values("string", {"type": "invalid-type"})
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Input tag 'invalid-type' found using 'type' does not match any of the expected tags: 'list'",
        )

    def test_partial_update_leaf_property_with_empty_allowed_values_list(self):
        """Test updating a leaf catalogue category's properties to have a property with an allowed values list that is
        empty."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_properties_with_property_with_allowed_values("string", {"type": "list", "values": []})
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "List should have at least 1 item after validation, not 0",
        )

    def test_partial_update_leaf_with_string_property_with_allowed_values_list_invalid_value(self):
        """Test updating a leaf catalogue category's properties to have a string property with an allowed values list
        with an invalid number value in it."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_properties_with_property_with_allowed_values(
            "string", {"type": "list", "values": ["1", "2", 3, "4"]}
        )
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_partial_update_leaf_with_string_property_with_allowed_values_list_duplicate_value(self):
        """Test updating a leaf catalogue category's properties to have a string property with an allowed values list
        with a duplicate string value in it."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        # Capitalisation is different as it shouldn't matter for this test
        self.patch_properties_with_property_with_allowed_values(
            "string", {"type": "list", "values": ["value1", "value2", "Value1", "value3"]}
        )
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: Value1",
        )

    def test_partial_update_leaf_with_number_property_with_allowed_values_list_invalid_value(self):
        """Test updating a leaf catalogue category's properties to have a number property with an allowed values list
        with an invalid number value in it."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_properties_with_property_with_allowed_values("number", {"type": "list", "values": [1, 2, "3", 4]})
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_partial_update_leaf_with_number_property_with_allowed_values_list_duplicate_value(self):
        """Test updating a leaf catalogue category's properties to have a number property with an allowed values list
        with a duplicate number value in it."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_properties_with_property_with_allowed_values("number", {"type": "list", "values": [1, 2, 1, 3]})
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: 1",
        )

    def test_partial_update_leaf_with_boolean_property_with_allowed_values_list(self):
        """Test updating a leaf catalogue category's properties to have a boolean property with an allowed values
        list."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.patch_properties_with_property_with_allowed_values("boolean", {"type": "list", "values": [True, False]})
        self.check_patch_catalogue_category_failed_with_validation_message(
            422,
            "Value error, allowed_values not allowed for a boolean property 'property'",
        )

    def test_partial_update_with_non_existent_id(self):
        """Test updating a non-existent catalogue category."""

        self.patch_catalogue_category(str(ObjectId()), {})
        self.check_patch_catalogue_category_failed_with_detail(404, "Catalogue category not found")

    def test_partial_update_invalid_id(self):
        """Test updating a catalogue category with an invalid ID."""

        self.patch_catalogue_category("invalid-id", {})
        self.check_patch_catalogue_category_failed_with_detail(404, "Catalogue category not found")


class DeleteDSL(UpdateDSL):
    """Base class for delete tests."""

    _delete_response_catalogue_category: Response

    def delete_catalogue_category(self, catalogue_category_id: str) -> None:
        """
        Deletes a catalogue category with the given ID.

        :param catalogue_category_id: ID of the catalogue category to be deleted.
        """

        self._delete_response_catalogue_category = self.test_client.delete(
            f"/v1/catalogue-categories/{catalogue_category_id}"
        )

    def check_delete_catalogue_category_success(self) -> None:
        """Checks that a prior call to `delete_catalogue_category` gave a successful response with the expected data
        returned."""

        assert self._delete_response_catalogue_category.status_code == 204

    def check_delete_catalogue_category_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_catalogue_category` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._delete_response_catalogue_category.status_code == status_code
        assert self._delete_response_catalogue_category.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue category."""

    def test_delete(self):
        """Test deleting a catalogue category."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.delete_catalogue_category(catalogue_category_id)
        self.check_delete_catalogue_category_success()

        self.get_catalogue_category(catalogue_category_id)
        self.check_get_catalogue_category_failed_with_detail(404, "Catalogue category not found")

    def test_delete_with_child_catalogue_category(self):
        """Test deleting a catalogue category with a child catalogue category."""

        catalogue_category_ids = self.post_nested_catalogue_categories(2)
        self.delete_catalogue_category(catalogue_category_ids[0])
        self.check_delete_catalogue_category_failed_with_detail(
            409, "Catalogue category has child elements and cannot be deleted"
        )

    def test_delete_with_child_item(self):
        """Test deleting a catalogue category with a child catalogue item."""

        catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY)
        self.post_child_catalogue_item()

        self.delete_catalogue_category(catalogue_category_id)
        self.check_delete_catalogue_category_failed_with_detail(
            409, "Catalogue category has child elements and cannot be deleted"
        )

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent catalogue category."""

        self.delete_catalogue_category(str(ObjectId()))
        self.check_delete_catalogue_category_failed_with_detail(404, "Catalogue category not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a catalogue category with an invalid ID."""

        self.delete_catalogue_category("invalid_id")
        self.check_delete_catalogue_category_failed_with_detail(404, "Catalogue category not found")
