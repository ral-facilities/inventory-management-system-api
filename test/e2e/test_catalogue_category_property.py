"""
End-to-End tests for the properties endpoint of the catalogue category router
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-ancestors

from test.e2e.conftest import E2ETestHelpers
from test.e2e.test_catalogue_category import GetDSL as CatalogueCategoryGetDSL
from test.e2e.test_catalogue_item import GetDSL as CatalogueItemGetDSL
from test.e2e.test_item import GetDSL as ItemGetDSL
from test.mock_data import (
    BASE_CATALOGUE_CATEGORY_GET_DATA_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_GET_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_GET_DATA_STRING_MANDATORY,
    CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
    ITEM_GET_DATA_WITH_ALL_PROPERTIES,
    PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE,
    PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1,
    PROPERTY_DATA_STRING_MANDATORY_TEXT,
    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_NONE,
    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
    PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE,
    PROPERTY_GET_DATA_STRING_MANDATORY_TEXT,
)
from typing import Optional

from bson import ObjectId
from fastapi import Response


class CreateDSL(ItemGetDSL, CatalogueCategoryGetDSL, CatalogueItemGetDSL):
    """Base class for create tests."""

    item_id: Optional[str]

    _post_response_property: Response
    _existing_catalogue_category_properties: list[dict]

    def post_test_item_and_prerequisites(self) -> None:
        """Posts an item for testing having first posted the required prerequisite entities. The item posted
        starts with a single property already defined."""

        self.item_id = self.post_item_and_prerequisites_with_given_properties(
            [CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY],
            [PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE],
            [PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE],
        )
        self._existing_catalogue_category_properties = self._post_response_catalogue_category.json()["properties"]

    def post_property(self, property_data: dict) -> Optional[str]:
        """Posts a property to a catalogue category.

        :param property_data: Dictionary containing the basic catalogue category property data data as would be required
                              for a `CatalogueCategoryPropertyPostSchema` but with any `unit_id`'s replaced by the
                              `unit` value in its properties as the IDs will be added automatically.
        :return: ID of the created property (or `None` if not successful).
        """

        # First need to replace all unit values with unit IDs
        full_property_data = property_data.copy()
        full_property_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            {"properties": [full_property_data]}, self.unit_value_id_dict
        )["properties"][0]

        self._post_response_property = self.test_client.post(
            "/v1/catalogue-categories/" f"{self.catalogue_category_id}/properties", json=full_property_data
        )

        property_id = (
            self._post_response_property.json()["id"] if self._post_response_property.status_code == 201 else None
        )

        # Append to the property name id dict for the new property
        if property_id:
            property_data = self._post_response_property.json()
            self.property_name_id_dict[property_data["name"]] = property_data["id"]
            self._unit_data_lookup_dict[property_data["id"]] = {
                "unit_id": property_data["unit_id"],
                "unit": property_data["unit"],
            }

        return property_id

    def post_property_with_allowed_values(self, property_type: str, allowed_values_post_data: dict) -> None:
        """
        Utility method that posts property named 'property' of a given type with a given set of allowed values.

        :param property_type: Type of the property to post.
        :param allowed_values_post_data: Dictionary containing the allowed values data as would be required for an
                                         `AllowedValuesSchema`.
        """

        self.post_property(
            {
                "name": "property",
                "type": property_type,
                "mandatory": False,
                "allowed_values": allowed_values_post_data,
            }
        )

    def check_post_property_success(self, expected_property_get_data: dict) -> None:
        """
        Checks that a prior call to `post_property` gave a successful response with the expected data returned.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `CatalogueCategoryPropertySchema` but with any `unit_id`'s
                                           replaced by the `unit` value in its properties as the IDs will be added
                                           automatically.
        """

        assert self._post_response_property.status_code == 201
        assert (
            self._post_response_property.json()
            == E2ETestHelpers.add_unit_ids_to_properties(
                {"properties": [expected_property_get_data]}, self.unit_value_id_dict
            )["properties"][0]
        )

    def check_post_property_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `post_property` gave a failed response with the expected code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._post_response_property.status_code == status_code
        assert self._post_response_property.json()["detail"] == detail

    def check_post_property_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_property` gave a failed response with the expected code and pydantic
        validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._post_response_property.status_code == status_code
        assert self._post_response_property.json()["detail"][0]["msg"] == message

    def check_catalogue_category_updated(self, expected_property_get_data: dict) -> None:
        """Checks the catalogue category is updated correctly with the new property.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `CatalogueCategoryPropertySchema` but with any `unit_id`'s
                                           replaced by the `unit` value in its properties as the IDs will be added
                                           automatically.
        """

        self.get_catalogue_category(self.catalogue_category_id)
        self.check_get_catalogue_category_success(
            {
                **BASE_CATALOGUE_CATEGORY_GET_DATA_WITH_PROPERTIES_MM,
                "properties": [
                    CATALOGUE_CATEGORY_PROPERTY_GET_DATA_BOOLEAN_MANDATORY,
                    expected_property_get_data,
                ],
            }
        )
        E2ETestHelpers.check_created_and_modified_times_updated_correctly(
            self._post_response_catalogue_category, self._get_response_catalogue_category
        )

    def check_catalogue_item_updated(self, expected_property_get_data: dict) -> None:
        """Checks the catalogue item is updated correctly with the new property.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `PropertySchema`. Does not need mandatory IDs
                                           (e.g. property/unit IDs) as they will be added automatically to check they
                                           are as expected.
        """

        self.get_catalogue_item(self.catalogue_item_id)
        self.check_get_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE, expected_property_get_data],
            }
        )
        E2ETestHelpers.check_created_and_modified_times_updated_correctly(
            self._post_response_catalogue_item, self._get_response_catalogue_item
        )

    def check_item_updated(self, expected_property_get_data: dict) -> None:
        """Checks the item is updated correctly with the new property.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `PropertySchema`. Does not need mandatory IDs
                                           (e.g. property/unit IDs) as they will be added automatically to check they
                                           are as expected.
        """

        self.get_item(self.item_id)
        self.check_get_item_success(
            {
                **ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [
                    PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE,
                    expected_property_get_data,
                ],
            }
        )
        E2ETestHelpers.check_created_and_modified_times_updated_correctly(
            self._post_response_item, self._get_response_item
        )


class TestCreate(CreateDSL):
    """Tests for creating a property at the catalogue category level."""

    def test_create_non_mandatory(self):
        """Test creating a non mandatory property."""

        self.post_test_item_and_prerequisites()
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.check_post_property_success(CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY)
        self.check_catalogue_category_updated(CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY)
        self.check_catalogue_item_updated(PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_NONE)
        self.check_item_updated(PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_NONE)

    def test_create_non_mandatory_with_unit(self):
        """Test creating a non mandatory property with a unit."""

        self.post_test_item_and_prerequisites()
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)

        self.check_post_property_success(CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.check_catalogue_category_updated(CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.check_catalogue_item_updated(PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE)
        self.check_item_updated(PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE)

    def test_create_mandatory(self):
        """Test creating a mandatory property."""

        self.post_test_item_and_prerequisites()
        self.post_property(
            {
                **CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY,
                "default_value": PROPERTY_DATA_STRING_MANDATORY_TEXT["value"],
            }
        )

        self.check_post_property_success(CATALOGUE_CATEGORY_PROPERTY_GET_DATA_STRING_MANDATORY)
        self.check_catalogue_category_updated(CATALOGUE_CATEGORY_PROPERTY_GET_DATA_STRING_MANDATORY)
        self.check_catalogue_item_updated(PROPERTY_GET_DATA_STRING_MANDATORY_TEXT)
        self.check_item_updated(PROPERTY_GET_DATA_STRING_MANDATORY_TEXT)

    def test_create_mandatory_with_boolean_int_default_value(self):
        """Test creating a mandatory property with a default value that is a boolean value while the type of the
        property is an int (this can cause an issue if not implemented property as boolean is a subclass of int
        - technically also applies to other endpoints' type checks but they occur in the same place in code anyway).
        """

        self.post_test_item_and_prerequisites()
        self.post_property({**CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_MANDATORY, "default_value": True})

        self.check_post_property_failed_with_validation_message(
            422, "Value error, default_value must be the same type as the property itself"
        )

    def test_create_mandatory_without_default_value(self):
        """Test creating a mandatory property without a default value."""

        self.post_test_item_and_prerequisites()
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY)

        self.check_post_property_failed_with_detail(422, "Cannot add a mandatory property without a default value")

    def test_create_with_allowed_values_list(self):
        """Test creating a property with an allowed values list."""

        self.post_test_item_and_prerequisites()
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST)

        self.check_post_property_success(
            CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
        )
        self.check_catalogue_category_updated(
            CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
        )
        self.check_catalogue_item_updated(
            {**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1, "value": None}
        )
        self.check_item_updated({**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1, "value": None})

    def test_create_with_allowed_values_list_with_invalid_default_value_not_in_list(self):
        """Test creating a property with an allowed values list with a default value that is not present in that
        list."""

        self.post_test_item_and_prerequisites()
        self.post_property(
            {**CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST, "default_value": 9001}
        )

        self.check_post_property_failed_with_validation_message(
            422, "Value error, default_value is not one of the allowed_values"
        )

    def test_create_with_allowed_values_list_with_invalid_default_value_type(self):
        """Test creating a property with an allowed values list with a default value that has an incorrect type."""

        self.post_test_item_and_prerequisites()
        self.post_property(
            {**CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST, "default_value": False}
        )

        self.check_post_property_failed_with_validation_message(
            422, "Value error, default_value must be the same type as the property itself"
        )

    def test_create_with_invalid_allowed_values_type(self):
        """Test creating a string property with an invalid allowed values type."""

        self.post_property_with_allowed_values("string", {"type": "invalid-type"})

        self.check_post_property_failed_with_validation_message(
            422,
            "Input tag 'invalid-type' found using 'type' does not match any of the expected tags: 'list'",
        )

    def test_create_with_empty_allowed_values_list(self):
        """Test creating a string property with an empty allowed values list."""

        self.post_property_with_allowed_values("string", {"type": "list", "values": []})

        self.check_post_property_failed_with_validation_message(
            422,
            "List should have at least 1 item after validation, not 0",
        )

    def test_create_string_with_allowed_values_list_with_invalid_value(self):
        """Test creating a string property with an allowed values list containing an invalid string value."""

        self.post_property_with_allowed_values("string", {"type": "list", "values": ["1", "2", 3, "4"]})

        self.check_post_property_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_create_string_with_allowed_values_list_with_duplicate_value(self):
        """Test creating a string property with an allowed values list containing a duplicate string value."""

        self.post_property_with_allowed_values(
            "string", {"type": "list", "values": ["value1", "value2", "Value1", "value3"]}
        )

        self.check_post_property_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: Value1",
        )

    def test_create_number_with_allowed_values_list_with_invalid_value(self):
        """Test creating a number property with an allowed values list containing an invalid number value."""

        self.post_property_with_allowed_values("number", {"type": "list", "values": [1, 2, "3", 4]})

        self.check_post_property_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' must only contain values of the same type as the property "
            "itself",
        )

    def test_create_number_with_allowed_values_list_with_duplicate_value(self):
        """Test creating a number property with an allowed values list containing a duplicate number value."""

        self.post_property_with_allowed_values("number", {"type": "list", "values": [1, 2, 1, 3]})

        self.check_post_property_failed_with_validation_message(
            422,
            "Value error, allowed_values of type 'list' contains a duplicate value: 1",
        )

    def test_create_boolean_with_allowed_values_list(self):
        """Test creating a boolean property with an allowed values list."""

        self.post_property_with_allowed_values("boolean", {"type": "list", "values": [True, False]})

        self.check_post_property_failed_with_validation_message(
            422,
            "Value error, allowed_values not allowed for a boolean property 'property'",
        )

    def test_create_with_non_existent_catalogue_category_id(self):
        """Test creating a property with a non-existent catalogue item ID."""

        self.catalogue_item_id = str(ObjectId())
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.check_post_property_failed_with_detail(404, "Catalogue category not found")

    def test_create_with_invalid_catalogue_category_id(self):
        """Test creating a property with an invalid catalogue item ID."""

        self.catalogue_item_id = "invalid-id"
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.check_post_property_failed_with_detail(404, "Catalogue category not found")

    def test_create_with_non_existent_unit_id(self):
        """Test creating a property with a non-existent unit ID."""

        self.post_test_item_and_prerequisites()
        self.set_unit_value_and_id("mm", str(ObjectId()))
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)

        self.check_post_property_failed_with_detail(422, "The specified unit does not exist")

    def test_create_with_invalid_unit_id(self):
        """Test creating a property with an invalid unit ID."""

        self.post_test_item_and_prerequisites()
        self.set_unit_value_and_id("mm", "invalid_id")
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)

        self.check_post_property_failed_with_detail(422, "The specified unit does not exist")

    def test_create_with_non_leaf_catalogue_category(self):
        """Test creating a property within a non-leaf catalogue category."""

        self.post_catalogue_category(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY)
        self.post_property(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.check_post_property_failed_with_detail(422, "Cannot add a property to a non-leaf catalogue category")

    def test_create_with_duplicate_name(self):
        """Test creating a property within with the same name as an existing one."""

        self.post_test_item_and_prerequisites()
        self.post_property({**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "default_value": False})

        self.check_post_property_failed_with_detail(
            422, f"Duplicate property name: {CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']}"
        )


class UpdateDSL(CreateDSL):
    """Base class for update tests."""

    _patch_response_property: Response

    def post_test_property_and_prerequisites(self, property_data: dict) -> Optional[str]:
        """Posts an property for testing having first posted the required prerequisite entities.

        :param property_data: Dictionary containing the basic catalogue category property data data as would be required
                              for a `CatalogueCategoryPropertyPostSchema` but with any `unit_id`'s replaced by the
                              `unit` value in its properties as the IDs will be added automatically.
        :return: ID of the created property (or `None` if not successful).
        """

        # Add in property at the start rather than following a post so created & modified times are accurate to before
        # any patch is done during update tests
        self.item_id = self.post_item_and_prerequisites_with_given_properties(
            [CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, property_data],
            [PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE, property_data],
            [PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE, property_data],
        )
        self._existing_catalogue_category_properties = self._post_response_catalogue_category.json()["properties"]

        return self._existing_catalogue_category_properties[1]["id"]

    def post_test_property_and_prerequisites_with_allowed_values_list(self) -> tuple[Optional[str], dict]:
        """Posts an property for testing having first posted the required prerequisite entities.

        :return: Tuple with
            - ID of the created property (or `None` if not successful).
            - Dictionary of the `allowed_values` data used in the creation of the property
        """

        return (
            self.post_test_property_and_prerequisites(
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
            ),
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST["allowed_values"],
        )

    def patch_property(self, property_id: str, property_update_data: dict) -> None:
        """
        Updates an property with the given ID.

        :param property_id: ID of the property to patch.
        :param property_update_data: Dictionary containing the basic catalogue category property data data as would be
                                     required for a `CatalogueCategoryPropertyPatchSchema`.
        """

        # Ensure the property ID is updated and the old one removed
        if "name" in property_update_data:
            self.property_name_id_dict = {
                key: value for key, value in self.property_name_id_dict.items() if value != property_id
            }
            self.property_name_id_dict[property_update_data["name"]] = property_id

        self._patch_response_property = self.test_client.patch(
            f"/v1/catalogue-categories/{self.catalogue_category_id}/properties/{property_id}", json=property_update_data
        )

    def check_patch_property_success(self, expected_property_get_data: dict) -> None:
        """
        Checks that a prior call to `patch_property` gave a successful response with the expected data returned.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `CatalogueCategoryPropertySchema` but with any `unit_id`'s
                                           replaced by the `unit` value in its properties as the IDs will be added
                                           automatically.
        """

        assert self._patch_response_property.status_code == 200
        assert (
            self._patch_response_property.json()
            == E2ETestHelpers.add_unit_ids_to_properties(
                {"properties": [expected_property_get_data]}, self.unit_value_id_dict
            )["properties"][0]
        )

    def check_patch_property_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `patch_property` gave a failed response with the expected code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._patch_response_property.status_code == status_code
        assert self._patch_response_property.json()["detail"] == detail

    def check_catalogue_item_not_updated(self, expected_property_get_data: dict) -> None:
        """Checks the catalogue item has not been updated.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `PropertySchema`. Does not need mandatory IDs
                                           (e.g. property/unit IDs) as they will be added automatically to check they
                                           are as expected.
        """

        self.get_catalogue_item(self.catalogue_item_id)
        self.check_get_catalogue_item_success(
            {
                **CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE, expected_property_get_data],
            }
        )
        E2ETestHelpers.check_created_and_modified_times_not_updated(
            self._post_response_catalogue_item, self._get_response_catalogue_item
        )

    def check_item_not_updated(self, expected_property_get_data: dict) -> None:
        """Checks the catalogue item has not been updated.

        :param expected_property_get_data: Dictionary containing the expected property data returned as would be
                                           required for a `PropertySchema`. Does not need mandatory IDs
                                           (e.g. property/unit IDs) as they will be added automatically to check they
                                           are as expected.
        """

        self.get_item(self.item_id)
        self.check_get_item_success(
            {
                **ITEM_GET_DATA_WITH_ALL_PROPERTIES,
                "properties": [
                    PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE,
                    expected_property_get_data,
                ],
            }
        )
        E2ETestHelpers.check_created_and_modified_times_not_updated(self._post_response_item, self._get_response_item)


class TestUpdate(UpdateDSL):
    """Tests for updating a property at the catalogue category level."""

    def test_partial_update_name(self):
        """Test updating the name of a property."""

        property_id = self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        property_update_data = {"name": "New property name"}
        self.patch_property(property_id, property_update_data)

        self.check_patch_property_success(
            {**CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY, **property_update_data}
        )
        self.check_catalogue_category_updated(
            {**CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY, **property_update_data}
        )
        self.check_catalogue_item_updated({**PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_NONE, **property_update_data})
        self.check_item_updated({**PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_NONE, **property_update_data})

    def test_partial_update_name_to_duplicate(self):
        """Test updating the name of a property to conflict with a pre-existing one."""

        property_id = self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.patch_property(property_id, {"name": CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY["name"]})

        self.check_patch_property_failed_with_detail(
            422, f"Duplicate property name: {CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY['name']}"
        )

    def test_update_allowed_values_list_adding_value(self):
        """Test updating the allowed values list of a property by adding an additional value to it."""

        property_id, existing_allowed_values = self.post_test_property_and_prerequisites_with_allowed_values_list()

        property_update_data = {
            "allowed_values": {**existing_allowed_values, "values": [*existing_allowed_values["values"], 9001]}
        }
        self.patch_property(property_id, property_update_data)

        self.check_patch_property_success(
            {
                **CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
                **property_update_data,
            }
        )
        self.check_catalogue_category_updated(
            {
                **CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
                **property_update_data,
            }
        )
        self.check_catalogue_item_not_updated(PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE)
        self.check_item_not_updated(PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE)

    def test_update_allowed_values_list_adding_value_with_different_type(self):
        """Test updating the allowed values list of a property by adding an additional value with a different type to
        it."""

        property_id, existing_allowed_values = self.post_test_property_and_prerequisites_with_allowed_values_list()

        self.patch_property(
            property_id,
            {"allowed_values": {**existing_allowed_values, "values": [*existing_allowed_values["values"], True]}},
        )

        self.check_patch_property_failed_with_detail(
            422, "allowed_values of type 'list' must only contain values of the same type as the property itself"
        )

    def test_update_allowed_values_list_adding_duplicate_value(self):
        """Test updating the allowed values list of a property by adding a duplicate value to it."""

        property_id, existing_allowed_values = self.post_test_property_and_prerequisites_with_allowed_values_list()

        self.patch_property(
            property_id,
            {
                "allowed_values": {
                    **existing_allowed_values,
                    "values": [*existing_allowed_values["values"], existing_allowed_values["values"][0]],
                }
            },
        )

        self.check_patch_property_failed_with_detail(
            422, f"allowed_values of type 'list' contains a duplicate value: {existing_allowed_values['values'][0]}"
        )

    def test_update_allowed_values_list_removing_value(self):
        """Test updating the allowed values list of a property by removing a value from it."""

        property_id, existing_allowed_values = self.post_test_property_and_prerequisites_with_allowed_values_list()

        self.patch_property(
            property_id,
            {
                "allowed_values": {
                    **existing_allowed_values,
                    "values": [*existing_allowed_values["values"][1:]],
                }
            },
        )

        self.check_patch_property_failed_with_detail(
            422, "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
        )

    def test_update_allowed_values_list_modifying_value(self):
        """Test updating the allowed values list of a property by modifying a value within it."""

        property_id, existing_allowed_values = self.post_test_property_and_prerequisites_with_allowed_values_list()

        self.patch_property(
            property_id,
            {
                "allowed_values": {
                    **existing_allowed_values,
                    "values": [
                        9001,
                        *existing_allowed_values["values"][1:],
                    ],
                }
            },
        )

        self.check_patch_property_failed_with_detail(
            422, "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
        )

    def test_update_allowed_values_from_none_to_value(self):
        """Test updating the allowed values of a property from None to a value."""

        property_id = self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.patch_property(
            property_id,
            {
                "allowed_values": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST[
                    "allowed_values"
                ],
            },
        )

        self.check_patch_property_failed_with_detail(422, "Cannot add allowed_values to an existing property")

    def test_update_allowed_values_from_value_to_none(self):
        """Test updating the allowed values list of a property."""

        property_id = self.post_test_property_and_prerequisites(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
        )

        self.patch_property(property_id, {"allowed_values": None})

        self.check_patch_property_failed_with_detail(422, "Cannot remove allowed_values from an existing property")

    def test_partial_update_with_non_existent_catalogue_category_id(self):
        """Test updating a property in a non-existent catalogue category."""

        property_id = self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)
        self.catalogue_category_id = str(ObjectId())

        self.patch_property(property_id, {})

        self.check_patch_property_failed_with_detail(404, "Catalogue category not found")

    def test_partial_update_with_catalogue_category_invalid_id(self):
        """Test updating a property with an invalid ID."""

        property_id = self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)
        self.catalogue_category_id = "invalid-id"

        self.patch_property(property_id, {})

        self.check_patch_property_failed_with_detail(404, "Catalogue category not found")

    def test_partial_update_with_non_existent_property_id(self):
        """Test updating a non-existent property."""

        self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.patch_property(str(ObjectId()), {})

        self.check_patch_property_failed_with_detail(404, "Catalogue category property not found")

    def test_partial_update_with_invalid_property_id(self):
        """Test updating a property with an invalid ID."""

        self.post_test_property_and_prerequisites(CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY)

        self.patch_property("invalid-id", {})

        self.check_patch_property_failed_with_detail(404, "Catalogue category property not found")
