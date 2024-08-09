# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue item router.
"""
from test.conftest import add_ids_to_properties
from test.e2e.conftest import E2ETestHelpers, replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import (
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    CATALOGUE_ITEM_POST_ALLOWED_VALUES,
    CREATED_MODIFIED_VALUES_EXPECTED,
    ITEM_POST_ALLOWED_VALUES,
    ITEM_POST_ALLOWED_VALUES_EXPECTED,
    SYSTEM_POST_A,
    SYSTEM_POST_B,
    USAGE_STATUS_POST_A,
)
from test.e2e.test_catalogue_item import CreateDSL as CatalogueItemCreateDSL
from test.e2e.test_system import CreateDSL as SystemCreateDSL
from test.e2e.test_unit import UNIT_POST_A, UNIT_POST_B
from test.mock_data import (
    CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    ITEM_DATA_ALL_VALUES_NO_PROPERTIES,
    ITEM_DATA_REQUIRED_VALUES_ONLY,
    ITEM_DATA_WITH_ALL_PROPERTIES,
    ITEM_GET_DATA_ALL_VALUES_NO_PROPERTIES,
    ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
    ITEM_GET_DATA_WITH_ALL_PROPERTIES,
    PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1,
    PROPERTY_DATA_STRING_MANDATORY_TEXT,
    SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    USAGE_STATUS_DATA_IN_USE,
)
from typing import Any, Optional
from unittest.mock import ANY

import pytest
from bson import ObjectId
from httpx import Response


class CreateDSL(CatalogueItemCreateDSL, SystemCreateDSL):
    """Base class for create tests."""

    catalogue_item_id: Optional[str]
    system_id: Optional[str]
    usage_status_value_id_dict: dict[str, str]

    _post_response_item: Response

    @pytest.fixture(autouse=True)
    def setup_item_create_dsl(self):
        """Setup fixtures"""

        self.catalogue_item_id = None
        self.system_id = None
        self.usage_status_value_id_dict = {}

    def add_ids_to_expected_item_get_data(self, expected_item_get_data) -> dict:
        """
        Adds required IDs to some expected item get data based on what has already been posted.

        :param expected_item_get_data: Dictionary containing the expected catalogue item data returned as would be
                                       required for an `ItemSchema`. Does not need mandatory IDs (e.g. `system_id`) as
                                       they will be added here.
        """
        # Where there are properties add the property ID, unit ID and unit value
        expected_item_get_data = E2ETestHelpers.add_property_ids_to_properties(
            expected_item_get_data, self.property_name_id_dict
        )
        properties = []
        for prop in expected_item_get_data["properties"]:
            properties.append({**prop, **self._unit_data_lookup_dict[prop["id"]]})
        expected_item_get_data = {**expected_item_get_data, "properties": properties}

        return {
            **expected_item_get_data,
            "catalogue_item_id": self.catalogue_item_id,
            "system_id": self.system_id,
            "usage_status_id": self.usage_status_value_id_dict[expected_item_get_data["usage_status"]],
        }

    def post_catalogue_item(self, catalogue_item_data: dict) -> Optional[str]:
        """
        Posts a catalogue item with the given data and returns the ID of the created catalogue item if successful.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required
                                        for a `CatalogueItemPostSchema` but with mandatory IDs missing and
                                        any `id`'s replaced by the `name` value in its properties as the
                                        IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        self.catalogue_item_id = CatalogueItemCreateDSL.post_catalogue_item(self, catalogue_item_data)
        return self.catalogue_item_id

    def post_system(self, system_post_data: dict) -> Optional[str]:
        """
        Posts a system with the given data and returns the id of the created system if successful.

        :param system_post_data: Dictionary containing the system data as would be required for a
                                 `SystemPostSchema`.
        :return: ID of the created system (or `None` if not successful).
        """

        self.system_id = SystemCreateDSL.post_system(self, system_post_data)
        return self.system_id

    def add_usage_status_value_and_id(self, usage_status_value: str, usage_status_id: str) -> None:
        """
        Stores a usage status value and ID inside the `usage_status_value_id_dict` for tests that need to have a
        non-existent or invalid usage status ID.

        :param usage_status_value: Value of the usage status.
        :param usage_status_id: ID of the usage status.
        """

        self.usage_status_value_id_dict[usage_status_value] = usage_status_id

    def post_usage_status(self, usage_status_post_data: dict) -> None:
        """Posts a usage status with the given data and stores the value and ID in a dictionary for lookup later.

        :param unit_post_data: Dictionary containing the unit data as would be required for a `UnitPostSchema`.
        """

        post_response = self.test_client.post("/v1/usage-statuses", json=usage_status_post_data)
        self.add_usage_status_value_and_id(usage_status_post_data["value"], post_response.json()["id"])

    def post_item(self, item_data: dict) -> Optional[str]:
        """
        Posts an item with the given data and returns the ID of the created item if successful.

        :param item_data: Dictionary containing the basic catalogue item data as would be required for a
                          `ItemPostSchema` but with mandatory IDs missing and any `id`'s replaced by the `name` value
                          in its properties as the IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        # Replace any unit values with unit IDs
        full_item_data = item_data.copy()
        full_item_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            full_item_data, self.unit_value_id_dict
        )
        full_item_data = E2ETestHelpers.replace_property_names_with_ids_in_properties(
            full_item_data, self.property_name_id_dict
        )

        # Insert mandatory IDs if they have been created
        if self.catalogue_item_id:
            full_item_data["catalogue_item_id"] = self.catalogue_item_id
        if self.system_id:
            full_item_data["system_id"] = self.system_id
        full_item_data["usage_status_id"] = self.usage_status_value_id_dict.get(full_item_data["usage_status"])

        self._post_response_item = self.test_client.post("/v1/items", json=full_item_data)

        return self._post_response_item.json()["id"] if self._post_response_item.status_code == 201 else None

    def post_item_and_prerequisites_no_properties(self, item_data: dict) -> Optional[str]:
        """
        Utility method that posts an item with the given data and also its prerequisite system, usage status, catalogue
        item and catalogue category. Uses CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY for the catalogue item and
        USAGE_STATUS_DATA_IN_USE for the usage status.

        :param item_data: Dictionary containing the basic item data as would be required for a `ItemPostSchema` but with
                          mandatory IDs missing and any `id`'s replaced by the `name` value in its properties as the IDs
                          will be added automatically.
        :return: ID of the created item (or `None` if not successful).
        """

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)

        return self.post_item(item_data)

    def post_item_and_prerequisites_with_properties(self, item_data: dict) -> Optional[str]:
        """
        Utility method that posts an item with the given data and also its prerequisite system, usage status, catalogue
        item and catalogue category. Uses CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES for the catalogue item and
        USAGE_STATUS_DATA_IN_USE for the usage status.

        :param item_data: Dictionary containing the basic item data as would be required for a `ItemPostSchema` but with
                          mandatory IDs missing and any `id`'s replaced by the `name` value in its properties as the IDs
                          will be added automatically.
        :return: ID of the created item (or `None` if not successful).
        """

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)

        return self.post_item(item_data)

    def post_item_and_prerequisites_with_given_properties(
        self,
        catalogue_category_properties_data: list[dict],
        catalogue_item_properties_data: list[dict],
        item_properties_data: list[dict],
    ) -> Optional[str]:
        """
        Utility method that posts an item with specific given properties and also its prerequisite system, usage status,
        catalogue item and catalogue category. Uses BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM and
        ITEM_DATA_WITH_ALL_PROPERTIES as a base.

        :param catalogue_category_properties_data: List of dictionaries containing the basic catalogue category property
                        data as would be required for a `CatalogueCategoryPostPropertySchema` but with any `unit_id`'s
                        replaced by the `unit` value in its properties as the IDs will be added automatically.
        :param catalogue_item_properties_data: List of dictionaries containing the basic catalogue item property data as
                        would be required for a `PropertyPostSchema` but with any `id`'s replaced by the `name` value as
                        the IDs will be added automatically.
        :param item_properties_data: List of dictionaries containing the basic item property data as would be required
                                     for a `PropertyPostSchema` but with any `id`'s replaced by the `name` value as the
                                     IDs will be added automatically.
        :return: ID of the created item (or `None` if not successful).
        """

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data, catalogue_item_properties_data
        )
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)

        return self.post_item({**ITEM_DATA_WITH_ALL_PROPERTIES, "properties": item_properties_data})

    def post_item_and_prerequisites_with_allowed_values(
        self,
        property_type: str,
        allowed_values_post_data: dict,
        catalogue_item_property_value: Any,
        item_property_value: Any,
    ) -> Optional[str]:
        """
        Utility method that posts an item with a property named 'property' of a given type with a given set of
        allowed values as well as any prerequisite entities (a catalogue item, system and usage status)

        :param property_type: Type of the property to post.
        :param allowed_values_post_data: Dictionary containing the allowed values data as would be required for an
                                         `AllowedValuesSchema` to be posted with the catalogue category.
        :param catalogue_item_property_value: Value of the property to post for the catalogue item.
        :param item_property_value: Value of the property to post for the item.
        :return: ID of the created item (or `None` if not successful).
        """

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_allowed_values(
            property_type, allowed_values_post_data, catalogue_item_property_value
        )
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)
        return self.post_item(
            {
                **ITEM_DATA_REQUIRED_VALUES_ONLY,
                "properties": [{"name": "property", "value": item_property_value}],
            }
        )

    def check_post_item_success(self, expected_item_get_data: dict) -> None:
        """
        Checks that a prior call to `post_item` gave a successful response with the expected data returned.

        Also merges in any properties that were defined in the catalogue item but are not given in the expected data.

        :param expected_item_get_data: Dictionary containing the expected item data returned as would be required for a
                                       `ItemSchema`. Does not need mandatory IDs (e.g. `system_id`) as they will be to
                                       check they are as expected.
        """

        # Where properties are involved in the catalogue item, need to merge them
        catalogue_item_data = self._post_response_catalogue_item.json()
        expected_item_get_data = expected_item_get_data.copy()
        if expected_item_get_data["properties"]:
            expected_merged_properties = []
            supplied_properties_dict = {
                supplied_property["name"]: supplied_property
                for supplied_property in expected_item_get_data["properties"]
            }
            for prop in catalogue_item_data["properties"]:
                supplied_property = supplied_properties_dict.get(prop["name"])
                expected_merged_properties.append(supplied_property if supplied_property else prop)

            expected_item_get_data["properties"] = expected_merged_properties

        assert self._post_response_item.status_code == 201
        assert self._post_response_item.json() == self.add_ids_to_expected_item_get_data(expected_item_get_data)

    def check_post_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `post_item` gave a failed response with the expected code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._post_response_item.status_code == status_code
        assert self._post_response_item.json()["detail"] == detail

    def check_post_item_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_item` gave a failed response with the expected code and pydantic validation
        error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._post_response_item.status_code == status_code
        assert self._post_response_item.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating an item."""

    def test_create_with_only_required_values_provided(self):
        """Test creating an item with only required values provided."""

        self.post_item_and_prerequisites_no_properties(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_success(ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_with_all_values_except_properties(self):
        """Test creating an item with all values provided except `properties`."""

        self.post_item_and_prerequisites_no_properties(ITEM_DATA_ALL_VALUES_NO_PROPERTIES)

        self.check_post_item_success(ITEM_GET_DATA_ALL_VALUES_NO_PROPERTIES)

    def test_create_with_no_properties_provided(self):
        """Test creating an item when none of the properties present in the catalogue item are defined in the item."""

        self.post_item_and_prerequisites_with_properties(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_success(ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_with_some_properties_provided(self):
        """Test creating an item when only some properties present in the catalogue item are defined in the item."""

        self.post_item_and_prerequisites_with_properties(
            {**ITEM_DATA_WITH_ALL_PROPERTIES, "properties": ITEM_DATA_WITH_ALL_PROPERTIES["properties"][1::]}
        )

        self.check_post_item_success(
            {**ITEM_GET_DATA_WITH_ALL_PROPERTIES, "properties": ITEM_GET_DATA_WITH_ALL_PROPERTIES["properties"][1::]}
        )

    def test_create_with_all_properties_provided(self):
        """Test creating an item when all properties present in the catalogue item are defined in the item."""

        self.post_item_and_prerequisites_with_properties(ITEM_DATA_WITH_ALL_PROPERTIES)

        self.check_post_item_success(ITEM_GET_DATA_WITH_ALL_PROPERTIES)

    def test_create_with_mandatory_property_given_none(self):
        """Test creating an item when a mandatory property is given a value of `None` in the item."""

        self.post_item_and_prerequisites_with_properties(
            {**ITEM_DATA_WITH_ALL_PROPERTIES, "properties": [{**PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE, "value": None}]}
        )

        self.check_post_item_failed_with_detail(
            422,
            f"Mandatory property with ID '{self.property_name_id_dict[PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE['name']]}' "
            "cannot be None.",
        )

    def test_create_with_non_mandatory_property_given_none(self):
        """Test creating an item when a non mandatory property is given a value of `None` in the item."""

        self.post_item_and_prerequisites_with_properties(
            {
                **ITEM_DATA_WITH_ALL_PROPERTIES,
                "properties": [{**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1, "value": None}],
            }
        )

        self.check_post_item_success(
            {
                **ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [{**ITEM_GET_DATA_WITH_ALL_PROPERTIES["properties"][1], "value": None}],
            }
        )

    def test_create_with_string_property_with_invalid_value_type(self):
        """Test creating an item with an invalid value type for a string property."""

        self.post_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY],
            catalogue_item_properties_data=[PROPERTY_DATA_STRING_MANDATORY_TEXT],
            item_properties_data=[{**PROPERTY_DATA_STRING_MANDATORY_TEXT, "value": 42}],
        )

        self.check_post_item_failed_with_detail(
            422,
            "Invalid value type for property with ID "
            f"'{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY['name']]}'. "
            "Expected type: string.",
        )

    def test_create_with_number_property_with_invalid_value_type(self):
        """Test creating an item with an invalid value type for a number property."""

        self.post_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            catalogue_item_properties_data=[PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1],
            item_properties_data=[{**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1, "value": "42"}],
        )

        self.check_post_item_failed_with_detail(
            422,
            "Invalid value type for property with ID '"
            f"{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT['name']]}"
            "'. Expected type: number.",
        )

    def test_create_with_boolean_property_with_invalid_value_type(self):
        """Test creating an item with an invalid value type for a boolean property."""

        self.post_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY],
            catalogue_item_properties_data=[PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE],
            item_properties_data=[{**PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE, "value": 0}],
        )

        self.check_post_item_failed_with_detail(
            422,
            "Invalid value type for property with ID '"
            f"{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']]}"
            "'. Expected type: boolean.",
        )

    def test_create_with_invalid_string_allowed_values_list_value(self):
        """Test creating an item with an invalid value for a string property with an allowed values list."""

        self.post_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, "value1", "value2"
        )
        self.check_post_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected one of value1.",
        )

    def test_create_with_invalid_string_allowed_values_list_type(self):
        """Test creating an item with an invalid type for a string property with an allowed values list."""

        self.post_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, "value1", 42
        )
        self.check_post_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: string.",
        )

    def test_create_with_invalid_number_allowed_values_list_value(self):
        """Test creating a catalogue item with an invalid value for a number property with an allowed values list."""

        self.post_item_and_prerequisites_with_allowed_values("number", {"type": "list", "values": [1]}, 1, 2)
        self.check_post_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. Expected one of 1.",
        )

    def test_create_with_invalid_number_allowed_values_list_type(self):
        """Test creating an item with an invalid type for a number property with an allowed values list."""

        self.post_item_and_prerequisites_with_allowed_values("number", {"type": "list", "values": [1]}, 1, "test")
        self.check_post_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: number.",
        )

    def test_create_with_non_existent_catalogue_item_id(self):
        """Test creating an item with a non-existent catalogue item ID."""

        self.catalogue_item_id = str(ObjectId())
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_failed_with_detail(422, "The specified catalogue item does not exist")

    def test_create_with_invalid_catalogue_item_id(self):
        """Test creating an item with an invalid catalogue item ID."""

        self.catalogue_item_id = "invalid-id"
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_failed_with_detail(422, "The specified catalogue item does not exist")

    def test_create_with_non_existent_system_id(self):
        """Test creating an item with a non-existent system ID."""

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.system_id = str(ObjectId())
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_failed_with_detail(422, "The specified system does not exist")

    def test_create_with_invalid_system_id(self):
        """Test creating an item with an invalid system ID."""

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.system_id = "invalid-id"
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_failed_with_detail(422, "The specified system does not exist")

    def test_create_with_non_existent_usage_status_id(self):
        """Test creating an item with a non-existent usage status ID."""

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.add_usage_status_value_and_id(ITEM_DATA_REQUIRED_VALUES_ONLY["usage_status"], str(ObjectId()))
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_failed_with_detail(422, "The specified usage status does not exist")

    def test_create_with_invalid_usage_status_id(self):
        """Test creating an item with an invalid usage status ID."""

        self.catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_usage_status(USAGE_STATUS_DATA_IN_USE)
        self.add_usage_status_value_and_id(ITEM_DATA_REQUIRED_VALUES_ONLY["usage_status"], "invalid-id")
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_item_failed_with_detail(422, "The specified usage status does not exist")


class GetDSL(CreateDSL):
    """Base class for get tests."""

    _get_response_item: Response

    def get_item(self, item_id: str) -> None:
        """
        Gets an item with the given ID.

        :param item_id: ID of the catalogue item to be obtained.
        """

        self._get_response_item = self.test_client.get(f"/v1/items/{item_id}")

    def check_get_item_success(self, expected_item_get_data: dict) -> None:
        """
        Checks that a prior call to `get_item` gave a successful response with the expected data returned.

        :param expected_item_get_data: Dictionary containing the expected item data returned as would be required for a
                                       `ItemSchema`. Does not need mandatory IDs (e.g. `system_id`) as they will
                                       be added automatically to check they are as expected.
        """

        assert self._get_response_item.status_code == 200
        assert self._get_response_item.json() == self.add_ids_to_expected_item_get_data(expected_item_get_data)

    def check_get_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `get_item` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response_item.status_code == status_code
        assert self._get_response_item.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting an item."""

    def test_get(self):
        """Test getting an item."""

        catalogue_item_id = self.post_item_and_prerequisites_no_properties(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.get_item(catalogue_item_id)
        self.check_get_item_success(ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_get_with_non_existent_id(self):
        """Test getting an item with a non-existent ID."""

        self.get_item(str(ObjectId()))
        self.check_get_item_failed_with_detail(404, "An item with such ID was not found")

    def test_get_with_invalid_id(self):
        """Test getting an item with an invalid ID."""

        self.get_item("invalid-id")
        self.check_get_item_failed_with_detail(404, "An item with such ID was not found")


class ListDSL(GetDSL):
    """Base class for list tests."""

    def get_items(self, filters: dict) -> None:
        """
        Gets a list of items with the given filters.

        :param filters: Filters to use in the request.
        """

        self._get_response_item = self.test_client.get("/v1/items", params=filters)

    def post_test_items(self) -> list[dict]:
        """
        Posts three items. The first two have the same catalogue item but different systems, and the last has a
        different catalogue item but the same system as the second catalogue item.

        :return: List of dictionaries containing the expected item data returned from a get endpoint in
                 the form of an `ItemSchema`. In the form [CATALOGUE_ITEM_A_SYSTEM_A, CATALOGUE_ITEM_A_SYSTEM_B,
                 CATALOGUE_ITEM_B_SYSTEM_B]
        """

        # First item
        self.post_item_and_prerequisites_no_properties(ITEM_DATA_REQUIRED_VALUES_ONLY)
        system_a_id = self.system_id
        catalogue_item_a_id = self.catalogue_item_id

        # Second item
        system_b_id = self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "name": "Another system"})
        self.post_item(ITEM_DATA_ALL_VALUES_NO_PROPERTIES)

        # Third item
        self.post_catalogue_item({**CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY, "name": "Another catalogue item"})
        catalogue_item_b_id = self.catalogue_item_id
        self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

        return [
            {
                **ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": catalogue_item_a_id,
                "system_id": system_a_id,
                "usage_status_id": self.usage_status_value_id_dict[ITEM_DATA_REQUIRED_VALUES_ONLY["usage_status"]],
            },
            {
                **ITEM_GET_DATA_ALL_VALUES_NO_PROPERTIES,
                "catalogue_item_id": catalogue_item_a_id,
                "system_id": system_b_id,
                "usage_status_id": self.usage_status_value_id_dict[ITEM_DATA_REQUIRED_VALUES_ONLY["usage_status"]],
            },
            {
                **ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": catalogue_item_b_id,
                "system_id": system_b_id,
                "usage_status_id": self.usage_status_value_id_dict[ITEM_DATA_REQUIRED_VALUES_ONLY["usage_status"]],
            },
        ]

    def check_get_items_success(self, expected_items_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_items` gave a successful response with the expected data returned.

        :param expected_items_get_data: List of dictionaries containing the expected item data returned as would be
                                        required for `ItemSchema`'s.
        """

        assert self._get_response_item.status_code == 200
        assert self._get_response_item.json() == expected_items_get_data


class TestList(ListDSL):
    """Tests for getting a list of items."""

    def test_list_with_no_filters(self):
        """
        Test getting a list of all items with no filters provided.

        Posts three items the first two in the same catalogue item and separate systems and the third in a different
        catalogue item but the same system as the second. Expects all three to be returned.
        """

        items = self.post_test_items()
        self.get_items(filters={})
        self.check_get_items_success(items)

    def test_list_with_system_id_filter(self):
        """
        Test getting a list of all items with a `system_id` filter provided.

        Posts three items the first two in the same catalogue item and separate systems and the third in a different
        catalogue item but the same system as the second. Expects just the latter two systems to be returned.
        """

        items = self.post_test_items()
        self.get_items(filters={"system_id": items[1]["system_id"]})
        self.check_get_items_success(items[1:])

    def test_list_with_invalid_system_id_filter(self):
        """Test getting a list of all items with an invalid `system_id` filter provided."""

        self.get_items(filters={"system_id": "invalid-id"})
        self.check_get_items_success([])

    def test_list_with_catalogue_item_id_filter(self):
        """
        Test getting a list of all items with a `catalogue_item_id` filter provided.

        Posts three items the first two in the same catalogue item and separate systems and the third in a different
        catalogue item but the same system as the second. Expects just the former two systems to be returned.
        """

        items = self.post_test_items()
        self.get_items(filters={"catalogue_item_id": items[0]["catalogue_item_id"]})
        self.check_get_items_success(items[0:2])

    def test_list_with_invalid_catalogue_item_id_filter(self):
        """Test getting a list of all items with an invalid `catalogue_item_id` filter provided."""

        self.get_items(filters={"catalogue_item_id": "invalid-id"})
        self.check_get_items_success([])

    def test_list_with_system_id_and_catalogue_item_id_filters(self):
        """
        Test getting a list of all items with `system_id` and `catalogue_item_id` filters provided.

        Posts three items the first two in the same catalogue item and separate systems and the third in a different
        catalogue item but the same system as the second. Expects just second item to be returned.
        """

        items = self.post_test_items()
        self.get_items(filters={"system_id": items[2]["system_id"], "catalogue_item_id": items[0]["catalogue_item_id"]})
        self.check_get_items_success([items[1]])

    def test_list_with_system_id_and_catalogue_item_id_filters_with_no_matching_results(self):
        """
        Test getting a list of all items with `system_id` and `catalogue_item_id` filters provided when there are no
        matching results.
        """

        self.get_items(filters={"system_id": str(ObjectId()), "catalogue_item_id": str(ObjectId())})
        self.check_get_items_success([])


# TODO: Update tests


# TODO: Change this to UpdateDSL once done
class DeleteDSL(ListDSL):
    """Base class for delete tests."""

    _delete_response_item: Response

    def delete_item(self, item_id: str) -> None:
        """
        Deletes an item with the given ID.

        :param item_id: ID of the item to be deleted.
        """

        self._delete_response_item = self.test_client.delete(f"/v1/items/{item_id}")

    def check_delete_item_success(self) -> None:
        """Checks that a prior call to `delete_item` gave a successful response with the expected data
        returned."""

        assert self._delete_response_item.status_code == 204

    def check_delete_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_item` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._delete_response_item.status_code == status_code
        assert self._delete_response_item.json()["detail"] == detail


# pylint:disable=too-many-ancestors
class TestDelete(DeleteDSL):
    """Tests for deleting an item."""

    def test_delete(self):
        """Test deleting an item."""

        item_id = self.post_item_and_prerequisites_no_properties(ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.delete_item(item_id)
        self.check_delete_item_success()

        self.get_item(item_id)
        self.check_get_item_failed_with_detail(404, "An item with such ID was not found")

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent item."""

        self.delete_item(str(ObjectId()))
        self.check_delete_item_failed_with_detail(404, "Item not found")

    def test_delete_with_invalid_id(self):
        """Test deleting an item with an invalid ID."""

        self.delete_item("invalid_id")
        self.check_delete_item_failed_with_detail(404, "Item not found")


# # pylint: disable=duplicate-code
# CATALOGUE_CATEGORY_POST_A = {
#     "name": "Category A",
#     "is_leaf": True,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "boolean", "mandatory": True},
#         {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
#         {"name": "Property D", "type": "string", "mandatory": False},
#     ],
# }

# CATALOGUE_ITEM_POST_A = {
#     "name": "Catalogue Item A",
#     "description": "This is Catalogue Item A",
#     "cost_gbp": 129.99,
#     "days_to_replace": 2.0,
#     "drawing_link": "https://drawing-link.com/",
#     "item_model_number": "abc123",
#     "is_obsolete": False,
#     "properties": [
#         {"name": "Property A", "value": 20},
#         {"name": "Property B", "value": False},
#         {"name": "Property C", "value": "20x15x10"},
#     ],
# }

# MANUFACTURER_POST = {
#     "name": "Manufacturer A",
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

# ITEM_POST = {
#     "is_defective": False,
#     "warranty_end_date": "2015-11-15T23:59:59Z",
#     "serial_number": "xyz123",
#     "delivered_date": "2012-12-05T12:00:00Z",
#     "notes": "Test notes",
#     "properties": [{"name": "Property A", "value": 21}],
# }

# ITEM_POST_EXPECTED = {
#     **ITEM_POST,
#     **CREATED_MODIFIED_VALUES_EXPECTED,
#     "id": ANY,
#     "purchase_order_number": None,
#     "asset_number": None,
#     "properties": [
#         {"name": "Property A", "value": 21, "unit": "mm"},
#         {"name": "Property B", "value": False, "unit": None},
#         {"name": "Property C", "value": "20x15x10", "unit": "cm"},
#         {"name": "Property D", "value": None, "unit": None},
#     ],
# }


# # pylint: disable=duplicate-code
# def _post_units(test_client):
#     """Utility function for posting all mock units defined at the top of this file"""

#     response = test_client.get("/v1/units")
#     units = response.json()

#     if response.json() == []:

#         response = test_client.post("/v1/units", json=UNIT_POST_A)
#         unit_mm = response.json()

#         response = test_client.post("/v1/units", json=UNIT_POST_B)
#         unit_cm = response.json()

#         units = [unit_mm, unit_cm]

#     return units


# def _post_catalogue_category_with_units(test_client, catalogue_category):
#     """Utility function for posting Catalogue category a defined at the top of this file"""

#     units = _post_units(test_client)

#     response = test_client.post(
#         "/v1/catalogue-categories",
#         json={
#             **catalogue_category,
#             "properties": replace_unit_values_with_ids_in_properties(catalogue_category["properties"], units),
#         },
#     )
#     catalogue_category = response.json()

#     return catalogue_category


# # pylint: enable=duplicate-code


# def test_partial_update_item(test_client):
#     """
#     Test changing 'usage_status' and 'is_defective' in an item
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]
#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {"usage_status": "Used", "is_defective": True}
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 200

#     item = response.json()

#     assert item == {
#         **ITEM_POST_EXPECTED,
#         **item_patch,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "usage_status": "New",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             ITEM_POST_EXPECTED["properties"],
#         ),
#     }


# def test_partial_update_item_invalid_id(test_client):
#     """
#     Test updating an item with an invalid ID.
#     """

#     item_patch = {"usage_status_id": str(ObjectId()), "is_defective": True}

#     response = test_client.patch("/v1/items/invalid", json=item_patch)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Item not found"


# def test_partial_update_item_non_existent_id(test_client):
#     """
#     Test updating an item with a non-existent ID.
#     """
#     item_patch = {"usage_status_id": str(ObjectId()), "is_defective": True}

#     response = test_client.patch(f"/v1/items/{str(ObjectId())}", json=item_patch)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Item not found"


# def test_partial_update_change_catalogue_item_id(test_client):
#     """
#     Test moving an item to another catalogue item
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {"catalogue_item_id": str(ObjectId())}
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "Cannot change the catalogue item of an item"


# def test_partial_update_change_system_id(test_client):
#     """
#     Test changing the system ID of an item
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id_a = response.json()["id"]

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_B)
#     system_id_b = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]
#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id_a,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {"system_id": system_id_b}
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 200

#     item = response.json()

#     assert item == {
#         **ITEM_POST_EXPECTED,
#         **item_patch,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id_b,
#         "usage_status_id": usage_status_id,
#         "usage_status": "New",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             ITEM_POST_EXPECTED["properties"],
#         ),
#     }


# def test_partial_update_change_non_existent_system_id(test_client):
#     """
#     Test updating system ID which is non-existent
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {"system_id": str(ObjectId())}
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified system does not exist"


# def test_partial_update_change_non_existent_usage_status_id(test_client):
#     """
#     Test updating usage status ID which is non-existent
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {"usage_status_id": str(ObjectId())}
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified usage status does not exist"


# def test_partial_update_change_invalid_usage_status_id(test_client):
#     """
#     Test updating usage status ID which is invalid
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {"usage_status_id": "invalid"}
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified usage status does not exist"


# def test_partial_update_property_values(test_client):
#     """
#     Test updating property values
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": 12},
#                 {"name": "Property B", "value": False},
#                 {"name": "Property C", "value": "20x15x10"},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 200

#     item = response.json()

#     assert item == {
#         **ITEM_POST_EXPECTED,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "usage_status": "New",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "value": 12, "unit": "mm"}] + ITEM_POST_EXPECTED["properties"][-3:],
#         ),
#     }


# def test_partial_update_property_values_with_mandatory_properties_given_none(
#     test_client,
# ):
#     """
#     Test updating a item's mandatory properties to have a value of None
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property B", "value": None},
#                 {"name": "Property C", "value": None},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.json()["detail"] == f"Mandatory property with ID '{prop_id}' cannot be None."
#     # pylint: enable=duplicate-code


# def test_partial_update_property_values_with_non_mandatory_properties_given_none(
#     test_client,
# ):
#     """
#     Test updating a item's mandatory properties to have a value of None
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": None},
#                 {"name": "Property B", "value": False},
#                 {"name": "Property C", "value": "20x15x10"},
#                 {"name": "Property D", "value": None},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 200

#     item = response.json()

#     assert item == {
#         **ITEM_POST_EXPECTED,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "usage_status": "New",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "unit": "mm", "value": None},
#                 {"name": "Property B", "unit": None, "value": False},
#                 {"name": "Property C", "unit": "cm", "value": "20x15x10"},
#                 {"name": "Property D", "unit": None, "value": None},
#             ],
#         ),
#     }


# def test_partial_update_property_values_with_allowed_values(test_client):
#     """
#     Test updating property values when using allowed_values in the catalogue category properties
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST_ALLOWED_VALUES,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             ITEM_POST_ALLOWED_VALUES["properties"],
#         ),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": 2},
#                 {"name": "Property B", "value": "red"},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 200

#     item = response.json()

#     assert item == {
#         **ITEM_POST_EXPECTED,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "usage_status": "New",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "unit": "mm", "value": 2},
#                 {"name": "Property B", "value": "red", "unit": None},
#             ],
#         ),
#     }


# def test_partial_update_property_values_with_allowed_values_invalid_list_string(
#     test_client,
# ):
#     """
#     Test updating property values when giving a string property a value that is not within the defined
#     allowed_values
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST_ALLOWED_VALUES,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             ITEM_POST_ALLOWED_VALUES["properties"],
#         ),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property B", "value": "blue"}],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.json()["detail"] == f"Invalid value for property with ID '{prop_id}'. Expected one of red, green."
#     # pylint: enable=duplicate-code


# def test_partial_update_property_values_with_allowed_values_invalid_list_number(
#     test_client,
# ):
#     """
#     Test updating property values when giving a number property a value that is not within the defined
#     allowed_values
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST_ALLOWED_VALUES,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             ITEM_POST_ALLOWED_VALUES["properties"],
#         ),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "value": 10}],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][0]["id"]
#     assert response.json()["detail"] == f"Invalid value for property with ID '{prop_id}'. Expected one of 2, 4, 6."
#     # pylint: enable=duplicate-code


# def test_partial_update_with_missing_existing_properties(test_client):
#     """
#     Test updating an item when not all properties defined in the catalogue item are supplied
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property B", "value": False},
#                 {"name": "Property C", "value": "25x10x5"},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     assert response.status_code == 200

#     item = response.json()

#     assert item == {
#         **ITEM_POST_EXPECTED,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "usage_status": "New",
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": 20, "unit": "mm"},
#                 {"name": "Property B", "unit": None, "value": False},
#                 {"name": "Property C", "unit": "cm", "value": "25x10x5"},
#                 {"name": "Property D", "unit": None, "value": None},
#             ],
#         ),
#     }


# def test_partial_update_item_change_value_for_string_property_invalid_type(test_client):
#     """
#     Test changing the value of a string item property to an invalid type.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property C", "value": 21}],
#         )
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][2]["id"]
#     assert response.json()["detail"] == f"Invalid value type for property with ID '{prop_id}'. Expected type: string."
#     # pylint: enable=duplicate-code


# def test_partial_update_item_change_value_for_number_property_invalid_type(test_client):
#     """
#     Test changing the value of a string item property to an invalid type.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "value": "21"}],
#         )
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][0]["id"]
#     assert response.json()["detail"] == f"Invalid value type for property with ID '{prop_id}'. Expected type: number."
#     # pylint: enable=duplicate-code


# def test_partial_update_item_change_value_for_boolean_property_invalid_type(
#     test_client,
# ):
#     """
#     Test changing the value of a string item property to an invalid type.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
#     manufacturer_id = response.json()["id"]
#     # pylint: enable=duplicate-code

#     # pylint: disable=duplicate-code
#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             CATALOGUE_ITEM_POST_A["properties"],
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     # pylint: enable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     response = test_client.post("/v1/items", json=item_post)

#     item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property B", "value": 21}],
#         )
#     }
#     response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.json()["detail"] == f"Invalid value type for property with ID '{prop_id}'. Expected type: boolean."
#     # pylint: enable=duplicate-code
