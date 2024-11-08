"""
End-to-End tests for the properties endpoint of the catalogue category router
"""

from test.conftest import add_ids_to_properties
from test.e2e.conftest import E2ETestHelpers, replace_unit_values_with_ids_in_properties
from test.e2e.test_catalogue_category import GetDSL as CatalogueCategoryGetDSL
from test.e2e.test_catalogue_item import GetDSL as CatalogueItemGetDSL
from test.e2e.test_item import CreateDSL as ItemCreateDSL
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
        :return: ID of the created catalogue category (or `None` if not successful).
        """

        full_property_data = property_data.copy()
        # TODO: Remove need for putting into "properties"? - same for where its used elsewhere
        full_property_data = E2ETestHelpers.replace_unit_values_with_ids_in_properties(
            {"properties": [full_property_data]}, self.unit_value_id_dict
        )["properties"][0]
        self._post_response_property = self.test_client.post(
            "/v1/catalogue-categories/" f"{self.catalogue_category_id}/properties", json=full_property_data
        )

        property_id = (
            self._post_response_property.json()["id"] if self._post_response_property.status_code == 201 else None
        )

        # TODO: Cleanup?
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


# EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST = {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}

# CATALOGUE_CATEGORY_PROPERTY_POST_NON_MANDATORY = {
#     "name": "Property B",
#     "type": "number",
#     "unit": "mm",
#     "mandatory": False,
# }
# CATALOGUE_CATEGORY_PROPERTY_POST_NON_MANDATORY_EXPECTED = {
#     **CATALOGUE_CATEGORY_PROPERTY_POST_NON_MANDATORY,
#     "allowed_values": None,
# }

# CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY = {
#     "name": "Property B",
#     "type": "number",
#     "unit": "mm",
#     "mandatory": True,
#     "default_value": 20,
# }
# CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_EXPECTED = {
#     "name": "Property B",
#     "type": "number",
#     "unit": "mm",
#     "mandatory": True,
#     "allowed_values": None,
# }

# NEW_CATALOGUE_CATEGORY_PROPERTY_MANDATORY_EXPECTED = CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_EXPECTED
# NEW_PROPERTY_MANDATORY_EXPECTED = {"name": "Property B", "unit": "mm", "value": 20}

# CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES = {
#     **CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY,
#     "allowed_values": {"type": "list", "values": [10, 20, 30]},
# }
# CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED = {
#     **NEW_CATALOGUE_CATEGORY_PROPERTY_MANDATORY_EXPECTED,
#     "allowed_values": {"type": "list", "values": [10, 20, 30]},
# }
# NEW_CATALOGUE_CATEGORY_PROPERTY_MANDATORY_ALLOWED_VALUES_EXPECTED = (
#     CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED
# )

# CATALOGUE_CATEGORY_PROPERTY_PATCH = {
#     "name": "New property name",
#     "allowed_values": {"type": "list", "values": [10, 20, 30, 40]},
# }

# CATALOGUE_CATEGORY_PROPERTY_PATCH_EXPECTED = {
#     **CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED,
#     **CATALOGUE_CATEGORY_PROPERTY_PATCH,
# }

# NEW_CATALOGUE_CATEGORY_PROPERTY_PATCH_EXPECTED = CATALOGUE_CATEGORY_PROPERTY_PATCH_EXPECTED
# NEW_PROPERTY_PATCH_EXPECTED = {"name": "New property name", "unit": "mm", "value": 20}

# CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY = {
#     "allowed_values": {"type": "list", "values": [10, 20, 30, 40]},
# }
# CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY_EXPECTED = {
#     **CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED,
#     **CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY,
# }


# class UpdateDSL(CreateDSL):
#     """Base class for update tests (inherits CreateDSL to gain access to posts)"""

#     _catalogue_item_patch_response: Response

#     def patch_property(
#         self,
#         property_patch,
#         catalogue_category_id: Optional[str] = None,
#         property_id: Optional[str] = None,
#     ):
#         """Patches a posted property"""
#         self._catalogue_item_patch_response = self.test_client.patch(
#             "/v1/catalogue-categories/"
#             f"{catalogue_category_id if catalogue_category_id else self.catalogue_category['id']}"
#             "/properties/"
#             f"{property_id if property_id else self.property['id']}",
#             json=property_patch,
#         )

#     def check_property_patch_response_success(self, property_expected):
#         """Checks the response of patching a property succeeded as expected"""

#         assert self._catalogue_item_patch_response.status_code == 200
#         self.property = self._catalogue_item_patch_response.json()
#         assert self.property == {**property_expected, "id": ANY, "unit_id": ANY}

#     def check_property_patch_response_failed_with_message(self, status_code, detail):
#         """Checks the response of patching a property failed as expected"""

#         assert self._catalogue_item_patch_response.status_code == status_code
#         assert self._catalogue_item_patch_response.json()["detail"] == detail


# class TestUpdate(UpdateDSL):
#     """Tests for updating a property at the catalogue category level"""

#     def test_update(self):
#         """
#         Test updating a property at the catalogue category level
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH)

#         # Check updated correctly down the tree
#         self.check_property_patch_response_success(CATALOGUE_CATEGORY_PROPERTY_PATCH_EXPECTED)
#         self.check_catalogue_category_updated(NEW_CATALOGUE_CATEGORY_PROPERTY_PATCH_EXPECTED)
#         self.check_catalogue_item_updated(NEW_PROPERTY_PATCH_EXPECTED)
#         self.check_item_updated(NEW_PROPERTY_PATCH_EXPECTED)

#     def test_update_category_only(self):
#         """
#         Test updating a property at the catalogue category level but with an update that should leave the catalogue
#         items and items alone (i.e. only updating the allowed values)
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY)

#         # Check updated correctly
#         self.check_property_patch_response_success(CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY_EXPECTED)
#         self.check_catalogue_category_updated(CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY_EXPECTED)
#         # These are testing values are the same as they should have been prior to the patch (NEW_ is only there from
#         # the create tests)
#         self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
#         self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

#     def test_update_category_no_changes_allowed_values_none(self):
#         """
#         Test updating a property at the catalogue category level but with an update that shouldn't change anything
#         (in this case also passing allowed_values as None and keeping it None on the patch request)
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY)
#         self.check_property_post_response_success(NEW_CATALOGUE_CATEGORY_PROPERTY_MANDATORY_EXPECTED)

#         # Patch the property
#         self.patch_property({"name": CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY["name"], "allowed_values": None})

#         # Check updated correctly
#         self.check_property_patch_response_success(NEW_CATALOGUE_CATEGORY_PROPERTY_MANDATORY_EXPECTED)
#         # These are testing values are the same as they should have been prior to the patch (NEW_ is only there from
#         # the create tests)
#         self.check_catalogue_category_updated(NEW_CATALOGUE_CATEGORY_PROPERTY_MANDATORY_EXPECTED)
#         self.check_catalogue_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)
#         self.check_item_updated(NEW_PROPERTY_MANDATORY_EXPECTED)

#     def test_update_non_existent_catalogue_category_id(self):
#         """
#         Test updating a property at the catalogue category level when the specified catalogue category doesn't exist
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH, catalogue_category_id=str(ObjectId()))

#         # Check
#         self.check_property_patch_response_failed_with_message(404, "Catalogue category not found")

#     def test_update_invalid_catalogue_category_id(self):
#         """
#         Test updating a property at the catalogue category level when the specified catalogue category id is invalid
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH, catalogue_category_id="invalid")

#         # Check
#         self.check_property_patch_response_failed_with_message(404, "Catalogue category not found")

#     def test_update_non_existent_property_id(self):
#         """
#         Test updating a property at the catalogue category level when the specified property doesn't
#         exist in the specified catalogue category
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH, property_id=str(ObjectId()))

#         # Check
#         self.check_property_patch_response_failed_with_message(404, "Catalogue category property not found")

#     def test_update_invalid_property_id(self):
#         """
#         Test updating a property at the catalogue category level when the specified catalogue item id is invalid
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH, property_id="invalid")

#         # Check
#         self.check_property_patch_response_failed_with_message(404, "Catalogue category property not found")

#     def test_updating_property_to_have_duplicate_name(self):
#         """
#         Test updating a property to have a name matching another already existing one
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property({"name": EXISTING_CATALOGUE_CATEGORY_PROPERTY_POST["name"]})
#         self.check_property_patch_response_failed_with_message(422, "Duplicate property name: Property A")

#     def test_updating_property_allowed_values_from_none_to_value(self):
#         """
#         Test updating a property to have a allowed_values when it was initially None
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_EXPECTED)

#         # Patch the property
#         self.patch_property(CATALOGUE_CATEGORY_PROPERTY_PATCH_ALLOWED_VALUES_ONLY)
#         self.check_property_patch_response_failed_with_message(422, "Cannot add allowed_values to an existing property")

#     def test_updating_property_allowed_values_from_value_to_none(self):
#         """
#         Test updating a property to have no allowed_values when it initially had
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property({"allowed_values": None})
#         self.check_property_patch_response_failed_with_message(
#             422, "Cannot remove allowed_values from an existing property"
#         )

#     def test_updating_property_removing_allowed_values_list(self):
#         """
#         Test updating a property to remove an element from an allowed values list
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(
#             {
#                 "allowed_values": {
#                     "type": "list",
#                     # Remove a single value
#                     "values": CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"][
#                         0:-1
#                     ],
#                 }
#             }
#         )
#         self.check_property_patch_response_failed_with_message(
#             422, "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
#         )

#     def test_updating_property_modifying_allowed_values_list(self):
#         """
#         Test updating a property to modify a value in an allowed values list
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(
#             {
#                 "allowed_values": {
#                     "type": "list",
#                     # Change only the last value
#                     "values": [
#                         *CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"][0:-1],
#                         42,
#                     ],
#                 }
#             }
#         )
#         self.check_property_patch_response_failed_with_message(
#             422, "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
#         )

#     def test_updating_property_allowed_values_list_adding_with_different_type(self):
#         """
#         Test updating a property to add a value to an allowed values list but with a different type to the rest
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(
#             {
#                 "allowed_values": {
#                     "type": "list",
#                     # Change only the last value
#                     "values": [
#                         *CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"],
#                         "different type",
#                     ],
#                 }
#             }
#         )
#         self.check_property_patch_response_failed_with_message(
#             422, "allowed_values of type 'list' must only contain values of the same type as the property itself"
#         )

#     def test_updating_property_allowed_values_list_adding_duplicate_value(self):
#         """
#         Test updating a property to add a duplicate value to an allowed values list
#         """

#         # Setup by creating a property to update
#         self.post_catalogue_category_and_items()
#         self.post_property(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES)
#         self.check_property_post_response_success(CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES_EXPECTED)

#         # Patch the property
#         self.patch_property(
#             {
#                 "allowed_values": {
#                     "type": "list",
#                     # Change only the last value
#                     "values": [
#                         *CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"],
#                         CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES["allowed_values"]["values"][0],
#                     ],
#                 }
#             }
#         )
#         self.check_property_patch_response_failed_with_message(
#             422,
#             "allowed_values of type 'list' contains a duplicate value: "
#             f"{CATALOGUE_CATEGORY_PROPERTY_POST_MANDATORY_ALLOWED_VALUES['allowed_values']['values'][0]}",
#         )
