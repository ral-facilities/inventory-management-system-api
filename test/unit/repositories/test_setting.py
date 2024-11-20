"""
Unit tests for the `SettingRepo` repository.
"""

from test.mock_data import SETTING_SPARES_DEFINITION_IN_DATA, USAGE_STATUS_IN_DATA_NEW
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import ClassVar, Optional, Type
from unittest.mock import MagicMock, Mock

import pytest

from inventory_management_system_api.models.setting import BaseSetting, SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.repositories.setting import (
    SPARES_DEFINITION_GET_AGGREGATION_PIPELINE,
    BaseSettingT,
    SettingRepo,
)


class SettingRepoDSL:
    """Base class for `SettingRepo` unit tests."""

    mock_database: Mock
    setting_repo: SettingRepo
    settings_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures."""

        self.mock_database = database_mock
        self.setting_repo = SettingRepo(database_mock)
        self.settings_collection = database_mock.settings

        self.mock_session = MagicMock()


class GetDSL(SettingRepoDSL):
    """Base class for `get` tests."""

    _obtained_output_model_type: Type[BaseSettingT]
    _expected_setting_out: BaseSettingT
    _obtained_setting: Optional[BaseSetting]

    def mock_get(
        self,
        output_model_type: Type[BaseSettingT],
        setting_in_data: Optional[dict],
        usage_statuses_in_data: Optional[list[dict]] = None,
    ) -> None:
        # TODO: Update comment
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param output_model_type: The output type of the setting's model to be obtained.
        :param setting_in_data: Either `None` or a dictionary containing the setting data as would be required for the
                               `In` database model.
        """

        # TODO: Just use out data instead on in to save having to complicate this logic
        if output_model_type is SparesDefinitionOut:
            # Expected output also needs usage status data for each given usage status so insert that data here
            setting_out_data = (
                {
                    **setting_in_data,
                    "usage_statuses": [
                        {
                            **UsageStatusOut(
                                **UsageStatusIn(**usage_statuses_in_data[i]).model_dump(), **usage_status_in_data
                            ).model_dump(),
                        }
                        for i, usage_status_in_data in enumerate(setting_in_data["usage_statuses"])
                    ],
                }
                if setting_in_data is not None
                else None
            )
        else:
            setting_out_data = setting_in_data

        self._expected_setting_out = output_model_type(**setting_out_data) if setting_out_data is not None else None

        if output_model_type is SparesDefinitionOut:
            self.settings_collection.aggregate.return_value = [setting_out_data] if setting_out_data is not None else []
        else:
            RepositoryTestHelpers.mock_find_one(
                self.settings_collection,
                (
                    self._expected_setting_out.model_dump(by_alias=True)
                    if self._expected_setting_out is not None
                    else None
                ),
            )

    def call_get(self, output_model_type: Type[BaseSettingT]) -> None:
        """
        Calls the `SettingRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param output_model_type: The output type of the setting's model to be obtained.
        """

        self._obtained_output_model_type = output_model_type
        self._obtained_setting = self.setting_repo.get(output_model_type, session=self.mock_session)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        if self._obtained_output_model_type is SparesDefinitionOut:
            self.settings_collection.aggregate.assert_called_once_with(SPARES_DEFINITION_GET_AGGREGATION_PIPELINE)
        else:
            self.settings_collection.find_one.assert_called_once_with(
                {"_id": self._obtained_output_model_type.SETTING_ID}, session=self.mock_session
            )

        assert self._obtained_setting == self._expected_setting_out


class TestGet(GetDSL):
    """Tests for getting a setting."""

    class TestSettingOut(BaseSetting):
        """Test setting"""

        SETTING_ID: ClassVar[str] = "test_setting_id"

    def test_get(self):
        """Test getting a setting."""

        self.mock_get(self.TestSettingOut, {"setting": "data"})
        self.call_get(self.TestSettingOut)
        self.check_get_success()

    def test_get_non_existent(self):
        """Test getting a setting that is non-existent."""

        self.mock_get(self.TestSettingOut, None)
        self.call_get(self.TestSettingOut)
        self.check_get_success()

    def test_get_spares_definition(self):
        """Test getting the spares definition setting."""

        self.mock_get(SparesDefinitionOut, SETTING_SPARES_DEFINITION_IN_DATA, [USAGE_STATUS_IN_DATA_NEW])
        self.call_get(SparesDefinitionOut)
        self.check_get_success()

    def test_get_non_existent_spares_definition(self):
        """Test getting the spares definition setting when it is non-existent."""

        self.mock_get(SparesDefinitionOut, None)
        self.call_get(SparesDefinitionOut)
        self.check_get_success()


class UpsertDSL(SettingRepoDSL):
    """Base class for `upsert` tests."""

    _setting_in: BaseSetting
    _output_model_type: BaseSetting
    _expected_setting_out: BaseSettingT
    _upserted_setting_in: BaseSetting
    _upserted_setting: BaseSettingT

    def mock_upsert(
        self,
        new_setting_in: dict,
        output_model_type: Type[BaseSettingT],
        new_usage_statuses_in_data: Optional[list[dict]],
    ) -> None:
        # TODO: Comment

        self._setting_in = new_setting_in
        self._output_model_type = output_model_type

        # TODO: Combine this into function in base repo DSL rather than repeating in get below
        setting_in_data = new_setting_in.model_dump()
        if output_model_type is SparesDefinitionOut:
            # Expected output also needs usage status data for each given usage status so insert that data here
            setting_out_data = {
                **setting_in_data,
                "usage_statuses": [
                    {
                        **UsageStatusOut(
                            **UsageStatusIn(**new_usage_statuses_in_data[i]).model_dump(), **usage_status_in_data
                        ).model_dump(),
                    }
                    for i, usage_status_in_data in enumerate(setting_in_data["usage_statuses"])
                ],
            }
        else:
            setting_out_data = setting_in_data

        self._expected_setting_out = output_model_type(**setting_out_data) if setting_out_data is not None else None

        # TODO: Again unify with below - perhaps inherit Get for this? - what about other tests?
        if output_model_type is SparesDefinitionOut:
            self.settings_collection.aggregate.return_value = [setting_out_data] if setting_out_data is not None else []
        else:
            RepositoryTestHelpers.mock_find_one(
                self.settings_collection,
                (
                    self._expected_setting_out.model_dump(by_alias=True)
                    if self._expected_setting_out is not None
                    else None
                ),
            )

    def call_upsert(self) -> None:
        # TODO: Comment

        self._upserted_setting = self.setting_repo.upsert(
            self._setting_in, self._output_model_type, session=self.mock_session
        )

    def check_upsert_success(self) -> None:
        """Checks that a prior call to `call_upsert` worked as expected."""

        self.settings_collection.update_one.assert_called_once_with(
            {"_id": self._setting_in.SETTING_ID},
            {"$set": self._setting_in.model_dump(by_alias=True)},
            upsert=True,
            session=self.mock_session,
        )

        assert self._upserted_setting == self._expected_setting_out


class TestUpdate(UpsertDSL):
    """Tests for upserting a setting."""

    # TODO: Test that isn't the spares definition
    def test_upsert(self):
        # TODO: Comment

        self.mock_upsert(
            SparesDefinitionIn(**SETTING_SPARES_DEFINITION_IN_DATA), SparesDefinitionOut, [USAGE_STATUS_IN_DATA_NEW]
        )
        self.call_upsert()
        self.check_upsert_success()
