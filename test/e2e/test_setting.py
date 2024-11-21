"""
End-to-End tests for the setting router.
"""

from copy import deepcopy
from test.e2e.test_usage_status import CreateDSL as UsageStatusCreateDSL
from test.mock_data import (
    SETTING_SPARES_DEFINITION_DATA_NEW,
    SETTING_SPARES_DEFINITION_DATA_NEW_USED,
    SETTING_SPARES_DEFINITION_GET_DATA_NEW,
    SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED,
    USAGE_STATUS_POST_DATA_NEW,
    USAGE_STATUS_POST_DATA_USED,
)

from bson import ObjectId
from httpx import Response


class SetSparesDefinitionDSL(UsageStatusCreateDSL):
    """Base class for set spares definition tests."""

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


class TestSetSparesDefinition(SetSparesDefinitionDSL):
    """Tests for setting the spares definition."""

    def test_set_spares_definition(self):
        """Test setting the spares definition (for the first time)."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW_USED)

        self.check_put_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED)

    def test_set_spares_definition_overwrite(self):
        """Test setting the spares definition (when it has already been assigned before)."""

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW_USED)
        self.check_put_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED)

        self.put_spares_definition_and_post_prerequisites(SETTING_SPARES_DEFINITION_DATA_NEW)
        self.check_put_spares_definition_success(SETTING_SPARES_DEFINITION_GET_DATA_NEW)

    def test_set_spares_definition_with_no_usage_statuses(self):
        """Test setting the spares definition with no usage statuses given."""

        self.put_spares_definition({**SETTING_SPARES_DEFINITION_DATA_NEW_USED, "usage_statuses": []})

        self.check_put_spares_definition_failed_with_validation_message(
            422, "List should have at least 1 item after validation, not 0"
        )

    def test_set_spares_definition_with_duplicate_usage_statuses(self):
        """Test setting the spares definition with no usage statuses given."""

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

    def test_set_spares_definition_with_non_existent_usage_status_id(self):
        """Test setting the spares definition when there is a non-existent usage status ID."""

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.add_usage_status_value_and_id(USAGE_STATUS_POST_DATA_USED["value"], str(ObjectId()))
        self.put_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW_USED)

        self.check_put_spares_definition_failed_with_detail(422, "A specified usage status does not exist")

    def test_set_spares_definition_with_invalid_usage_status_id(self):
        """Test setting the spares definition when there is an invalid usage status ID."""

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.add_usage_status_value_and_id(USAGE_STATUS_POST_DATA_USED["value"], "invalid-id")
        self.put_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW_USED)

        self.check_put_spares_definition_failed_with_detail(422, "A specified usage status does not exist")
