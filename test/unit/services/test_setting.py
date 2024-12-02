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
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.schemas.setting import SparesDefinitionPutSchema
from inventory_management_system_api.services.setting import SettingService


class SettingServiceDSL:
    """Base class for `SettingService` unit tests."""

    mock_setting_repository: Mock
    mock_catalogue_item_repository: Mock
    mock_item_repository: Mock
    mock_usage_status_repository: Mock
    mock_utils: Mock
    mock_start_session_transaction: Mock
    setting_service: SettingService

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    @pytest.fixture(autouse=True)
    def setup(
        self,
        setting_repository_mock,
        catalogue_item_repository_mock,
        item_repository_mock,
        usage_status_repository_mock,
        setting_service,
    ):
        """Setup fixtures"""

        self.mock_setting_repository = setting_repository_mock
        self.mock_catalogue_item_repository = catalogue_item_repository_mock
        self.mock_item_repository = item_repository_mock
        self.mock_usage_status_repository = usage_status_repository_mock
        self.setting_service = setting_service

        with patch("inventory_management_system_api.services.setting.utils") as mocked_utils:
            with patch(
                "inventory_management_system_api.services.setting.start_session_transaction"
            ) as mocked_start_session_transaction:
                self.mock_utils = mocked_utils
                self.mock_start_session_transaction = mocked_start_session_transaction
                yield


class UpdateSparesDefinitionDSL(SettingServiceDSL):
    """Base class for `update_spares_definition` tests."""

    _spares_definition_put: SparesDefinitionPutSchema
    _expected_spares_definition_in: SparesDefinitionIn
    _expected_spares_definition_out: MagicMock
    _expected_catalogue_item_ids: list[ObjectId]
    _updated_spares_definition: MagicMock
    _update_spares_definition_exception: pytest.ExceptionInfo

    def mock_update_spares_definition(
        self, spares_definition_data: dict, usage_statuses_out_data: list[Optional[dict]]
    ) -> None:
        """
        Mocks repository methods appropriately to test the `update_spares_definition` service method.

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

        # Expected list of catalogue item ids that need to be updated (actual values don't matter here)
        self._expected_catalogue_item_ids = [ObjectId(), ObjectId()]
        self.mock_catalogue_item_repository.list_ids.return_value = self._expected_catalogue_item_ids

    def call_update_spares_definition(self) -> None:
        """Calls the `SettingService` `update_spares_definition` method with the appropriate data from a prior call to
        `mock_update_spares_definition`."""

        self._updated_spares_definition = self.setting_service.update_spares_definition(self._spares_definition_put)

    def call_update_spares_definition_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `SettingService` `update_spares_definition` method with the appropriate data from a prior call to
        `mock_update_spares_definition` while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.setting_service.update_spares_definition(self._spares_definition_put)
        self._update_spares_definition_exception = exc

    def check_update_spares_definition_success(self) -> None:
        """Checks that a prior call to `call_update_spares_definition` worked as expected."""

        # Ensure obtained all of the required usage statuses
        self.mock_usage_status_repository.get.assert_has_calls(
            # Pydantic Field confuses pylint
            # pylint: disable=not-an-iterable
            [call(usage_status.id) for usage_status in self._spares_definition_put.usage_statuses]
        )

        # Ensure started a transaction
        self.mock_start_session_transaction.assert_called_once_with("updating spares definition")
        expected_session = self.mock_start_session_transaction.return_value.__enter__.return_value

        # Ensure upserted with expected data
        self.mock_setting_repository.upsert.assert_called_once_with(
            self._expected_spares_definition_in, SparesDefinitionOut, session=expected_session
        )

        # Ensure obtained list of all catalogue item ids and used them to recalculate the number of spares
        self.mock_catalogue_item_repository.list_ids.assert_called_once_with()
        self.mock_utils.get_usage_status_ids_from_spares_definition.assert_called_once_with(
            self._expected_spares_definition_out
        )

        expected_prepare_for_number_of_spares_recalculation_calls = []
        expected_perform_number_of_spares_recalculation_calls = []
        for catalogue_item_id in self._expected_catalogue_item_ids:
            expected_prepare_for_number_of_spares_recalculation_calls.append(
                call(catalogue_item_id, self.mock_catalogue_item_repository, expected_session)
            )
            expected_perform_number_of_spares_recalculation_calls.append(
                call(
                    catalogue_item_id,
                    self.mock_utils.get_usage_status_ids_from_spares_definition.return_value,
                    self.mock_catalogue_item_repository,
                    self.mock_item_repository,
                    expected_session,
                )
            )
        self.mock_utils.prepare_for_number_of_spares_recalculation.assert_has_calls(
            expected_prepare_for_number_of_spares_recalculation_calls
        )
        self.mock_utils.perform_number_of_spares_recalculation.assert_has_calls(
            expected_perform_number_of_spares_recalculation_calls
        )

        assert self._updated_spares_definition == self._expected_spares_definition_out

    def check_update_spares_definition_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_spares_definition_expecting_error` worked as expected, raising an
        exception with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_setting_repository.upsert.assert_not_called()

        assert str(self._update_spares_definition_exception.value) == message


class TestUpdateSpareDefinition(UpdateSparesDefinitionDSL):
    """Tests for updating the spares definition."""

    def test_update_spare_definition(self):
        """Test updating the spares definition."""

        self.mock_update_spares_definition(
            SETTING_SPARES_DEFINITION_DATA_NEW_USED, [USAGE_STATUS_OUT_DATA_NEW, USAGE_STATUS_OUT_DATA_USED]
        )
        self.call_update_spares_definition()
        self.check_update_spares_definition_success()

    def test_update_spare_definition_with_non_existent_usage_status_id(self):
        """Test updating the spares definition with a non-existent usage status ID."""

        self.mock_update_spares_definition(SETTING_SPARES_DEFINITION_DATA_NEW_USED, [USAGE_STATUS_OUT_DATA_NEW, None])
        self.call_update_spares_definition_expecting_error(MissingRecordError)
        self.check_update_spares_definition_failed_with_exception(
            # Pydantic Field confuses pylint
            # pylint: disable=unsubscriptable-object
            f"No usage status found with ID: {self._spares_definition_put.usage_statuses[1].id}"
        )
