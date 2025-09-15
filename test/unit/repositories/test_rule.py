"""
Unit tests for the `RuleRepo` repository.
"""

from test.mock_data import RULE_OUT_DATA_STORAGE_CREATION, RULES_OUT_DATA
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.models.rule import RuleOut
from inventory_management_system_api.repositories.rule import (
    RULES_GET_AGGREGATION_PIPELINE_ENTITY_INSERT_STAGES,
    RuleRepo,
)


class RuleRepoDSL:
    """Base class for `RuleRepo` unit tests."""

    mock_database: Mock
    mock_utils: Mock
    rule_repository: RuleRepo
    rules_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures."""

        self.mock_database = database_mock
        self.rule_repository = RuleRepo(database_mock)
        self.rules_collection = database_mock.rules

        with patch("inventory_management_system_api.repositories.rule.utils") as mock_utils:
            self.mock_utils = mock_utils
            yield


class ListDSL(RuleRepoDSL):
    """Base class for `list` tests."""

    _expected_rules_out: list[RuleOut]
    _src_system_type_id_filter: Optional[str]
    _dst_system_type_id_filter: Optional[str]
    _obtained_rules_out: list[RuleOut]

    def mock_list(self, rules_out_data: list[dict]):
        """
        Mocks database methods appropriately to test the `list` repo method.

        :param rules_out_data: List of dictionaries containing the rule data as would be required for a `RuleOut`
                               database model.
        """

        self._expected_rules_out = [RuleOut(**rule_out_data) for rule_out_data in rules_out_data]

        self.rules_collection.aggregate.return_value = [rule_out.model_dump() for rule_out in self._expected_rules_out]

    def call_list(self, src_system_type_id: Optional[str], dst_system_type_id: Optional[str]):
        """
        Calls the `RuleRepo` `list` method.

        :param src_system_type_id: ID of the source system type to query by, or `None`.
        :param dst_system_type_id: ID of the destination system type to query by, or `None`.
        """

        self._src_system_type_id_filter = src_system_type_id
        self._dst_system_type_id_filter = dst_system_type_id

        self._obtained_rules_out = self.rule_repository.list(
            src_system_type_id, dst_system_type_id, session=self.mock_session
        )

    def check_list_success(self):
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_utils.list_query.assert_called_once_with(
            {
                "src_system_type_id": self._src_system_type_id_filter,
                "dst_system_type_id": self._dst_system_type_id_filter,
            },
            "rules",
        )
        self.rules_collection.aggregate.assert_called_once_with(
            [{"$match": self.mock_utils.list_query.return_value}, *RULES_GET_AGGREGATION_PIPELINE_ENTITY_INSERT_STAGES],
            session=self.mock_session,
        )


class TestList(ListDSL):
    """Tests for listing rules."""

    def test_list(self):
        """Test listing rules."""

        self.mock_list(RULES_OUT_DATA)
        self.call_list(src_system_type_id=None, dst_system_type_id=None)
        self.check_list_success()

    def test_list_with_src_system_id_filter(self):
        """Test listing rules with a given `src_system_type_id`."""

        self.mock_list(RULES_OUT_DATA)
        self.call_list(src_system_type_id=str(ObjectId()), dst_system_type_id=None)
        self.check_list_success()

    def test_list_with_dst_system_id_filter(self):
        """Test listing rules with a given `dst_system_type_id`."""

        self.mock_list(RULES_OUT_DATA)
        self.call_list(src_system_type_id=None, dst_system_type_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_src_and_dst_system_id_filter_with_no_results(self):
        """Test listing rules with a `src_system_type_id` and `dst_system_type_id` filter returning no results."""

        self.mock_list([])
        self.call_list(src_system_type_id=str(ObjectId()), dst_system_type_id=str(ObjectId()))
        self.check_list_success()


class CheckExistsDSL(RuleRepoDSL):
    """Base class for `check_exists` tests."""

    _expected_result: bool
    _src_system_type_id: Optional[str]
    _dst_system_type_id: Optional[str]
    _dst_usage_status_id: Optional[str]
    _obtained_result: bool

    def mock_check_exists(self, result: bool):
        """
        Mocks database methods appropriately to test the `check_exists` repo method.

        :param result: The result to mock for.
        """

        self._expected_result = result
        # Actual returned value doesn't matter here just as long as its not None
        RepositoryTestHelpers.mock_find_one(self.rules_collection, RULE_OUT_DATA_STORAGE_CREATION if result else None)

    def call_check_exists(
        self, src_system_type_id: Optional[str], dst_system_type_id: Optional[str], dst_usage_status_id: Optional[str]
    ):
        """
        Calls the `RuleRepo` `check_exists` method.

        :param src_system_type_id: ID of the source system type to query by.
        :param dst_system_type_id: ID of the destination system type to query by.
        :param dst_usage_status_id: ID of the destination usage status to query by.
        """

        self._src_system_type_id = src_system_type_id
        self._dst_system_type_id = dst_system_type_id
        self._dst_usage_status_id = dst_usage_status_id

        self._obtained_result = self.rule_repository.check_exists(
            src_system_type_id, dst_system_type_id, dst_usage_status_id, session=self.mock_session
        )

    def check_check_exists_success(self):
        """Checks that a prior call to `call_check_exists` worked as expected."""

        self.rules_collection.find_one.assert_called_with(
            {
                "src_system_type_id": CustomObjectId(self._src_system_type_id) if self._src_system_type_id else None,
                "dst_system_type_id": CustomObjectId(self._dst_system_type_id) if self._dst_system_type_id else None,
                "dst_usage_status_id": CustomObjectId(self._dst_usage_status_id) if self._dst_usage_status_id else None,
            },
            session=self.mock_session,
        )

        assert self._obtained_result == self._expected_result


class TestCheckExists(CheckExistsDSL):
    """Tests for checking if a rule exists."""

    def test_check_exists_with_all_ids_given(self):
        """Test checking the existence of a rule with specific IDs given for each parameter."""

        self.mock_check_exists(True)
        self.call_check_exists(
            src_system_type_id=str(ObjectId()), dst_system_type_id=str(ObjectId()), dst_usage_status_id=str(ObjectId())
        )
        self.check_check_exists_success()

    def test_check_exists_with_all_ids_none(self):
        """Test checking the existence of a rule with no IDs given for each parameter."""

        self.mock_check_exists(False)
        self.call_check_exists(src_system_type_id=None, dst_system_type_id=None, dst_usage_status_id=None)
        self.check_check_exists_success()
