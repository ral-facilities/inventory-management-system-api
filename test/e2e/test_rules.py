"""
End-to-End tests for the rule router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code


from test.mock_data import (
    RULE_GET_DATA_OPERATIONAL_TO_SCRAPPED,
    RULE_GET_DATA_OPERATIONAL_TO_STORAGE,
    RULE_GET_DATA_STORAGE_CREATION,
    RULE_GET_DATA_STORAGE_DELETION,
    RULES_GET_DATA,
    SYSTEM_TYPE_GET_DATA_OPERATIONAL,
    SYSTEM_TYPE_GET_DATA_STORAGE,
)

import pytest
from fastapi.testclient import TestClient
from httpx import Response


class ListDSL:
    """Base class for list tests."""

    test_client: TestClient

    _get_response_rule: Response

    @pytest.fixture(autouse=True)
    def setup_rule_list_dsl(self, test_client):
        """Setup fixtures."""

        self.test_client = test_client

    def get_rules(self, filters: dict) -> None:
        """
        Gets a list of rules with the given filters.

        :param filters: Filters to use in the request.
        """

        self._get_response_rule = self.test_client.get("/v1/rules", params=filters)

    def check_get_rules_success(self, expected_rules_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_rules` gave a successful response with the expected data returned.

        :param expected_rules_get_data: List of dictionaries containing the expected rule data returned as would be
                                        required for `RuleSchema`'s.
        """

        assert self._get_response_rule.status_code == 200
        assert self._get_response_rule.json() == expected_rules_get_data


class TestList(ListDSL):
    """Tests for getting a list of systems."""

    def test_list_with_no_filters(self):
        """Test getting a list of all rules with no filters provided."""

        self.get_rules(filters={})
        self.check_get_rules_success(RULES_GET_DATA)

    def test_list_with_src_system_type_id_filter(self):
        """Test getting a list of all rules with a `src_system_type_id` filter provided."""

        self.get_rules(filters={"src_system_type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]})
        self.check_get_rules_success([RULE_GET_DATA_OPERATIONAL_TO_STORAGE, RULE_GET_DATA_OPERATIONAL_TO_SCRAPPED])

    def test_list_with_null_src_system_type_id_filter(self):
        """Test getting a list of all rules with a `src_system_type_id` filter of `null` provided."""

        self.get_rules(filters={"src_system_type_id": "null"})
        self.check_get_rules_success([RULE_GET_DATA_STORAGE_CREATION])

    def test_list_with_invalid_src_system_type_id_filter(self):
        """Test getting a list of all rules with an invalid `src_system_type_id` filter provided."""

        self.get_rules(filters={"src_system_type_id": "invalid-id"})
        self.check_get_rules_success([])

    def test_list_with_dst_system_type_id_filter(self):
        """Test getting a list of all rules with a `dst_system_type_id` filter provided."""

        self.get_rules(filters={"dst_system_type_id": SYSTEM_TYPE_GET_DATA_STORAGE["id"]})
        self.check_get_rules_success([RULE_GET_DATA_STORAGE_CREATION, RULE_GET_DATA_OPERATIONAL_TO_STORAGE])

    def test_list_with_null_dst_system_type_id_filter(self):
        """Test getting a list of all rules with a `dst_system_type_id` filter of `null` provided."""

        self.get_rules(filters={"dst_system_type_id": "null"})
        self.check_get_rules_success([RULE_GET_DATA_STORAGE_DELETION])

    def test_list_with_invalid_dst_system_type_id_filter(self):
        """Test getting a list of all rules with an invalid `dst_system_type_id` filter provided."""

        self.get_rules(filters={"dst_system_type_id": "invalid-id"})
        self.check_get_rules_success([])

    def test_list_with_src_and_dst_system_type_id_filter(self):
        """Test getting a list of all rules with `src_system_type_id` and `dst_system_type_id` filters provided
        when there are no matching results."""

        self.get_rules(
            filters={
                "src_system_type_id": SYSTEM_TYPE_GET_DATA_STORAGE["id"],
                "dst_system_type_id": SYSTEM_TYPE_GET_DATA_STORAGE["id"],
            }
        )
        self.check_get_rules_success([])
