"""
Unit tests for the `SettingService` service.
"""

from test.mock_data import (
    SETTING_SPARES_DEFINITION_IN_DATA_STORAGE_OR_OPERATIONAL,
    SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
    SYSTEM_TYPE_OUT_DATA_STORAGE,
)
from test.unit.services.conftest import ServiceTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.services.setting import SettingService

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments


class SettingServiceDSL:
    """Base class for `SettingService` unit tests."""

    mock_setting_repository: Mock
    mock_system_type_repository: Mock
    mock_catalogue_item_repository: Mock
    mock_item_repository: Mock
    mock_start_session_transaction: Mock
    setting_service: SettingService

    @pytest.fixture(autouse=True)
    def setup(
        self,
        setting_repository_mock,
        system_type_repository_mock,
        catalogue_item_repository_mock,
        item_repository_mock,
        setting_service,
    ):
        """Setup fixtures."""

        self.mock_setting_repository = setting_repository_mock
        self.mock_system_type_repository = system_type_repository_mock
        self.mock_catalogue_item_repository = catalogue_item_repository_mock
        self.mock_item_repository = item_repository_mock
        self.setting_service = setting_service

        with patch(
            "inventory_management_system_api.services.setting.start_session_transaction"
        ) as mocked_start_session_transaction:
            self.mock_start_session_transaction = mocked_start_session_transaction
            yield


class SetSparesDefinitionDSL(SettingServiceDSL):
    """Base class for `set_spares_definition` tests."""

    _spares_definition_in: SparesDefinitionIn
    _expected_spares_definition_out: MagicMock
    _expected_catalogue_item_ids = list[ObjectId]
    _updated_spares_definition: MagicMock
    _set_spares_definition_exception: pytest.ExceptionInfo

    def mock_set_spares_definition(
        self, spares_definition_in_data: dict, system_types_out_data: list[Optional[dict]]
    ) -> None:
        """
        Mocks repository methods appropriately to test the `set_spares_definition` service method.

        :param spares_definition_in_data: Dictionary containing the new spares definition data as would be required for
                                          a `SparesDefinitionIn` database model.
        :param system_types_out_data: List where each element is either `None` or a dictionary containing the system
                                      type data as would be required for a `SystemTypeOut` database model.
        """

        # Stored usage statuses
        for i in range(0, len(spares_definition_in_data["system_type_ids"])):
            ServiceTestHelpers.mock_get(
                self.mock_system_type_repository,
                SystemTypeOut(**system_types_out_data[i]) if system_types_out_data[i] else None,
            )

        self._spares_definition_in = SparesDefinitionIn(**spares_definition_in_data)

        # Upserted setting
        self._expected_spares_definition_out = MagicMock()
        self.mock_setting_repository.upsert.return_value = self._expected_spares_definition_out

        # Expected list of catalogue item IDs that need to be updated (actual values don't matter here)
        self._expected_catalogue_item_ids = [ObjectId(), ObjectId()]
        self.mock_catalogue_item_repository.list_ids.return_value = self._expected_catalogue_item_ids

    def call_set_spares_definition(self) -> None:
        """Calls the `SettingService` `set_spares_definition` method with the appropriate data from a prior call to
        `mock_set_spares_definition`."""

        self._updated_spares_definition = self.setting_service.set_spares_definition(self._spares_definition_in)

    def call_set_spares_definition_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `SettingService` `set_spares_definition` method with the appropriate data from a prior call to
        `mock_set_spares_definition while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.setting_service.set_spares_definition(self._spares_definition_in)
        self._set_spares_definition_exception = exc

    def check_set_spares_definition_success(self) -> None:
        """Checks that a prior call to `call_set_spares_definition` worked as expected."""

        # Ensure checked all of the system types
        self.mock_system_type_repository.get.assert_has_calls(
            [call(str(system_type_id)) for system_type_id in self._spares_definition_in.system_type_ids]
        )

        # Ensure started a transaction
        self.mock_start_session_transaction.assert_called_once_with("setting spares definition")
        expected_session = self.mock_start_session_transaction.return_value.__enter__.return_value

        # Ensure upserted with expected data
        self.mock_setting_repository.upsert.assert_called_once_with(
            self._spares_definition_in, SparesDefinitionOut, session=expected_session
        )

        # Ensure obtained list of all catalogue item ids recalculated the number of spares for each
        self.mock_catalogue_item_repository.list_ids.assert_called_once_with()

        expected_count_in_catalogue_item_with_system_type_one_of_calls = []
        expected_update_number_of_spares_calls = []
        for catalogue_item_id in self._expected_catalogue_item_ids:
            expected_count_in_catalogue_item_with_system_type_one_of_calls.append(
                call(catalogue_item_id, self._spares_definition_in.system_type_ids, session=expected_session)
            )
            expected_update_number_of_spares_calls.append(
                call(
                    catalogue_item_id,
                    self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.return_value,
                    session=expected_session,
                )
            )

        assert self._updated_spares_definition == self._expected_spares_definition_out

    def check_set_spares_definition_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_set_spares_definition_expecting_error` worked as expected, raising an
        exception with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_setting_repository.upsert.assert_not_called()

        assert str(self._set_spares_definition_exception.value) == message


class TestSetSparesDefinition(SetSparesDefinitionDSL):
    """Tests for setting the spares definition."""

    def test_set_spares_definition(self):
        """Test updating the spares definition."""

        self.mock_set_spares_definition(
            SETTING_SPARES_DEFINITION_IN_DATA_STORAGE_OR_OPERATIONAL,
            [SYSTEM_TYPE_OUT_DATA_STORAGE, SYSTEM_TYPE_OUT_DATA_OPERATIONAL],
        )
        self.call_set_spares_definition()
        self.check_set_spares_definition_success()

    def test_set_spares_definition_with_non_existent_system_type_id(self):
        """Test updating the spares definition with a non-existent system type ID."""

        self.mock_set_spares_definition(
            SETTING_SPARES_DEFINITION_IN_DATA_STORAGE_OR_OPERATIONAL, [SYSTEM_TYPE_OUT_DATA_STORAGE, None]
        )
        self.call_set_spares_definition_expecting_error(MissingRecordError)
        self.check_set_spares_definition_failed_with_exception(
            f"No system type found with ID: {self._spares_definition_in.system_type_ids[1]}"
        )


class GetSparesDefinitionDSL(SettingServiceDSL):
    """Base class for 'get_spares_definition' tests."""

    _expected_spares_definition: MagicMock
    _obtained_spares_definition: MagicMock

    def mock_get_spares_definition(self) -> None:
        """Mocks repo methods appropriately to test 'get_spares_definition' service method."""
        self._expected_spares_definition = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_setting_repository, self._expected_spares_definition)

    def call_get_spares_definition(self) -> None:
        """Calls the 'SettingService' 'get_spares_definition' method.
        :param setting_id: ID of the setting to be obtained
        """

        self._obtained_spares_definition = self.setting_service.get_spares_definition()

    def check_get_spares_definition_success(self):
        """Checks that a prior call to 'call_get_spares_definition' worked as expected"""
        self.mock_setting_repository.get.assert_called_once_with(SparesDefinitionOut)
        assert self._obtained_spares_definition == self._expected_spares_definition


class TestGetSparesDefinition(GetSparesDefinitionDSL):
    """Tests for getting the spares definition"""

    def test_get_spares_definition(self):
        """Test getting the spares definition"""

        self.mock_get_spares_definition()
        self.call_get_spares_definition()
        self.check_get_spares_definition_success()
