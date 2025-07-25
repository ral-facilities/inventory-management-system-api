"""
Unit tests for the `SettingRepo` repository.
"""

from test.mock_data import SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import ClassVar, Optional, Type
from unittest.mock import MagicMock, Mock

import pytest

from inventory_management_system_api.models.setting import SettingOutBase, SparesDefinitionOut
from inventory_management_system_api.repositories.setting import SettingOutBaseT, SettingRepo


class ExampleSettingOut(SettingOutBase):
    """Test setting."""

    SETTING_ID: ClassVar[str] = "test_setting_id"


class SettingRepoDSL:
    """Base class for `SettingRepo` unit tests."""

    mock_database: Mock
    setting_repo: SettingRepo
    settings_collection: Mock

    mock_session = MagicMock

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures."""

        self.mock_database = database_mock
        self.setting_repo = SettingRepo(database_mock)
        self.settings_collection = database_mock.settings

        self.mock_session = MagicMock()


class GetDSL(SettingRepoDSL):
    """Base class for `get` tests."""

    _obtained_out_model_type: Type[SettingOutBaseT]
    _expected_setting_out: SettingOutBaseT
    _obtained_setting: Optional[SettingOutBaseT]

    def mock_get(self, out_model_type: Type[SettingOutBaseT], setting_out_data: Optional[dict]) -> None:
        """
        Mocks database methods appropriately  to test the `get` repo method.

        :param out_model_type: The type of the setting's output model to be obtained.
        :param setting_out_data: Either `None` or a dictionary containing the setting data as would be required for the
                                 setting's `Out` database model.
        """
        self._expected_setting_out = out_model_type(**setting_out_data) if setting_out_data is not None else None

        RepositoryTestHelpers.mock_find_one(
            self.settings_collection, self._expected_setting_out.model_dump() if self._expected_setting_out else None
        )

    def call_get(self, out_model_type: Type[SettingOutBaseT]) -> None:
        """Calls the `SettingRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param out_model_type: The type of the setting's output model to be obtained.
        """

        self._obtained_out_model_type = out_model_type
        self._obtained_setting = self.setting_repo.get(out_model_type, session=self.mock_session)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.settings_collection.find_one.assert_called_once_with(
            {"_id": self._obtained_out_model_type.SETTING_ID}, session=self.mock_session
        )
        assert self._obtained_setting == self._expected_setting_out


class TestGet(GetDSL):
    """Tests for getting a setting."""

    def test_get(self):
        """Test getting a setting."""

        self.mock_get(ExampleSettingOut, {"_id": ExampleSettingOut.SETTING_ID})
        self.call_get(ExampleSettingOut)
        self.check_get_success()

    def test_get_non_existent(self):
        """Test getting a setting that is non-existent."""

        self.mock_get(ExampleSettingOut, None)
        self.call_get(ExampleSettingOut)
        self.check_get_success()

    def test_get_spares_definition(self):
        """Test getting the spares definition setting."""

        self.mock_get(SparesDefinitionOut, SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE)
        self.call_get(SparesDefinitionOut)
        self.check_get_success()

    def test_get_spares_definition_when_non_existent(self):
        """Test getting the spares definition setting when it is non-existent."""

        self.mock_get(SparesDefinitionOut, None)
        self.call_get(SparesDefinitionOut)
        self.check_get_success()
