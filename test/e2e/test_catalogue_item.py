# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue item router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code
# pylint: disable=too-many-public-methods

from test.conftest import add_ids_to_properties
from test.e2e.conftest import E2ETestHelpers, replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import (
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    CATALOGUE_ITEM_POST_ALLOWED_VALUES,
    CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED,
    CREATED_MODIFIED_VALUES_EXPECTED,
    SYSTEM_POST_A,
    USAGE_STATUS_POST_A,
    USAGE_STATUS_POST_B,
)
from test.e2e.test_catalogue_category import CreateDSL as CatalogueCategoryCreateDSL
from test.e2e.test_item import ITEM_POST
from test.e2e.test_manufacturer import CreateDSL as ManufacturerCreateDSL
from test.e2e.test_unit import UNIT_POST_A, UNIT_POST_B
from test.mock_data import (
    BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY,
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
    MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_NONE,
    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
    UNIT_POST_DATA_MM,
)
from typing import Any, Optional
from unittest.mock import ANY

import pytest
from bson import ObjectId
from httpx import Response


# TODO: Should this be inherited or should there be a base test client for it? Also need manufacturer and system
class CreateDSL(CatalogueCategoryCreateDSL, ManufacturerCreateDSL):
    """Base class for create tests."""

    catalogue_category_id: Optional[str]
    manufacturer_id: Optional[str]
    property_name_id_dict: dict[str, str]

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
                                                 IDs (e.g. manufacturer_id) as they will be added here.
        """
        # Where there are properties add the property ID, unit ID and unit value
        expected_catalogue_item_get_data = E2ETestHelpers.add_property_ids_to_properties(
            expected_catalogue_item_get_data, self.property_name_id_dict
        )
        properties = []
        for prop in expected_catalogue_item_get_data["properties"]:
            properties.append({**prop, **self._unit_data_lookup_dict[prop["id"]]})
        expected_catalogue_item_get_data["properties"] = properties

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
            catalogue_category_data = self._post_response.json()
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
        Posts a catalogue item with the given data and returns the ID of the created catalogue item if
        successful.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required
                                        for a `CatalogueItemPostSchema` but with mandatory IDs missing and
                                        any `id`'s replaced by the `name` value in its properties as the
                                        IDs will be added automatically.
        :return: ID of the created catalogue item (or `None` if not successful).
        """

        # Replace any unit values with unit IDs
        catalogue_item_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            catalogue_item_data, self.unit_value_id_dict
        )
        catalogue_item_data = E2ETestHelpers.replace_property_names_with_ids_in_properties(
            catalogue_item_data, self.property_name_id_dict
        )

        # Insert mandatory IDs if they have been created
        if self.catalogue_category_id:
            catalogue_item_data["catalogue_category_id"] = self.catalogue_category_id
        if self.manufacturer_id:
            catalogue_item_data["manufacturer_id"] = self.manufacturer_id

        self._post_response = self.test_client.post("/v1/catalogue-items", json=catalogue_item_data)

        return self._post_response.json()["id"] if self._post_response.status_code == 201 else None

    def post_catalogue_item_and_prerequisites_with_allowed_values(
        self, property_type: str, allowed_values_post_data: dict, property_value: Any
    ) -> None:
        """
        Utility method that posts a catalogue item with a property named 'property' of a given type with a given set of
        allowed values as well as any prerequisite entities (a catalogue category and a manufacturer)

        :param property_type: Type of the property to post.
        :param allowed_values_post_data: Dictionary containing the allowed values data as would be required for an
                                         `AllowedValuesSchema` to be posted with the catalogue category.
        :param property_value: Value of the property to post for the item.
        """
        self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES,
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
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [
                    {"name": "property", "value": property_value},
                ],
            }
        )

    def check_post_catalogue_item_success(self, expected_catalogue_item_get_data: dict) -> None:
        """
        Checks that a prior call to `post_catalogue_item` gave a successful response with the expected data
        returned.

        :param expected_catalogue_item_get_data: Dictionary containing the expected catalogue item data returned as
                                                 would be required for a `CatalogueItemSchema`. Does not need mandatory
                                                 IDs (e.g. manufacturer_id) as they will be to check they are as
                                                 expected.
        """

        assert self._post_response.status_code == 201
        assert self._post_response.json() == self.add_ids_to_expected_catalogue_item_get_data(
            expected_catalogue_item_get_data
        )

    def check_post_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `post_catalogue_item` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"] == detail

    def check_post_catalogue_item_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_catalogue_item` gave a failed response with the expected code and
        pydantic validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category."""

    def test_create_with_only_required_values_provided(self):
        """Test creating a catalogue item with only required values provided."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_non_obsolete_with_all_values_except_properties(self):
        """Test creating a non obsolete catalogue item with all values provided except `properties` and
        those related to being obsolete."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES)

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

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
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

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": "invalid-id",
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422, "The specified replacement catalogue item does not exist"
        )

    def test_create_with_all_properties_defined(self):
        """Test creating a catalogue item with all properties within the catalogue category being defined."""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES)

    def test_create_with_mandatory_properties_only(self):
        """Test creating a catalogue item with only mandatory properties defined."""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY)

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY)

    def test_create_with_mandatory_properties_given_none(self):
        """Test creating a catalogue item when mandatory properties are given a value of `None`."""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
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

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item({**CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY, "properties": []})

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Missing mandatory property with ID: "
            f"'{self.property_name_id_dict[PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE['name']]}'",
        )

    def test_create_with_non_mandatory_properties_given_none(self):
        """Test creating a catalogue item when non-mandatory properties are given a value of `None`."""

        # TODO: Have a post for base catalogue category with properties/manufacturer or something to reduce lines
        # repeated
        self.post_unit(UNIT_POST_DATA_MM)
        # TODO: Should BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES have _MM?
        self.post_catalogue_category(BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [
                    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
                    PROPERTY_DATA_NUMBER_NON_MANDATORY_NONE,
                    PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
                ],
            }
        )

        self.check_post_catalogue_item_success(CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY)

    def test_create_with_string_property_with_invalid_value_type(self):
        """Test creating a catalogue item with an invalid value type for a string property."""

        # TODO: Add utility function just for adding with specific properties?
        self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY],
            }
        )
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [
                    {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY["name"], "value": 42},
                ],
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID "
            f"'{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY['name']]}'. "
            "Expected type: string.",
        )

    def test_create_with_number_property_with_invalid_value_type(self):
        """Test creating a catalogue item with an invalid value type for a number property."""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            }
        )
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [
                    {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT["name"], "value": "42"},
                ],
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID '"
            f"{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT['name']]}"
            "'. Expected type: number.",
        )

    def test_create_with_boolean_property_with_invalid_value_type(self):
        """Test creating a catalogue item with an invalid value type for a boolean property."""

        self.post_catalogue_category(
            {
                **BASE_CATALOGUE_CATEGORY_WITH_PROPERTIES,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY],
            }
        )
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_catalogue_item(
            {
                **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
                "properties": [
                    {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY["name"], "value": "42"},
                ],
            }
        )

        self.check_post_catalogue_item_failed_with_detail(
            422,
            "Invalid value type for property with ID '"
            f"{self.property_name_id_dict[CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']]}"
            "'. Expected type: boolean.",
        )

    def test_create_with_invalid_string_allowed_values_list_value(self):
        """Test creating a catalogue item with an invalid value for a string property with an allowed values list."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, "value2"
        )
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected one of value1.",
        )

    def test_create_with_invalid_string_allowed_values_list_type(self):
        """Test creating a catalogue item with an invalid type for a string property with an allowed values list."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values(
            "string", {"type": "list", "values": ["value1"]}, 42
        )
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value type for property with ID '{self.property_name_id_dict['property']}'. "
            "Expected type: string.",
        )

    def test_create_with_invalid_number_allowed_values_list_value(self):
        """Test creating a catalogue item with an invalid value for a number property with an allowed values list."""

        self.post_catalogue_item_and_prerequisites_with_allowed_values("number", {"type": "list", "values": [1]}, 2)
        self.check_post_catalogue_item_failed_with_detail(
            422,
            f"Invalid value for property with ID '{self.property_name_id_dict['property']}'. Expected one of 1.",
        )

    def test_create_with_invalid_number_allowed_values_list_type(self):
        """Test creating a catalogue item with an invalid type for a number property with an allowed values list."""

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

    _get_response: Response

    def get_catalogue_item(self, catalogue_item_id: str) -> None:
        """
        Gets a catalogue item with the given ID.

        :param catalogue_item_id: ID of the catalogue item to be obtained.
        """

        self._get_response = self.test_client.get(f"/v1/catalogue-items/{catalogue_item_id}")

    def check_get_catalogue_item_success(self, expected_catalogue_item_get_data: dict) -> None:
        """
        Checks that a prior call to `get_catalogue_item` gave a successful response with the expected data returned.

        :param expected_catalogue_item_get_data: Dictionary containing the expected system data returned as would be
                                                 required for a `CatalogueItemSchema`. Does not need mandatory IDs (e.g.
                                                 manufacturer_id) as they will be added automatically to check they are
                                                 as expected.
        """

        assert self._get_response.status_code == 200
        assert self._get_response.json() == self.add_ids_to_expected_catalogue_item_get_data(
            expected_catalogue_item_get_data
        )

    def check_get_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `get_catalogue_item` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a catalogue item."""

    def test_get(self):
        """Test getting a catalogue item."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        catalogue_item_id = self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

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
        Gets a list catalogue items with the given filters.

        :param filters: Filters to use in the request.
        """

        self._get_response = self.test_client.get("/v1/catalogue-items", params=filters)

    def post_test_catalogue_items(self) -> list[dict]:
        """
        Posts two catalogue items each in a separate catalogue category and returns their expected responses when
        returned by the ist endpoint.

        :return: List of dictionaries containing the expected catalogue category data returned from a get endpoint in
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

        :param expected_catalogue_items_get_data: List of dictionaries containing the expected system data
                                                  returned as would be required for `CatalogueItemSchema`'s.
        """

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_catalogue_items_get_data


class TestList(ListDSL):
    """Tests for getting a list of catalogue items."""

    def test_list_with_no_filters(self):
        """
        Test getting a list of all catalogue items with no filters provided.

        Posts two catalogue items in different catalogue categories and expects both to be returned.
        """

        catalogue_items = self.post_test_catalogue_items()
        self.get_catalogue_items(filters={})
        self.check_get_catalogue_items_success(catalogue_items)

    def test_list_with_catalogue_category_id_filter(self):
        """
        Test getting a list of all catalogue items with a `catalogue_category_id` filter provided.

        Posts two catalogue items in different catalogue categories and then filter using the `catalogue_category_id`
        expecting only the second catalogue item to be returned.
        """

        catalogue_items = self.post_test_catalogue_items()
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


# TODO: Update tests


# TODO: Inherit from UpdateDSL
class DeleteDSL(ListDSL):
    """Base class for delete tests."""

    _delete_response: Response

    # TODO: Move into UpdateDSL? (like post_child_item in catalogue category tests - depends if needed there or not)
    def post_child_item(self) -> None:
        """Utility method that posts a child item for the last catalogue item posted."""

        # pylint:disable=fixme
        # TODO: This should be cleaned up in future

        response = self.test_client.post("/v1/systems", json=SYSTEM_POST_A)
        system_id = response.json()["id"]

        response = self.test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
        usage_status_id = response.json()["id"]

        item_post = {
            "is_defective": False,
            "warranty_end_date": "2015-11-15T23:59:59Z",
            "serial_number": "xyz123",
            "delivered_date": "2012-12-05T12:00:00Z",
            "notes": "Test notes",
            "catalogue_item_id": self._post_response.json()["id"],
            "system_id": system_id,
            "usage_status_id": usage_status_id,
            "properties": [],
        }
        self.test_client.post("/v1/items", json=item_post)

    def delete_catalogue_item(self, catalogue_item_id: str) -> None:
        """
        Deletes a catalogue item with the given ID.

        :param catalogue_item_id: ID of the catalogue item to be deleted.
        """

        self._delete_response = self.test_client.delete(f"/v1/catalogue-items/{catalogue_item_id}")

    def check_delete_catalogue_item_success(self) -> None:
        """Checks that a prior call to `delete_catalogue_item` gave a successful response with the expected data
        returned."""

        assert self._delete_response.status_code == 204

    def check_delete_catalogue_item_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_catalogue_item` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._delete_response.status_code == status_code
        assert self._delete_response.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue item."""

    def test_delete(self):
        """Test deleting a catalogue item."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        catalogue_item_id = self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)

        self.delete_catalogue_item(catalogue_item_id)
        self.check_delete_catalogue_item_success()

        self.get_catalogue_item(catalogue_item_id)
        self.check_get_catalogue_item_failed_with_detail(404, "Catalogue item not found")

    def test_delete_with_child_item(self):
        """Test deleting a catalogue category with a child catalogue item."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        catalogue_item_id = self.post_catalogue_item(CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)
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


# # pylint: disable=duplicate-code
# CATALOGUE_CATEGORY_POST_A = {
#     "name": "Category A",
#     "is_leaf": True,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "boolean", "mandatory": True},
#         {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
#     ],
# }
# # pylint: enable=duplicate-code

# CATALOGUE_CATEGORY_POST_B = {
#     "name": "Category B",
#     "is_leaf": True,
#     "properties": [
#         {"name": "Property A", "type": "boolean", "mandatory": True},
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

# CATALOGUE_ITEM_POST_A_EXPECTED = {
#     **CATALOGUE_ITEM_POST_A,
#     **CREATED_MODIFIED_VALUES_EXPECTED,
#     "id": ANY,
#     "cost_to_rework_gbp": None,
#     "days_to_rework": None,
#     "drawing_number": None,
#     "obsolete_reason": None,
#     "obsolete_replacement_catalogue_item_id": None,
#     "notes": None,
#     "properties": [
#         {"name": "Property A", "value": 20, "unit": "mm"},
#         {"name": "Property B", "value": False, "unit": None},
#         {"name": "Property C", "value": "20x15x10", "unit": "cm"},
#     ],
# }

# CATALOGUE_ITEM_POST_B = {
#     "name": "Catalogue Item B",
#     "description": "This is Catalogue Item B",
#     "cost_gbp": 300.00,
#     "cost_to_rework_gbp": 120.99,
#     "days_to_replace": 1.5,
#     "days_to_rework": 3.0,
#     "drawing_number": "789xyz",
#     "is_obsolete": False,
#     "notes": "Some extra information",
#     "properties": [{"name": "Property A", "value": True}],
# }
# # pylint: enable=duplicate-code

# CATALOGUE_ITEM_POST_B_EXPECTED = {
#     **CATALOGUE_ITEM_POST_B,
#     **CREATED_MODIFIED_VALUES_EXPECTED,
#     "id": ANY,
#     "drawing_link": None,
#     "item_model_number": None,
#     "obsolete_reason": None,
#     "obsolete_replacement_catalogue_item_id": None,
#     "properties": [{"name": "Property A", "value": True, "unit": None}],
# }

# def test_partial_update_catalogue_item_when_no_child_items(test_client):
#     """
#     Test changing the name and description of a catalogue item when it doesn't have any child
#     items
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         **catalogue_item_patch,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_when_has_child_items(test_client):
#     """
#     Test updating a catalogue item which has child items.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         **catalogue_item_patch,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_invalid_id(test_client):
#     """
#     Test updating a catalogue item with an invalid ID.
#     """
#     catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}

#     response = test_client.patch("/v1/catalogue-items/invalid", json=catalogue_item_patch)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Catalogue item not found"


# def test_partial_update_catalogue_item_non_existent_id(test_client):
#     """
#     Test updating a catalogue item with a non-existent ID.
#     """
#     catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}

#     response = test_client.patch(f"/v1/catalogue-items/{str(ObjectId())}", json=catalogue_item_patch)

#     assert response.status_code == 404
#     assert response.json()["detail"] == "Catalogue item not found"


# def test_partial_update_catalogue_item_change_catalogue_category_id(test_client):
#     """
#     Test moving a catalogue item to another catalogue category with the same properties without
#     specifying any new properties.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     catalogue_category_b = _post_catalogue_category_with_units(
#         test_client,
#         {
#             **CATALOGUE_CATEGORY_POST_B,
#             "properties": CATALOGUE_CATEGORY_POST_A["properties"],
#         },
#     )
#     # pylint: enable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "catalogue_category_id": catalogue_category_b["id"],
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category_b["properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_change_catalogue_category_id_without_properties(test_client):
#     """
#     Test moving a catalogue item to another catalogue category without supplying any properties.
#     """
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {"catalogue_category_id": catalogue_category_b_id}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     assert (
#         response.json()["detail"]
#         == "Cannot move catalogue item to a category with different properties without specifying the "
#         "new properties"
#     )


# def test_partial_update_catalogue_item_change_catalogue_category_id_with_properties(test_client):
#     """
#     Test moving a catalogue item to another catalogue category while supplying any new properties.
#     """
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "catalogue_category_id": catalogue_category_b["id"],
#         "properties": add_ids_to_properties(catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_change_catalogue_category_id_with_different_properties_order(test_client):
#     """
#     Test moving a catalogue item to another catalogue category with the same properties but in a different order
#     without supplying the new properties.
#     """
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     catalogue_category_b = _post_catalogue_category_with_units(
#         test_client,
#         {
#             **CATALOGUE_CATEGORY_POST_B,
#             "properties": CATALOGUE_CATEGORY_POST_A["properties"][::-1],
#         },
#     )

#     catalogue_category_b_id = catalogue_category_b["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {"catalogue_category_id": catalogue_category_b_id}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     assert (
#         response.json()["detail"]
#         == "Cannot move catalogue item to a category with different properties without specifying the "
#         "new properties"
#     )


# def test_partial_update_catalogue_item_change_catalogue_category_id_missing_mandatory_properties(test_client):
#     """
#     Test moving a catalogue item to another catalogue category with missing mandatory properties.
#     """
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "catalogue_category_id": catalogue_category_a["id"],
#         "properties": add_ids_to_properties(
#             catalogue_category_a["properties"], [CATALOGUE_ITEM_POST_B["properties"][0]]
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     prop_id = catalogue_category_a["properties"][1]["id"]
#     assert response.json()["detail"] == f"Missing mandatory property with ID: '{prop_id}'"


# def test_partial_update_catalogue_item_change_catalogue_category_id_missing_non_mandatory_properties(test_client):
#     """
#     Test moving a catalogue item to another catalogue category with missing non-mandatory properties.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b = response.json()
#     # pylint: enable=duplicate-code

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "catalogue_category_id": catalogue_category_a["id"],
#         "properties": add_ids_to_properties(
#             catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"][-2:]
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_B_EXPECTED,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category_a["properties"],
#             [{"name": "Property A", "unit": "mm", "value": None}, *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:]],
#         ),
#     }


# def test_partial_update_catalogue_item_change_catalogue_category_id_invalid_id(test_client):
#     """
#     Test changing the catalogue category ID of a catalogue item to an invalid ID.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "catalogue_category_id": "invalid",
#         "properties": add_ids_to_properties(None, [CATALOGUE_ITEM_POST_A["properties"][0]]),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified catalogue category does not exist"


# def test_partial_update_catalogue_item_change_catalogue_category_id_non_existent_id(test_client):
#     """
#     Test changing the catalogue category ID of a catalogue item to a non-existent ID.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "catalogue_category_id": str(ObjectId()),
#         "properties": add_ids_to_properties(None, [CATALOGUE_ITEM_POST_A["properties"][0]]),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified catalogue category does not exist"


# def test_partial_update_catalogue_item_change_catalogue_category_id_non_leaf_catalogue_category(test_client):
#     """
#     Test moving a catalogue item to a non-leaf catalogue category.
#     """
#     catalogue_category_post_a = {"name": "Category A", "is_leaf": False}
#     response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post_a)
#     catalogue_category_a_id = response.json()["id"]
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {"catalogue_category_id": catalogue_category_a_id}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


# def test_partial_update_catalogue_item_change_catalogue_category_id_has_child_items(test_client):
#     """
#     Test moving a catalogue item with child items to another catalogue category.
#     """
#     # pylint: disable=duplicate-code
#     # Parent
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b = response.json()

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     catalogue_item_patch = {
#         "catalogue_category_id": catalogue_category_b["id"],
#         "properties": add_ids_to_properties(catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]
#     # child
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], ITEM_POST["properties"]),
#     }
#     test_client.post("/v1/items", json=item_post)

#     response = test_client.patch(f"/v1/catalogue-items/{catalogue_item_id}", json=catalogue_item_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


# def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id(test_client):
#     """
#     Test updating a catalogue item with an obsolete replacement catalogue item ID.
#     """
#     catalogue_category_a = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category_b = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post_a = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category_a["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_a["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)
#     catalogue_item_a_id = response.json()["id"]

#     catalogue_item_post_b = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

#     catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": catalogue_item_a_id}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_B_EXPECTED,
#         "catalogue_category_id": catalogue_category_b["id"],
#         "manufacturer_id": manufacturer_id,
#         "is_obsolete": True,
#         "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
#         "properties": add_ids_to_properties(
#             catalogue_category_b["properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id_invalid_id(test_client):
#     """
#     Test updating a catalogue item with an invalid obsolete replacement catalogue item ID.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": "invalid"}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified replacement catalogue item does not exist"


# def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id_non_existent_id(test_client):
#     """
#     Test updating a catalogue item with aa non-existent obsolete replacement catalogue item ID.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": str(ObjectId())}
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified replacement catalogue item does not exist"


# def test_partial_update_catalogue_item_with_mandatory_properties_given_none(test_client):
#     """
#     Test updating a catalogue item's mandatory properties to have a value of None
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 CATALOGUE_ITEM_POST_A["properties"][0],
#                 {**CATALOGUE_ITEM_POST_A["properties"][1], "value": None},
#                 {**CATALOGUE_ITEM_POST_A["properties"][2], "value": None},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.json()["detail"] == f"Mandatory property with ID '{prop_id}' cannot be None."
#     # pylint: enable=duplicate-code


# def test_partial_update_catalogue_item_with_non_mandatory_properties_given_none(test_client):
#     """
#     Test updating a catalogue item's non-mandatory properties to have a value of None
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{**CATALOGUE_ITEM_POST_A["properties"][0], "value": None}, *CATALOGUE_ITEM_POST_A["properties"][1:]],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200
#     catalogue_item = response.json()
#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {**CATALOGUE_ITEM_POST_A_EXPECTED["properties"][0], "value": None},
#                 *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][1:],
#             ],
#         ),
#     }


# def test_partial_update_catalogue_item_add_non_mandatory_property(test_client):
#     """
#     Test adding a non-mandatory property and a value.
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"][-2:]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"])
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_remove_non_mandatory_property(test_client):
#     """
#     Test removing a non-mandatory property and its value..
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"][-2:])
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_A_EXPECTED,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "unit": "mm", "value": None}, *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:]],
#         ),
#     }


# def test_partial_update_catalogue_item_remove_mandatory_property(test_client):
#     """
#     Test removing a mandatory property and its value.
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [CATALOGUE_ITEM_POST_A["properties"][0], CATALOGUE_ITEM_POST_A["properties"][2]],
#         )
#     }

#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.status_code == 422
#     assert response.json()["detail"] == f"Missing mandatory property with ID: '{prop_id}'"


# def test_partial_update_catalogue_item_change_value_for_string_property_invalid_type(test_client):
#     """
#     Test changing the value of a string property to an invalid type.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": 20},
#                 {"name": "Property B", "value": False},
#                 {"name": "Property C", "value": True},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][2]["id"]
#     assert response.json()["detail"] == f"Invalid value type for property with ID '{prop_id}'. Expected type: string."
#     # pylint: enable=duplicate-code


# def test_partial_update_catalogue_item_change_value_for_number_property_invalid_type(test_client):
#     """
#     Test changing the value of a number property to an invalid type.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": "20"},
#                 {"name": "Property B", "value": False},
#                 {"name": "Property C", "value": "20x15x10"},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][0]["id"]
#     assert response.json()["detail"] == f"Invalid value type for property with ID '{prop_id}'. Expected type: number."


# def test_partial_update_catalogue_item_change_value_for_boolean_property_invalid_type(test_client):
#     """
#     Test changing the value of a boolean property to an invalid type.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [
#                 {"name": "Property A", "value": 20},
#                 {"name": "Property B", "value": "False"},
#                 {"name": "Property C", "value": "20x15x10"},
#             ],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.json()["detail"] == f"Invalid value type for property with ID '{prop_id}'. Expected type: boolean."
#     # pylint: enable=duplicate-code


# def test_partial_update_catalogue_item_change_values_with_allowed_values(test_client):
#     """
#     Test changing the value of properties with allowed_values defined
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "value": 6}, {"name": "Property B", "value": "green"}],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "unit": "mm", "value": 6}, {"name": "Property B", "unit": None, "value": "green"}],
#         ),
#     }


# def test_partial_update_catalogue_item_change_value_for_invalid_allowed_values_list_string(test_client):
#     """
#     Test updating a catalogue item when giving a string property a value that is not within
#     the defined allowed_values list
#     """

#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "value": 4}, {"name": "Property B", "value": "blue"}],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][1]["id"]
#     assert response.json()["detail"] == f"Invalid value for property with ID '{prop_id}'. Expected one of red, green."
#     # pylint: enable=duplicate-code


# def test_partial_update_catalogue_item_change_value_for_invalid_allowed_values_list_number(test_client):
#     """
#     Test updating a catalogue item when giving a number property a value that is not within
#     the defined allowed_values list
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
#         ),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"],
#             [{"name": "Property A", "value": 10}, {"name": "Property B", "value": "green"}],
#         ),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     # pylint: disable=duplicate-code
#     assert response.status_code == 422
#     prop_id = catalogue_category["properties"][0]["id"]
#     assert response.json()["detail"] == f"Invalid value for property with ID '{prop_id}'. Expected one of 2, 4, 6."
#     # pylint: enable=duplicate-code


# def test_partial_update_properties_when_has_child_items(test_client):
#     """
#     Test updating the properties of a catalogue item when it has child items.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_d_id = response.json()["id"]

#     manufacturer_e_post = {
#         **MANUFACTURER,
#         "name": "Manufacturer E",
#     }
#     response = test_client.post("/v1/manufacturers", json=manufacturer_e_post)
#     manufacturer_e_id = response.json()["id"]

#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_B)
#     usage_status_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_d_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]
#     # Child
#     # pylint: disable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     test_client.post("/v1/items", json=item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "manufacturer_id": manufacturer_e_id,
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


# def test_partial_update_catalogue_item_change_manufacturer_id_when_no_child_items(test_client):
#     """
#     Test updating the manufacturer ID of a catalogue item when it doesn't have any child items.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_d_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     manufacturer_e_post = {
#         "name": "Manufacturer E",
#         "url": "http://example.com/",
#         "address": {
#             "address_line": "2 Example Street",
#             "town": "Oxford",
#             "county": "Oxfordshire",
#             "country": "United Kingdom",
#             "postcode": "OX1 2AB",
#         },
#         "telephone": "07384723948",
#     }
#     # pylint: enable=duplicate-code
#     response = test_client.post("/v1/manufacturers", json=manufacturer_e_post)
#     manufacturer_e_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_d_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "manufacturer_id": manufacturer_e_id,
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 200

#     catalogue_item = response.json()

#     assert catalogue_item == {
#         **CATALOGUE_ITEM_POST_B_EXPECTED,
#         **catalogue_item_patch,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_e_id,
#         "properties": add_ids_to_properties(
#             catalogue_category["properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
#         ),
#     }


# def test_partial_update_catalogue_item_change_manufacturer_id_when_has_child_items(test_client):
#     """
#     Test updating the manufacturer ID of a catalogue item when it has child items.
#     """
#     catalogue_category = _post_catalogue_category_with_units(test_client, CATALOGUE_CATEGORY_POST_A)

#     response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
#     system_id = response.json()["id"]

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
#     usage_status_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_A,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     # pylint: enable=duplicate-code
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
#     catalogue_item_id = response.json()["id"]

#     # pylint: disable=duplicate-code
#     # Child
#     # pylint: disable=duplicate-code
#     item_post = {
#         **ITEM_POST,
#         "catalogue_item_id": catalogue_item_id,
#         "system_id": system_id,
#         "usage_status_id": usage_status_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
#     }
#     test_client.post("/v1/items", json=item_post)
#     # pylint: enable=duplicate-code

#     catalogue_item_patch = {
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 409
#     assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


# def test_partial_update_catalogue_item_change_manufacturer_id_invalid_id(test_client):
#     """
#     Test changing the manufacturer ID of a catalogue item to an invalid ID.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "manufacturer_id": "invalid",
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified manufacturer does not exist"


# def test_partial_update_catalogue_item_change_manufacturer_id_non_existent_id(test_client):
#     """
#     Test changing the manufacturer ID of a catalogue item to a non-existent ID.
#     """
#     response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
#     catalogue_category = response.json()

#     response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
#     manufacturer_id = response.json()["id"]

#     catalogue_item_post = {
#         **CATALOGUE_ITEM_POST_B,
#         "catalogue_category_id": catalogue_category["id"],
#         "manufacturer_id": manufacturer_id,
#         "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_B["properties"]),
#     }
#     response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

#     catalogue_item_patch = {
#         "manufacturer_id": str(ObjectId()),
#     }
#     response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

#     assert response.status_code == 422
#     assert response.json()["detail"] == "The specified manufacturer does not exist"
