"""
End-to-End tests for the setting router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-ancestors

from copy import deepcopy
from test.e2e.conftest import E2ETestHelpers
from test.e2e.test_catalogue_item import GetDSL as CatalogueItemGetDSL
from test.e2e.test_item import DeleteDSL as ItemDeleteDSL
from test.e2e.test_usage_status import CreateDSL as UsageStatusCreateDSL
from test.mock_data import (
    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
    ITEM_DATA_REQUIRED_VALUES_ONLY,
    SETTING_SPARES_DEFINITION_DATA_NEW,
    SETTING_SPARES_DEFINITION_DATA_NEW_USED,
    SETTING_SPARES_DEFINITION_GET_DATA_NEW,
    SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED,
    SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    USAGE_STATUS_POST_DATA_NEW,
    USAGE_STATUS_POST_DATA_USED,
)
from typing import Optional

from bson import ObjectId
from httpx import Response


class UpdateSparesDefinitionDSL(UsageStatusCreateDSL):
    """Base class for update spares definition tests."""

    _put_response_spares_definition: Response

    def put_spares_definition(self, spares_definition_data: dict) -> None:
        """
        Puts a spares definition.

        :param spares_definition_data: Dictionary containing the patch data as would be required for a
                                       `SparesDefinitionPutSchema` but with any `id`'s replaced by the `value` as the
                                       IDs will be added automatically.
        """

        # Insert actual usage status IDs
        spares_definition_put_data = deepcopy(spares_definition_data)
        for usage_status_dict in spares_definition_put_data["usage_statuses"]:
            usage_status_dict["id"] = self.usage_status_value_id_dict.get(usage_status_dict["value"])
            del usage_status_dict["value"]

        self._put_response_spares_definition = self.test_client.put(
            "/v1/settings/spares_definition", json=spares_definition_put_data
        )

    def put_spares_definition_and_post_prerequisites(self, spares_definition_data: dict) -> None:
        """
        Utility method that puts a spares definition having first posted any prerequisite usage statuses.

        :param spares_definition_data: Dictionary containing the patch data as would be required for a
                                       `SparesDefinitionPutSchema` but with any `id`'s replaced by the `value` as the
                                       IDs will be added automatically.
        """

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.post_usage_status(USAGE_STATUS_POST_DATA_USED)
        self.put_spares_definition(spares_definition_data)

    def check_put_spares_definition_success(self, expected_spares_definition_get_data: dict) -> None:
        """
        Checks that a prior call to `put_spares_definition` gave a successful response with the expected data returned.

        :param expected_spares_definition_get_data: Dictionary containing the expected system data returned as would be
                                                    required for a `SparesDefinitionSchema`.
        """

        assert self._put_response_spares_definition.status_code == 200
        assert self._put_response_spares_definition.json() == expected_spares_definition_get_data

    def check_put_spares_definition_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `put_spares_definition` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._put_response_spares_definition.status_code == status_code
        assert self._put_response_spares_definition.json()["detail"] == detail

    def check_put_spares_definition_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `put_spares_definition` gave a failed response with the expected code and pydantic
        validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._put_response_spares_definition.status_code == status_code
        assert self._put_response_spares_definition.json()["detail"][0]["msg"] == message


class TestUpdateSparesDefinition(UpdateSparesDefinitionDSL):
    """Tests for updating the spares definition."""

    def test_update_spares_definition(self):
        """Test updating the spares definition (for the first time)."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW_USED)

        self.check_put_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED)

    def test_update_spares_definition_overwrite(self):
        """Test updating the spares definition (when it has already been assigned before)."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW_USED)
        self.check_put_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED)

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW)
        self.check_put_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW)

    def test_update_spares_definition_with_no_usage_statuses(self):
        """Test updating the spares definition with no usage statuses given."""

        self.put_spares_definition({**SETTING_SPARES_DEFINITION_DATA_NEW_USED, "usage_statuses": []})

        self.check_put_spares_definition_failed_with_validation_message(
            422, "List should have at least 1 item after validation, not 0"
        )

    def test_update_spares_definition_with_duplicate_usage_statuses(self):
        """Test updating the spares definition with no usage statuses given."""

        self.put_spares_definition_and_post_prerequisites(
            {
                **SETTING_SPARES_DEFINITION_DATA_NEW_USED,
                "usage_statuses": [
                    *SETTING_SPARES_DEFINITION_DATA_NEW_USED["usage_statuses"],
                    SETTING_SPARES_DEFINITION_DATA_NEW_USED["usage_statuses"][0].copy(),
                ],
            }
        )

        self.check_put_spares_definition_failed_with_validation_message(
            422,
            "Value error, usage_statuses contains a duplicate ID: "
            f"{self.usage_status_value_id_dict[SETTING_SPARES_DEFINITION_DATA_NEW_USED['usage_statuses'][0]['value']]}",
        )

    def test_update_spares_definition_with_non_existent_usage_status_id(self):
        """Test updating the spares definition when there is a non-existent usage status ID."""

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.add_usage_status_value_and_id(USAGE_STATUS_POST_DATA_USED["value"], str(ObjectId()))
        self.put_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW_USED)

        self.check_put_spares_definition_failed_with_detail(422, "A specified usage status does not exist")

    def test_update_spares_definition_with_invalid_usage_status_id(self):
        """Test updating the spares definition when there is an invalid usage status ID."""

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.add_usage_status_value_and_id(USAGE_STATUS_POST_DATA_USED["value"], "invalid-id")
        self.put_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW_USED)

        self.check_put_spares_definition_failed_with_detail(422, "A specified usage status does not exist")


class GetSparesDefinitionDSL(UpdateSparesDefinitionDSL):
    """Base class for get spares definition tests."""

    _get_response_spares_definition: Response

    def get_spares_definition(self):
        """Gets the spares definition."""

        self._get_response_spares_definition = self.test_client.get("/v1/settings/spares_definition")

    def check_get_spares_definition_success(self, expected_spares_definition_get_data: dict):
        """
        Checks that a prior call to `get_spares_definition` gave a successful response with the expected data returned.

        :param expected_spares_definition_get_data: Dictionary containing the expected system data returned as would be
                                                    required for a `SparesDefinitionSchema`.
        """

        assert self._get_response_spares_definition.status_code == 200
        assert self._get_response_spares_definition.json() == expected_spares_definition_get_data

    def check_get_spares_definition_failed_with_detail(self, status_code: int, detail: str):
        """
        Checks that a prior call to `get_spares_definition` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response_spares_definition.status_code == status_code
        assert self._get_response_spares_definition.json()["detail"] == detail


class TestGetSparesDefinition(GetSparesDefinitionDSL):
    """Tests for getting the spares definition."""

    def test_get_spares_definition(self):
        """Test getting the spares definition."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW_USED)
        self.get_spares_definition()
        self.check_get_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED)

    def test_get_spares_definition_when_non_existent(self):
        """Test getting the spares definition when it is non-existent."""

        self.get_spares_definition()
        self.check_get_spares_definition_failed_with_detail(404, "Spares definition not found.")


class SparesDefinitionDSL(UpdateSparesDefinitionDSL, ItemDeleteDSL, CatalogueItemGetDSL):
    """Base class for spares definition tests."""

    catalogue_item_ids: list[str]
    _post_responses_catalogue_items: list[Response]

    def post_item_with_usage_status(self, usage_status_value: str) -> Optional[str]:
        """
        Utility method that posts an item with a specific usage status.

        :return: ID of the created item (or `None` if not successful).
        """

        return self.post_item({**ITEM_DATA_REQUIRED_VALUES_ONLY, "usage_status": usage_status_value})

    def post_items_and_prerequisites_with_usage_statuses(self, usage_status_values_lists: list[list[str]]) -> None:
        """
        Utility method that posts a series of catalogue items and items as well as their prerequisite manufacturer,
        catalogue category, units, usage statuses and units where the items have a given series of usage statuses.


        :param usage_status_values_lists: List containing lists of usage status values. Each outer list represents
                                          a separate catalogue item to create and each value in the inner list
                                          gives the usage status of an item to create within that same catalogue item.
        """

        # Item pre-requisites
        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)

        # Avoid re-posting unnecessarily
        if USAGE_STATUS_POST_DATA_NEW["value"] not in self.usage_status_value_id_dict:
            self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
            self.post_usage_status(USAGE_STATUS_POST_DATA_USED)

        # Create one catalogue item for each list in usage_status_values_lists
        self.catalogue_item_ids = []
        self._post_responses_catalogue_items = []
        for i, usage_status_values in enumerate(usage_status_values_lists):
            # Only post prerequisites once
            if i == 0:
                catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
                    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
                )
            else:
                catalogue_item_id = self.post_catalogue_item(CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES)
            self.catalogue_item_ids.append(catalogue_item_id)
            self._post_responses_catalogue_items.append(self._post_response_catalogue_item)

            # Create one item for each usage status value in usage_status_values
            for usage_status_value in usage_status_values:
                self.post_item_with_usage_status(usage_status_value)

    def patch_item_usage_status(self, item_id: str, usage_status_value: str) -> None:
        """
        Utility method that patches an item to have a given usage status given its value.

        :param item_id: ID of the item to patch.
        :param usage_status_value: Value of the usage status to update the item with.
        """

        self.patch_item(item_id, {"usage_status_id": self.usage_status_value_id_dict[usage_status_value]})

    def check_catalogue_items_spares(self, expected_number_of_spares_list: list[Optional[int]]) -> None:
        """
        Checks that any catalogue items created via `post_items_and_prerequisites_with_usage_statuses` have specific
        expected `number_of_spares` values.

        :param expected_number_of_spares_list: List of the expected values of the `number_of_spares` field, one for
                                               each catalogue item that was created.
        """

        for i, (catalogue_item_id, expected_number_of_spares) in enumerate(
            zip(self.catalogue_item_ids, expected_number_of_spares_list)
        ):
            self.get_catalogue_item(catalogue_item_id)
            self.check_get_catalogue_item_success(
                {**CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES, "number_of_spares": expected_number_of_spares}
            )

            # Also ensure the created and modified times are not changed
            E2ETestHelpers.check_created_and_modified_times_not_updated(
                self._post_responses_catalogue_items[i], self._get_response_catalogue_item
            )


class TestSparesDefinitionDSL(SparesDefinitionDSL):
    """Tests for spares definition."""

    def test_set_spares_definition_with_existing_items(self):
        """Test setting the spares definition when there are existing items."""

        self.post_items_and_prerequisites_with_usage_statuses(
            [
                # Catalogue item 1
                ["New", "Used"],
                # Catalogue item 2
                ["New", "New"],
            ]
        )

        # Set new spares definition and ensure all are updated
        self.check_catalogue_items_spares([None, None])
        self.put_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW)
        self.check_catalogue_items_spares([1, 2])

    def test_create_item_after_spares_definition_set(self):
        """Test creating an item after the spares definition is set."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW)
        self.post_items_and_prerequisites_with_usage_statuses([["Used"], ["New"]])

        # Add one new item to the second catalogue item and ensure only it is updated
        self.check_catalogue_items_spares([0, 1])
        self.post_item_with_usage_status("New")
        self.check_catalogue_items_spares([0, 2])

    def test_update_item_after_spares_definition_set(self):
        """Test updating an item after the spares definition is set."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW)
        self.post_items_and_prerequisites_with_usage_statuses([["Used"], ["New"]])
        item_id = self.post_item_with_usage_status("Used")

        # Update the new item's usage status and ensure this updates its catalogue item
        self.check_catalogue_items_spares([0, 1])
        self.patch_item_usage_status(item_id, "New")
        self.check_catalogue_items_spares([0, 2])

    def test_delete_item_after_spares_definition_set(self):
        """Test updating an item after the spares definition is set."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW)
        self.post_items_and_prerequisites_with_usage_statuses([["Used"], ["New"]])
        item_id = self.post_item_with_usage_status("New")

        # Update the new item's usage status and ensure this updates its catalogue item
        self.check_catalogue_items_spares([0, 2])
        self.delete_item(item_id)
        self.check_catalogue_items_spares([0, 1])
