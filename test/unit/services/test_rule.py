"""
Unit tests for the `RuleService` service.
"""

from test.unit.services.conftest import ServiceTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.services.rule import RuleService


class RuleServiceDSL:
    """Base class for `RuleService` unit tests."""

    mock_rule_repository: Mock
    rule_service: RuleService

    @pytest.fixture(autouse=True)
    def setup(self, rule_repository_mock, rule_service):
        """Setup fixtures."""

        self.mock_rule_repository = rule_repository_mock
        self.rule_service = rule_service


class ListDSL(RuleServiceDSL):
    """Base class for `list` tests."""

    _src_system_type_id_filter: Optional[str]
    _dst_system_type_id_filter: Optional[str]
    _expected_rules: MagicMock
    _obtained_rules: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_rules = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_rule_repository, self._expected_rules)

    def call_list(self, src_system_type_id: Optional[str], dst_system_type_id: Optional[str]) -> None:
        """
        Calls the `RuleService` `list` method.

        :param src_system_type_id: `src_system_type_id` to filter the rules by or `None`.
        :param dst_system_type_id: `dst_system_type_id` to filter the rules by or `None`.
        """

        self._src_system_type_id_filter = src_system_type_id
        self._dst_system_type_id_filter = dst_system_type_id
        self._obtained_rules = self.rule_service.list(src_system_type_id, dst_system_type_id)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_rule_repository.list.assert_called_once_with(
            self._src_system_type_id_filter, self._dst_system_type_id_filter
        )
        assert self._obtained_rules == self._expected_rules


class TestList(ListDSL):
    """Tests for listing rules."""

    def test_list(self):
        """Test listing rules."""

        self.mock_list()
        self.call_list(str(ObjectId()), str(ObjectId()))
        self.check_list_success()
