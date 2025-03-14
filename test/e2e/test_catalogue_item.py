"""
End-to-End tests for the catalogue item router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-ancestors

import copy
from test.e2e.conftest import E2ETestHelpers
from test.e2e.test_catalogue_category import CreateDSL as CatalogueCategoryCreateDSL
from test.e2e.test_manufacturer import CreateDSL as ManufacturerCreateDSL
from test.mock_data import (
    BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
    CATALOGUE_ITEM_GET_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_GET_DATA_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
    CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
    MANUFACTURER_POST_DATA_ALL_VALUES,
    MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE,
    PROPERTY_DATA_STRING_MANDATORY_TEXT,
    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42,
    PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
    SYSTEM_POST_DATA_NO_PARENT_A,
    UNIT_POST_DATA_MM,
    USAGE_STATUS_POST_DATA_NEW,
)
from typing import Any, Optional

import pytest
from bson import ObjectId
from httpx import Response

from inventory_management_system_api.schemas.catalogue_item import CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS


class CreateDSL(CatalogueCategoryCreateDSL, ManufacturerCreateDSL):
    """Base class for create tests."""

    catalogue_category_id: Optional[str]
    manufacturer_id: Optional[str]
    property_name_id_dict: dict[str, str]

    _post_response_catalogue_item: Response

    # Key of property name, and value a dictionary containing the `unit` and `unit_id` as would
    # be expected inside a property response
    _unit_data_lookup_dict: dict[str, dict]

    @pytest.fixture(autouse=True)
    def setup_catalogue_item_create_dsl(self):
        """Setup fixtures"""

        self.property_name_id_dict = {}
        self.catalogue_category_id = None
        self.manufacturer_id = None

        self._unit_data_lookup_dict = {}

    def add_ids_to_expected_catalogue_item_get_data(self, expected_catalogue_item_get_data) -> dict:
        """
        Adds required IDs to some expected catalogue item get data based on what has already been posted.

        :param expected_catalogue_item_get_data: Dictionary containing the expected catalogue item data returned as
                                                 would be required for a `CatalogueItemSchema`. Does not need mandatory
                                                 IDs (e.g. `manufacturer_id`) as they will be added here.
        """
        # Where there are properties add the property ID, unit ID and unit value
        expected_catalogue_item_get_data = E2ETestHelpers.add_property_ids_to_properties(
            expected_catalogue_item_get_data, self.property_name_id_dict
        )
        properties = []
        for prop in expected_catalogue_item_get_data["properties"]:
            properties.append({**prop, **self._unit_data_lookup_dict[prop["id"]]})
        expected_catalogue_item_get_data = {**expected_catalogue_item_get_data, "properties": properties}

        return {
            **expected_catalogue_item_get_data,
            "catalogue_category_id": self.catalogue_category_id,
            "manufacturer_id": self.manufacturer_id,
        }

    def post_catalogue_category(self, catalogue_category_data: dict) -> Optional[str]:
        """
        Posts a catalogue category with the given data and returns the ID of the created catalogue category if
        successful.

        :param catalogue_category_data: Dictionary containing the basic catalogue category data as would be required
                                        for a `CatalogueCategoryPostSchema` but with any `unit_id`'s replaced by the
                                        `unit` value in its properties as the IDs will be added automatically.
        :return: ID of the created catalogue category (or `None` if not successful).
        """
        self.catalogue_category_id = CatalogueCategoryCreateDSL.post_catalogue_category(self, catalogue_category_data)

        # Assign the property name id dict for any properties
        if self.catalogue_category_id:
            self.property_name_id_dict = {}
            catalogue_category_data = self._post_response_catalogue_category.json()
            for prop in catalogue_category_data["properties"]:
                self.property_name_id_dict[prop["name"]] = prop["id"]
                self._unit_data_lookup_dict[prop["id"]] = {"unit_id": prop["unit_id"], "unit": prop["unit"]}

        return self.catalogue_category_id

    def post_manufacturer(self, manufacturer_post_data: dict) -> Optional[str]:
        """
        Posts a manufacturer with the given data, returns the ID of the created manufacturer if successful.

        :param manufacturer_post_data: Dictionary containing the manufacturer data as would be required for a
                                       `ManufacturerPostSchema`.
        :return: ID of the created manufacturer (or `None` if not successful).
        """
        self.manufacturer_id = ManufacturerCreateDSL.post_manufacturer(self, manufacturer_post_data)
        return self.manufacturer_id

    def post_catalogue_item(self, catalogue_item_data: dict) -> Optional[str]:
        """
        Posts a catalogue item with the given data and returns the ID of the created catalogue item if successful.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required
                                        for a `CatalogueItemPostSchema` but with mandatory IDs missing and
                                        any `id`'s replaced by the `name` value in its properties as the
                                        IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        # Replace any unit values with unit IDs
        full_catalogue_item_data = copy.deepcopy(catalogue_item_data)
        full_catalogue_item_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            full_catalogue_item_data, self.unit_value_id_dict
        )
        full_catalogue_item_data = E2ETestHelpers.replace_property_names_with_ids_in_properties(
            full_catalogue_item_data, self.property_name_id_dict
        )

        # Insert mandatory IDs if they have been created
        if self.catalogue_category_id:
            full_catalogue_item_data["catalogue_category_id"] = self.catalogue_category_id
        if self.manufacturer_id:
            full_catalogue_item_data["manufacturer_id"] = self.manufacturer_id

        self._post_response_catalogue_item = self.test_client.post("/v1/catalogue-items", json=full_catalogue_item_data)

        return (
            self._post_response_catalogue_item.json()["id"]
            if self._post_response_catalogue_item.status_code == 201
            else None
        )

    def post_catalogue_item_and_prerequisites_no_properties(self, catalogue_item_data: dict) -> Optional[str]:
        """
        Utility method that posts a catalogue item with the given data and also its prerequisite manufacturer,
        catalogue category and units. Uses `CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES` for the catalogue
        category.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required for a
                                    `CatalogueItemPostSchema` but with mandatory IDs missing and any `id`'s replaced by
                                    the `name` value in its properties as the IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)

        return self.post_catalogue_item(catalogue_item_data)

    def post_catalogue_item_and_prerequisites_with_properties(self, catalogue_item_data: dict) -> Optional[str]:
        """
        Utility method that posts a catalogue item with the given data and also its prerequisite manufacturer,
        catalogue category and units. Uses BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM for the catalogue category.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required for a
                                    `CatalogueItemPostSchema` but with mandatory IDs missing and any `id`'s replaced by
                                    the `name` value in its properties as the IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)

        return self.post_catalogue_item(catalogue_item_data)

    def post_catalogue_item_and_prerequisites_with_given_properties(
        self, catalogue_category_properties_data: list[dict], catalogue_item_properties_data: list[dict]
    ) -> Optional[str]:
        """
        Utility method that posts a catalogue item with specific given properties and also its prerequisite
        manufacturer, catalogue category and units. Uses BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM and
        CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES as a base.

        :param catalogue_category_properties_data: List of dictionaries containing the basic catalogue category property
                        data as would be required for a `CatalogueCategoryPostPropertySchema` but with any `unit_id`'s
                        replaced by the `unit` value in its properties as the IDs will be added automatically.
        :param catalogue_item_properties_data: List of dictionaries containing the basic catalogue item property data as
                        would be required for a `PropertyPostSchema` but with any `id`'s replaced by the `name` value as
                        the IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "properties": catalogue_category_properties_data,
            }
        )
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)

        return self.post_catalogue_item(
            {**CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES, "properties": catalogue_item_properties_data}
        )

    def post_catalogue_item_and_prerequisites_with_allowed_values(
        self, property_type: str, allowed_values_post_data: dict, property_value: Any
    ) -> Optional[str]:
        """
        Utility method that posts a catalogue item with a property named 'property' of a given type with a given set of
        allowed values as well as any prerequisite entities (a catalogue category and a manufacturer).

        :param property_type: Type of the property to post.
        :param allowed_values_post_data: Dictionary containing the allowed values data as would be required for an
                                         `AllowedValuesSchema` to be posted with the catalogue category.
        :param property_value: Value of the property to post for the item.
        :return: ID of the created catalogue item (or `None` if not successful).
        """
        self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
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
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        return self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [{"name": "property", "value": property_value}],
            }
        )

    def check_post_catalogue_item_success(self, expected_catalogue_item_get_data: dict) -> None:
        """
        Checks that a prior call to `post_catalogue_item` gave a successful response with the expected data
        returned.

        :param expected_catalogue_item_get_data: Dictionary containing the expected catalogue item data returned as
                                would be required for a `CatalogueItemSchema`. Does not need mandatory IDs (e.g.
                                `manufacturer_id`) as they will be added automatically to check they are as expected.
        """

        assert self._post_response_catalogue_item.status_code == 201
        assert self._post_response_catalogue_item.json() == self.add_ids_to_expected_catalogue_item_get_data(
            expected_catalogue_item_get_data
        )

    def check_post_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `post_catalogue_item` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._post_response_catalogue_item.status_code == status_code
        assert self._post_response_catalogue_item.json()["detail"] == detail

    def check_post_catalogue_item_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_catalogue_item` gave a failed response with the expected code and
        pydantic validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._post_response_catalogue_item.status_code == status_code
        assert self._post_response_catalogue_item.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue item."""

    def test_create_with_only_required_values_provided(self):
        """Test creating a catalogue item with only required values provided."""

        self.post_catalogue_item_and_prerequisites_no_properties(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_non_obsolete_with_all_values_except_properties(self):
        """Test creating a non obsolete catalogue item with all values provided except `properties` and
        those related to being obsolete."""

        self.post_catalogue_item_and_prerequisites_no_properties(CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_NOT_OBSOLETE_NO_PROPERTIES)

    def test_create_obsolete_with_all_values_except_properties(self):
        """Test creating an obsolete catalogue item with all values provided except `properties`."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        obsolete_replacement_catalogue_item_id = self.post_catalogue_item(
            CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES
        )
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            }
        )

        self.check_post_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            }
        )

    def test_create_obsolete_with_non_existent_obsolete_replacement_catalogue_item_id(self):
        """Test creating an obsolete catalogue item with a non-existent `obsolete_replacement_catalogue_item_id`."""

        self.post_catalogue_item_and_prerequisites_no_properties(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": str(ObjectId()),
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422, "The specified replacement catalogue item does not exist"
        )

    def test_create_obsolete_with_invalid_obsolete_replacement_catalogue_item_id(self):
        """Test creating an obsolete catalogue item an invalid `obsolete_replacement_catalogue_item_id`."""

        self.post_catalogue_item_and_prerequisites_no_properties(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": "invalid-id",
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422, "The specified replacement catalogue item does not exist"
        )

    def test_create_with_all_properties_provided(self):
        """Test creating a catalogue item with all properties within the catalogue category being defined."""

        self.post_catalogue_item_and_prerequisites_with_properties(CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES)

    def test_create_with_mandatory_properties_only(self):
        """Test creating a catalogue item with only mandatory properties defined."""

        self.post_catalogue_item_and_prerequisites_with_properties(CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY)

    def test_create_with_mandatory_properties_given_none(self):
        """Test creating a catalogue item when mandatory properties are given a value of `None`."""

        self.post_catalogue_item_and_prerequisites_with_properties(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [{**PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE, "value": None}],
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Mandatory property with ID '{self.property_name_id_dict[PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE['name']]}' "
            "cannot be None.",
        )

    def test_create_with_missing_mandatory_properties(self):
        """Test creating a catalogue item when missing mandatory properties."""

        self.post_catalogue_item_and_prerequisites_with_properties(
            {**CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY, "properties": []}
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Missing mandatory property with ID: "
            f"'{self.property_name_id_dict[PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE['name']]}'",
        )

    def test_create_with_non_mandatory_properties_given_none(self):
        """Test creating a catalogue item when non-mandatory properties are given a value of `None`."""

        self.post_catalogue_item_and_prerequisites_with_properties(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [
                    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
                    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE,
                    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
                ],
            }
        )

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY)

    def test_create_with_string_property_with_invalid_value_type(self):
        """Test creating a catalogue item with an invalid value type for a string property."""

        self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY],
            catalogue_item_properties_data=[
                {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY["name"], "value": 42},
            ],
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID "
            f"'{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY['name']]}'. "
            "Expected type: string.",
        )

    def test_create_with_number_property_with_invalid_value_type(self):
        """Test creating a catalogue item with an invalid value type for a number property."""

        self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            catalogue_item_properties_data=[
                {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT["name"], "value": "42"},
            ],
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID '"
            f"{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT['name']]}"
            "'. Expected type: number.",
        )

    def test_create_with_boolean_property_with_invalid_value_type(self):
        """Test creating a catalogue item with an invalid value type for a boolean property."""

        self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY],
            catalogue_item_properties_data=[
                {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY["name"], "value": 0},
            ],
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID '"
            f"{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']]}"
            "'. Expected type: boolean.",
        )

    def test_create_with_allowed_values_list(self):
        """Test creating a catalogue item with properties that have allowed values lists."""

        self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
                CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
            ],
            catalogue_item_properties_data=[
                PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
                PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
            ],
        )
        self.check_post_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [
                    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
                    PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
                ],
            }
        )

    def test_create_with_string_property_with_allowed_values_list_with_invalid_value(self):
        """Test creating a catalogue item with a string property with an allowed values list while giving it a value not
        in the list."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, "value2"
        )
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected one of value1.",
        )

    def test_create_with_string_property_with_allowed_values_list_with_invalid_type(self):
        """Test creating a catalogue item with a string property with an allowed values list while giving it a value
        with an incorrect type."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, 42
        )
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: string.",
        )

    def test_create_with_number_property_with_allowed_values_list_with_invalid_value(self):
        """Test creating a catalogue item with a number property with an allowed values list while giving it a value not
        in the list."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values("number", {"type": "list", "values": [1]}, 2)
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. Expected one of 1.",
        )

    def test_create_with_number_property_with_allowed_values_list_with_invalid_type(self):
        """Test creating a catalogue item with a number property with an allowed values list while giving it a value
        with an incorrect type."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "number", {"type": "list", "values": [1]}, "test"
        )
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: number.",
        )

    def test_create_in_non_leaf_catalogue_category(self):
        """Test creating a catalogue item within a non-leaf catalogue category."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_failed_with_detail(
            409, "Adding a catalogue item to a non-leaf catalogue category is not allowed"
        )

    def test_create_with_non_existent_catalogue_category_id(self):
        """Test creating a catalogue item with a non-existent catalogue category ID."""

        self.catalogue_category_id = str(ObjectId())
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_failed_with_detail(422, "The specified catalogue category does not exist")

    def test_create_with_invalid_catalogue_category_id(self):
        """Test creating a catalogue item with an invalid catalogue category ID."""

        self.catalogue_category_id = "invalid-id"
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_failed_with_detail(422, "The specified catalogue category does not exist")

    def test_create_with_non_existent_manufacturer_id(self):
        """Test creating a catalogue item with a non-existent manufacturer ID."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.manufacturer_id = str(ObjectId())
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_failed_with_detail(422, "The specified manufacturer does not exist")

    def test_create_with_invalid_manufacturer_id(self):
        """Test creating a catalogue item with an invalid manufacturer ID."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.manufacturer_id = "invalid-id"
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_failed_with_detail(422, "The specified manufacturer does not exist")


class GetDSL(CreateDSL):
    """Base class for get tests."""

    _get_response_catalogue_item: Response

    def get_catalogue_item(self, catalogue_item_id: str) -> None:
        """
        Gets a catalogue item with the given ID.

        :param catalogue_item_id: ID of the catalogue item to be obtained.
        """

        self._get_response_catalogue_item = self.test_client.get(f"/v1/catalogue-items/{catalogue_item_id}")

    def check_get_catalogue_item_success(self, expected_catalogue_item_get_data: dict) -> None:
        """
        Checks that a prior call to `get_catalogue_item` gave a successful response with the expected data returned.

        :param expected_catalogue_item_get_data: Dictionary containing the expected catalogue item data returned as
                                                 would be required for a `CatalogueItemSchema`. Does not need mandatory
                                                 IDs (e.g. `manufacturer_id`) as they will be added automatically to
                                                 check they are as expected.
        """

        assert self._get_response_catalogue_item.status_code == 200
        assert self._get_response_catalogue_item.json() == self.add_ids_to_expected_catalogue_item_get_data(
            expected_catalogue_item_get_data
        )

    def check_get_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `get_catalogue_item` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response_catalogue_item.status_code == status_code
        assert self._get_response_catalogue_item.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a catalogue item."""

    def test_get(self):
        """Test getting a catalogue item."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.get_catalogue_item(catalogue_item_id)
        self.check_get_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_get_with_non_existent_id(self):
        """Test getting a catalogue item with a non-existent ID."""

        self.get_catalogue_item(str(ObjectId()))
        self.check_get_catalogue_item_failed_with_detail(404, "Catalogue item not found")

    def test_get_with_invalid_id(self):
        """Test getting a catalogue item with an invalid ID."""

        self.get_catalogue_item("invalid-id")
        self.check_get_catalogue_item_failed_with_detail(404, "Catalogue item not found")


class ListDSL(GetDSL):
    """Base class for list tests."""

    def get_catalogue_items(self, filters: dict) -> None:
        """
        Gets a list of catalogue items with the given filters.

        :param filters: Filters to use in the request.
        """

        self._get_response_catalogue_item = self.test_client.get("/v1/catalogue-items", params=filters)

    def post_test_catalogue_items_and_prerequisites(self) -> list[dict]:
        """
        Posts two catalogue items having first posted the required prerequisite entities. Each catalogue item is in a
        separate catalogue category.

        :return: List of dictionaries containing the expected catalogue item data returned from a get endpoint in
                 the form of a `CatalogueItemSchema`.
        """

        first_catalogue_category_id = self.post_catalogue_category(
            CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES
        )
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)
        second_catalogue_category_id = self.post_catalogue_category(
            {**CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES, "name": "Another category"}
        )
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES)

        return [
            {
                **CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_category_id": first_catalogue_category_id,
                "manufacturer_id": self.manufacturer_id,
            },
            {
                **CATALOGUE_ITEM_GET_DATA_NOT_OBSOLETE_NO_PROPERTIES,
                "catalogue_category_id": second_catalogue_category_id,
                "manufacturer_id": self.manufacturer_id,
            },
        ]

    def check_get_catalogue_items_success(self, expected_catalogue_items_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_catalogue_items` gave a successful response with the expected data returned.

        :param expected_catalogue_items_get_data: List of dictionaries containing the expected catalogue item data
                                                  returned as would be required for `CatalogueItemSchema`'s.
        """

        assert self._get_response_catalogue_item.status_code == 200
        assert self._get_response_catalogue_item.json() == expected_catalogue_items_get_data


class TestList(ListDSL):
    """Tests for getting a list of catalogue items."""

    def test_list_with_no_filters(self):
        """
        Test getting a list of all catalogue items with no filters provided.

        Posts two catalogue items in different catalogue categories and expects both to be returned.
        """

        catalogue_items = self.post_test_catalogue_items_and_prerequisites()
        self.get_catalogue_items(filters={})
        self.check_get_catalogue_items_success(catalogue_items)

    def test_list_with_catalogue_category_id_filter(self):
        """
        Test getting a list of all catalogue items with a `catalogue_category_id` filter provided.

        Posts two catalogue items in different catalogue categories and then filter using the `catalogue_category_id`
        expecting only the second catalogue item to be returned.
        """

        catalogue_items = self.post_test_catalogue_items_and_prerequisites()
        self.get_catalogue_items(filters={"catalogue_category_id": catalogue_items[1]["catalogue_category_id"]})
        self.check_get_catalogue_items_success([catalogue_items[1]])

    def test_list_with_catalogue_category_id_filter_with_no_matching_results(self):
        """Test getting a list of all catalogue items with a `catalogue_category_id` filter that returns no results."""

        self.get_catalogue_items(filters={"catalogue_category_id": str(ObjectId())})
        self.check_get_catalogue_items_success([])

    def test_list_with_invalid_catalogue_category_id_filter(self):
        """Test getting a list of all catalogue items with an invalid `catalogue_category_id` filter returns no
        results."""

        self.get_catalogue_items(filters={"catalogue_category_id": "invalid-id"})
        self.check_get_catalogue_items_success([])


class UpdateDSL(ListDSL):
    """Base class for update tests."""

    _patch_response_catalogue_item: Response

    def patch_catalogue_item(self, catalogue_item_id: str, catalogue_item_update_data: dict) -> None:
        """
        Patches a catalogue item with the given ID.

        :param catalogue_item_id: ID of the catalogue item to patch.
        :param catalogue_item_update_data: Dictionary containing the basic patch data as would be required for a
                                           `CatalogueItemPatchSchema` but with any `id`'s replaced by the `name` value
                                           in its properties as the IDs will be added automatically.
        """

        # Replace any property names with ids
        catalogue_item_update_data = E2ETestHelpers.replace_property_names_with_ids_in_properties(
            catalogue_item_update_data, self.property_name_id_dict
        )

        self._patch_response_catalogue_item = self.test_client.patch(
            f"/v1/catalogue-items/{catalogue_item_id}", json=catalogue_item_update_data
        )

    def post_child_item(self) -> None:
        """Utility method that posts a child item for the last catalogue item posted."""

        # pylint:disable=fixme
        # TODO: This should be cleaned up in future

        response = self.test_client.post("/v1/systems", json=SYSTEM_POST_DATA_NO_PARENT_A)
        system_id = response.json()["id"]

        response = self.test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_DATA_NEW)
        usage_status_id = response.json()["id"]

        item_post = {
            "is_defective": False,
            "warranty_end_date": "2015-11-15T23:59:59Z",
            "serial_number": "xyz123",
            "delivered_date": "2012-12-05T12:00:00Z",
            "notes": "Test notes",
            "catalogue_item_id": self._post_response_catalogue_item.json()["id"],
            "system_id": system_id,
            "usage_status_id": usage_status_id,
            "properties": [],
        }
        self.test_client.post("/v1/items", json=item_post)

    def check_patch_catalogue_item_success(self, expected_catalogue_item_get_data: dict) -> None:
        """
        Checks that a prior call to `patch_catalogue_item` gave a successful response with the expected data
        returned.

        :param expected_catalogue_item_get_data: Dictionary containing the expected catalogue item data returned as
                                        would be required for a `CatalogueItemSchema`. Does not need mandatory IDs
                                        (e.g. `manufacturer_id`) as they will be added automatically to check they are
                                        as expected.
        """

        assert self._patch_response_catalogue_item.status_code == 200
        assert self._patch_response_catalogue_item.json() == self.add_ids_to_expected_catalogue_item_get_data(
            expected_catalogue_item_get_data
        )

        E2ETestHelpers.check_created_and_modified_times_updated_correctly(
            self._post_response_catalogue_item, self._patch_response_catalogue_item
        )

    def check_patch_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `patch_catalogue_item` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._patch_response_catalogue_item.status_code == status_code
        assert self._patch_response_catalogue_item.json()["detail"] == detail

    def check_patch_catalogue_item_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `patch_catalogue_item` gave a failed response with the expected code and
        pydantic validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._patch_response_catalogue_item.status_code == status_code
        assert self._patch_response_catalogue_item.json()["detail"][0]["msg"] == message


class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue item."""

    def test_partial_update_all_fields_except_ids_or_properties_with_no_children(self):
        """Test updating all fields of a catalogue item except any of its `_id` fields or properties when it has
        no children."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES)
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_NOT_OBSOLETE_NO_PROPERTIES)

    def test_partial_update_all_fields_except_ids_or_properties_with_children(self):
        """Test updating all fields of a catalogue item except any of its `_id` fields or properties when it has
        children."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_child_item()

        self.patch_catalogue_item(catalogue_item_id, CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES)
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_NOT_OBSOLETE_NO_PROPERTIES)

    def test_partial_update_catalogue_category_id_no_properties(self):
        """Test updating the `catalogue_category_id` of a catalogue item when no properties are involved."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        new_catalogue_category_id = self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY)

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id})
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_partial_update_catalogue_category_id_with_same_defined_properties(self):
        """Test updating the `catalogue_category_id` of a catalogue item when both the old and new catalogue category
        has identical properties."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {**BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM, "name": "Another category"}
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id})
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES)

    def test_partial_update_catalogue_category_id_and_properties_with_same_defined_properties(self):
        """Test updating the `catalogue_category_id` and `properties` of a catalogue item when both the old and new
        catalogue category has identical properties."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {**BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM, "name": "Another category"}
        )

        self.patch_catalogue_item(
            catalogue_item_id,
            {
                "catalogue_category_id": new_catalogue_category_id,
                "properties": CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY["properties"],
            },
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY["properties"],
            }
        )

    def test_partial_update_catalogue_category_id_with_same_defined_properties_different_order(self):
        """Test updating the `catalogue_category_id` of a catalogue item when both the old and new catalogue category
        has identical properties but in a different order."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "name": "Another category",
                "properties": BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM["properties"][::-1],
            }
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Cannot move catalogue item to a category with different properties without specifying the new properties",
        )

    def test_partial_update_catalogue_category_id_and_properties_with_same_defined_properties_different_order(self):
        """Test updating the `catalogue_category_id` and `properties` of a catalogue item when both the old and new
        catalogue category has identical properties but in a different order."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "name": "Another category",
                "properties": BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM["properties"][::-1],
            }
        )

        self.patch_catalogue_item(
            catalogue_item_id,
            {
                "catalogue_category_id": new_catalogue_category_id,
                "properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"][::-1],
            },
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES["properties"][::-1],
            }
        )

    def test_partial_update_catalogue_category_id_with_different_defined_properties(self):
        """Test updating the `catalogue_category_id` of a catalogue item when the old and new catalogue category
        have different properties."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "name": "Another category",
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            }
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Cannot move catalogue item to a category with different properties without specifying the new properties",
        )

    def test_partial_update_catalogue_category_id_and_properties_with_different_defined_properties(self):
        """Test updating the `catalogue_category_id` and `properties` of a catalogue item when the old and new catalogue
        category have different properties."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "name": "Another category",
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            }
        )

        self.patch_catalogue_item(
            catalogue_item_id,
            {
                "catalogue_category_id": new_catalogue_category_id,
                "properties": [PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42],
            },
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42],
            }
        )

    def test_partial_update_catalogue_category_id_while_removing_all_defined_properties(self):
        """Test updating the `catalogue_category_id` of a catalogue item when the old catalogue category and item has
        properties but the new one does not."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "name": "Another category",
                "properties": [],
            }
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Cannot move catalogue item to a category with different properties without specifying the new properties",
        )

    def test_partial_update_catalogue_category_id_and_properties_while_removing_all_defined_properties(self):
        """Test updating the `catalogue_category_id` and `properties` of a catalogue item when the old catalogue
        category and item has properties but the new one does not."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )
        new_catalogue_category_id = self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM,
                "name": "Another category",
                "properties": [],
            }
        )

        self.patch_catalogue_item(
            catalogue_item_id,
            {"catalogue_category_id": new_catalogue_category_id, "properties": []},
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [],
            }
        )

    def test_partial_update_catalogue_category_id_and_properties_with_missing_non_mandatory_properties(self):
        """Test updating the `catalogue_category_id` of a catalogue item when the item has missing non mandatory
        properties in the new catalogue category."""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        new_catalogue_category_id = self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM)

        self.patch_catalogue_item(
            catalogue_item_id,
            {
                "catalogue_category_id": new_catalogue_category_id,
                "properties": CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY["properties"],
            },
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
                "properties": CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY["properties"],
            }
        )

    def test_partial_update_catalogue_category_id_and_properties_with_missing_mandatory_properties(self):
        """Test updating the `catalogue_category_id` of a catalogue item when the item has missing mandatory properties
        in the new catalogue category."""

        self.post_unit(UNIT_POST_DATA_MM)
        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        new_catalogue_category_id = self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM)

        self.patch_catalogue_item(
            catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id, "properties": []}
        )
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Missing mandatory property with ID: "
            f"'{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']]}'",
        )

    def test_partial_update_catalogue_category_id_with_non_leaf_id(self):
        """Test updating the `catalogue_category_id` of a catalogue item to a non-leaf catalogue category."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        new_catalogue_category_id = self.post_catalogue_category(
            CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": new_catalogue_category_id})
        self.check_patch_catalogue_item_failed_with_detail(
            409, "Adding a catalogue item to a non-leaf catalogue category is not allowed"
        )

    def test_partial_update_catalogue_category_id_with_non_existent_id(self):
        """Test updating the `catalogue_category_id` of a catalogue item to a non-existent catalogue category."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": str(ObjectId())})
        self.check_patch_catalogue_item_failed_with_detail(422, "The specified catalogue category does not exist")

    def test_partial_update_catalogue_category_id_with_invalid_id(self):
        """Test updating the `catalogue_category_id` of a catalogue item to an invalid ID."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"catalogue_category_id": "invalid-id"})
        self.check_patch_catalogue_item_failed_with_detail(422, "The specified catalogue category does not exist")

    def test_partial_update_manufacturer_id_with_no_children(self):
        """Test updating the `manufacturer_id` of a catalogue item when it has no children."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        new_manufacturer_id = self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)

        self.patch_catalogue_item(catalogue_item_id, {"manufacturer_id": new_manufacturer_id})
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_partial_update_manufacturer_id_with_children(self):
        """Test updating the `manufacturer_id` of a catalogue item when it has children."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_child_item()
        new_manufacturer_id = self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)

        self.patch_catalogue_item(catalogue_item_id, {"manufacturer_id": new_manufacturer_id})
        self.check_patch_catalogue_item_failed_with_detail(
            409,
            "Catalogue item has child elements, so the following fields cannot be updated: "
            + ", ".join(CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS),
        )

    def test_partial_update_manufacturer_id_with_non_existent_id(self):
        """Test updating the `manufacturer_id` of a catalogue item to a non-existent manufacturer."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"manufacturer_id": str(ObjectId())})
        self.check_patch_catalogue_item_failed_with_detail(422, "The specified manufacturer does not exist")

    def test_partial_update_manufacturer_id_with_invalid_id(self):
        """Test updating the `manufacturer_id` of a catalogue item to an invalid ID."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"manufacturer_id": "invalid-id"})
        self.check_patch_catalogue_item_failed_with_detail(422, "The specified manufacturer does not exist")

    def test_partial_update_properties_with_no_children(self):
        """Test updating the `properties` of a catalogue item when it has no children."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"properties": []})
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_partial_update_properties_with_mandatory_properties_given_none(self):
        """Test updating the `properties` of a catalogue item to have mandatory properties with a value of `None`."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": [{**PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE, "value": None}]}
        )
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Mandatory property with ID "
            f"'{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']]}' "
            "cannot be None.",
        )

    def test_partial_update_properties_with_non_mandatory_properties_given_none(self):
        """Test updating the `properties` of a catalogue item to have non mandatory properties with a value of
        `None`."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )

        self.patch_catalogue_item(
            catalogue_item_id,
            {
                "properties": [
                    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
                    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE,
                    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
                ]
            },
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY["properties"],
            }
        )

    def test_partial_update_properties_adding_non_mandatory_property(self):
        """Test updating the `properties` of a catalogue item to define a previously undefined non-mandatory
        property."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            {
                **CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
                "properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"][0:1],
            }
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"]}
        )
        self.check_patch_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES)

    def test_partial_update_properties_removing_non_mandatory_property(self):
        """Test updating the `properties` of a catalogue item to remove a previously defined non-mandatory property."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"][0:2]}
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [
                    *CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES["properties"][0:2],
                    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
                ],
            }
        )

    def test_partial_update_properties_removing_mandatory_property(self):
        """Test updating the `properties` of a catalogue item to remove a previously defined mandatory property."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"][1:3]}
        )
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Missing mandatory property with ID: "
            f"'{self.property_name_id_dict[PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE['name']]}'",
        )

    def test_partial_update_properties_with_string_property_with_invalid_value_type(self):
        """Test updating the `properties` of a catalogue item to have an invalid value type for a string property."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY],
            catalogue_item_properties_data=[PROPERTY_DATA_STRING_MANDATORY_TEXT],
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": [{**PROPERTY_DATA_STRING_MANDATORY_TEXT, "value": 42}]}
        )
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID "
            f"'{self.property_name_id_dict[PROPERTY_DATA_STRING_MANDATORY_TEXT['name']]}'. Expected type: string.",
        )

    def test_partial_update_properties_with_number_property_with_invalid_value_type(self):
        """Test updating the `properties` of a catalogue item to have an invalid value type for a number property."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            catalogue_item_properties_data=[PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42],
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": [{**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42, "value": "42"}]}
        )
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID "
            f"'{self.property_name_id_dict[PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42['name']]}'. "
            "Expected type: number.",
        )

    def test_partial_update_properties_with_boolean_property_with_invalid_value_type(self):
        """Test updating the `properties` of a catalogue item to have an invalid value type for a boolean property."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY],
            catalogue_item_properties_data=[PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE],
        )

        self.patch_catalogue_item(
            catalogue_item_id, {"properties": [{**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "value": "True"}]}
        )
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID "
            f"'{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']]}'. "
            "Expected type: boolean.",
        )

    def test_partial_update_properties_with_allowed_values_list(self):
        """Test updating the `properties` of a catalogue item that has allowed values lists."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_given_properties(
            catalogue_category_properties_data=[
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
                CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
            ],
            catalogue_item_properties_data=[],
        )

        self.patch_catalogue_item(
            catalogue_item_id,
            {
                "properties": [
                    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
                    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
                ]
            },
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [
                    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
                    PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
                ],
            }
        )

    def test_partial_update_string_property_with_allowed_values_list_to_invalid_value(self):
        """Test updating the value of a string property with an allowed values list to be a value not in the list."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1", "value2", "value3"]}, "value1"
        )

        self.patch_catalogue_item(catalogue_item_id, {"properties": [{"name": "property", "value": "value42"}]})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. Expected one of value1, "
            "value2, value3.",
        )

    def test_partial_update_string_property_with_allowed_values_list_to_invalid_value_type(self):
        """Test updating the value of a string property with an allowed values list to be the wrong type."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, "value1"
        )

        self.patch_catalogue_item(catalogue_item_id, {"properties": [{"name": "property", "value": 42}]})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: string.",
        )

    def test_partial_update_number_property_with_allowed_values_list_to_invalid_value(self):
        """Test updating the value of a number property with an allowed values list to be a value not in the list."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "number", {"type": "list", "values": [1, 2, 3]}, 1
        )

        self.patch_catalogue_item(catalogue_item_id, {"properties": [{"name": "property", "value": 42}]})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. Expected one of 1, 2, 3.",
        )

    def test_partial_update_number_property_with_allowed_values_list_to_invalid_value_type(self):
        """Test updating the value of a number property with an allowed values list to be the wrong type."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "number", {"type": "list", "values": [1]}, 1
        )

        self.patch_catalogue_item(catalogue_item_id, {"properties": [{"name": "property", "value": "2"}]})
        self.check_patch_catalogue_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: number.",
        )

    def test_partial_update_properties_with_children(self):
        """Test updating the `properties` of a catalogue item when it has children."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_child_item()

        self.patch_catalogue_item(catalogue_item_id, {"properties": []})
        self.check_patch_catalogue_item_failed_with_detail(
            409,
            "Catalogue item has child elements, so the following fields cannot be updated: "
            + ", ".join(CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS),
        )

    def test_partial_update_obsolete_replacement_catalogue_item_id(self):
        """Test updating the `obsolete_replacement_catalogue_item` of a catalogue item."""

        obsolete_replacement_catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        catalogue_item_id = self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.patch_catalogue_item(
            catalogue_item_id, {"obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id}
        )
        self.check_patch_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            }
        )

    def test_partial_update_obsolete_replacement_catalogue_item_id_with_non_existent_id(self):
        """Test updating the `obsolete_replacement_catalogue_item` of a catalogue item to a non-existent catalogue
        item."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"obsolete_replacement_catalogue_item_id": str(ObjectId())})
        self.check_patch_catalogue_item_failed_with_detail(
            422, "The specified replacement catalogue item does not exist"
        )

    def test_partial_update_obsolete_replacement_catalogue_item_id_with_invalid_id(self):
        """Test updating the `obsolete_replacement_catalogue_item` of a catalogue item to an invalid ID."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.patch_catalogue_item(catalogue_item_id, {"obsolete_replacement_catalogue_item_id": "invalid-id"})
        self.check_patch_catalogue_item_failed_with_detail(
            422, "The specified replacement catalogue item does not exist"
        )

    def test_partial_update_with_non_existent_id(self):
        """Test updating a non-existent catalogue item."""

        self.patch_catalogue_item(str(ObjectId()), {})
        self.check_patch_catalogue_item_failed_with_detail(404, "Catalogue item not found")

    def test_partial_update_invalid_id(self):
        """Test updating a catalogue item with an invalid ID."""

        self.patch_catalogue_item("invalid-id", {})
        self.check_patch_catalogue_item_failed_with_detail(404, "Catalogue item not found")


class DeleteDSL(UpdateDSL):
    """Base class for delete tests."""

    _delete_response_catalogue_item: Response

    def delete_catalogue_item(self, catalogue_item_id: str) -> None:
        """
        Deletes a catalogue item with the given ID.

        :param catalogue_item_id: ID of the catalogue item to be deleted.
        """

        self._delete_response_catalogue_item = self.test_client.delete(f"/v1/catalogue-items/{catalogue_item_id}")

    def check_delete_catalogue_item_success(self) -> None:
        """Checks that a prior call to `delete_catalogue_item` gave a successful response with the expected data
        returned."""

        assert self._delete_response_catalogue_item.status_code == 204

    def check_delete_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_catalogue_item` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._delete_response_catalogue_item.status_code == status_code
        assert self._delete_response_catalogue_item.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue item."""

    def test_delete(self):
        """Test deleting a catalogue item."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )

        self.delete_catalogue_item(catalogue_item_id)
        self.check_delete_catalogue_item_success()

        self.get_catalogue_item(catalogue_item_id)
        self.check_get_catalogue_item_failed_with_detail(404, "Catalogue item not found")

    def test_delete_with_child_item(self):
        """Test deleting a catalogue item with a child item."""

        catalogue_item_id = self.post_catalogue_item_and_prerequisites_no_properties(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY
        )
        self.post_child_item()

        self.delete_catalogue_item(catalogue_item_id)
        self.check_delete_catalogue_item_failed_with_detail(
            409, "Catalogue item has child elements and cannot be deleted"
        )

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent catalogue item."""

        self.delete_catalogue_item(str(ObjectId()))
        self.check_delete_catalogue_item_failed_with_detail(404, "Catalogue item not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a catalogue item with an invalid ID."""

        self.delete_catalogue_item("invalid_id")
        self.check_delete_catalogue_item_failed_with_detail(404, "Catalogue item not found")
