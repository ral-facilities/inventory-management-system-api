"""
Unit tests for the `SettingService` service.
"""

from copy import deepcopy
from test.mock_data import (
    SETTING_SPARES_DEFINITION_DATA_NEW_USED,
    USAGE_STATUS_OUT_DATA_NEW,
    USAGE_STATUS_OUT_DATA_USED,
)
from test.unit.services.conftest import ServiceTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.schemas.setting import SparesDefinitionPutSchema
from inventory_management_system_api.services.setting import SettingService


class SettingServiceDSL:
    """Base class for `SettingService` unit tests."""

    mock_setting_repository: Mock
    mock_usage_status_repository: Mock
    setting_service: SettingService

    @pytest.fixture(autouse=True)
    def setup(self, setting_repository_mock, usage_status_repository_mock, setting_service):
        """Setup fixtures"""

        self.mock_setting_repository = setting_repository_mock
        self.mock_usage_status_repository = usage_status_repository_mock
        self.setting_service = setting_service


class SetSparesDefinitionDSL(SettingServiceDSL):
    """Base class for `set_spares_definition` tests."""

    _spares_definition_put: SparesDefinitionPutSchema
    _expected_spares_definition_in: SparesDefinitionIn
    _expected_spares_definition_out: MagicMock
    _set_spares_definition: MagicMock
    _set_spares_definition_exception: pytest.ExceptionInfo

    def mock_set_spares_definition(
        self, spares_definition_data: dict, usage_statuses_out_data: list[Optional[dict]]
    ) -> None:
        """
        Mocks repository methods appropriately to test the `set_spares_definition` service method.

        :param spares_definition_data: Dictionary containing the put data as would be required for a
                                       `SparesDefinitionPutSchema` but with any `id`'s replaced by the `value` as the
                                       IDs will be added automatically.
        :param usage_statuses_out_data: List where each element is either `None` or dictionaries containing the basic
                                        usage status data as would be required for a `UsageStatusOut` database model.
                                        (Should correspond to each of the usage status IDs given in the setting put
                                        data.)
        """

        # Stored usage statuses
        for i in range(0, len(spares_definition_data["usage_statuses"])):
            ServiceTestHelpers.mock_get(self.mock_usage_status_repository, usage_statuses_out_data[i])

        # Insert usage status IDs
        spares_definition_put_data = deepcopy(spares_definition_data)
        for i, usage_status_dict in enumerate(spares_definition_put_data["usage_statuses"]):
            usage_status_dict["id"] = (
                str(ObjectId()) if usage_statuses_out_data[i] is None else usage_statuses_out_data[i]["id"]
            )
            del usage_status_dict["value"]

        # Put schema
        self._spares_definition_put = SparesDefinitionPutSchema(**spares_definition_put_data)

        # Expected input for the repository
        self._expected_spares_definition_in = SparesDefinitionIn(**spares_definition_put_data)

        # Upserted setting
        self._expected_spares_definition_out = MagicMock()
        ServiceTestHelpers.mock_upsert(self.mock_setting_repository, self._expected_spares_definition_out)

    def call_set_spares_definition(self) -> None:
        """Calls the `SettingService` `set_spares_definition` method with the appropriate data from a prior call to
        `mock_set_spares_definition`."""

        self._set_spares_definition = self.setting_service.set_spares_definition(self._spares_definition_put)

    def call_set_spares_definition_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `SettingService` `set_spares_definition` method with the appropriate data from a prior call to
        `mock_set_spares_definition` while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.setting_service.set_spares_definition(self._spares_definition_put)
        self._set_spares_definition_exception = exc

    def check_set_spares_definition_success(self) -> None:
        """Checks that a prior call to `call_set_spares_definition` worked as expected."""

        # Ensure obtained all of the required usage statuses
        self.mock_usage_status_repository.get.assert_has_calls(
            # Pydantic Field confuses pylint
            # pylint: disable=not-an-iterable
            [call(usage_status.id) for usage_status in self._spares_definition_put.usage_statuses]
        )

        # Ensure upserted with expected data
        self.mock_setting_repository.upsert.assert_called_once_with(
            self._expected_spares_definition_in, SparesDefinitionOut
        )

        assert self._set_spares_definition == self._expected_spares_definition_out

    def check_set_spares_definition_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_set_spares_definition_expecting_error` worked as expected, raising an
        exception with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_setting_repository.upsert.assert_not_called()

        assert str(self._set_spares_definition_exception.value) == message


class TestSetSpareDefinition(SetSparesDefinitionDSL):
    """Tests for setting the spares definition."""

    def test_set_spare_definition(self):
        """Test setting the spares definition."""

        self.mock_set_spares_definition(
            SETTING_SPARES_DEFINITION_DATA_NEW_USED, [USAGE_STATUS_OUT_DATA_NEW, USAGE_STATUS_OUT_DATA_USED]
        )
        self.call_set_spares_definition()
        self.check_set_spares_definition_success()

    def test_set_spare_definition_with_non_existent_usage_status_id(self):
        """Test setting the spares definition with a non-existent usage status ID."""

        self.mock_set_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW_USED, [USAGE_STATUS_OUT_DATA_NEW, None])
        self.call_set_spares_definition_expecting_error(MissingRecordError)
        self.check_set_spares_definition_failed_with_exception(
            # Pydantic Field confuses pylint
            # pylint: disable=unsubscriptable-object
            f"No usage status found with ID: {self._spares_definition_put.usage_statuses[1].id}"
        )
