"""
Unit tests for the `SettingRepo` repository.
"""

from test.mock_data import SETTING_SPARES_DEFINITION_IN_DATA_NEW_USED, SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import ClassVar, Optional, Type
from unittest.mock import MagicMock, Mock

import pytest

from inventory_management_system_api.models.setting import (
    SettingInBase,
    SettingOutBase,
    SparesDefinitionIn,
    SparesDefinitionOut,
)
from inventory_management_system_api.repositories.setting import (
    SPARES_DEFINITION_GET_AGGREGATION_PIPELINE,
    SettingInBaseT,
    SettingOutBaseT,
    SettingRepo,
)


class ExampleSettingIn(SettingInBase):
    """Test setting."""

    SETTING_ID: ClassVar[str] = "test_setting_id"


class ExampleSettingOut(ExampleSettingIn, SettingOutBase):
    """Test setting."""


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


class UpsertDSL(SettingRepoDSL):
    """Base class for `upsert` tests."""

    _setting_in: SettingInBaseT
    _out_model_type: Type[SettingOutBaseT]
    _expected_setting_out: SettingOutBaseT
    _upserted_setting_in: SettingInBaseT
    _upserted_setting: SettingOutBaseT

    def mock_upsert(
        self,
        new_setting_in_data: dict,
        new_setting_out_data: dict,
        in_model_type: Type[SettingInBaseT],
        out_model_type: Type[SettingOutBaseT],
    ) -> None:
        """
        Mocks database methods appropriately to test the `upsert` repo method.

        :param new_setting_in_data: Dictionary containing the new setting data as would be required for a
                                    `SettingInBase` database model.
        :param new_setting_out_data: Dictionary containing the new setting data as would be required for a
                                    `SettingOutBase` database model.
        :param in_model_type: The type of the setting's input model.
        :param out_model_type: The type of the setting's output model.
        """

        self._setting_in = in_model_type(**new_setting_in_data)
        self._out_model_type = out_model_type

        self._expected_setting_out = out_model_type(**new_setting_out_data)

        RepositoryTestHelpers.mock_find_one(self.settings_collection, new_setting_out_data)

        if out_model_type is SparesDefinitionOut:
            self.settings_collection.aggregate.return_value = [new_setting_out_data]

    def call_upsert(self) -> None:
        """Calls the `SettingRepo` `upsert` method with the appropriate data from a prior call to `mock_upsert`."""

        self._upserted_setting = self.setting_repo.upsert(
            self._setting_in, self._out_model_type, session=self.mock_session
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

    def test_upsert(self):
        """Test upserting a setting."""

        self.mock_upsert({"_id": "example_setting"}, {"_id": "example_setting"}, ExampleSettingIn, ExampleSettingOut)
        self.call_upsert()
        self.check_upsert_success()

    def test_upsert_spares_definition(self):
        """Test upserting the spares definition setting."""

        self.mock_upsert(
            SETTING_SPARES_DEFINITION_IN_DATA_NEW_USED,
            SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED,
            SparesDefinitionIn,
            SparesDefinitionOut,
        )
        self.call_upsert()
        self.check_upsert_success()


class GetDSL(SettingRepoDSL):
    """Base class for `get` tests."""

    _obtained_out_model_type: Type[SettingOutBaseT]
    _expected_setting_out: SettingOutBaseT
    _expect_return_before_aggregate: bool
    _obtained_setting: Optional[SettingOutBaseT]

    def mock_get(
        self,
        out_model_type: Type[SettingOutBaseT],
        setting_database_data: Optional[dict],
        setting_out_data: Optional[dict],
    ) -> None:
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param out_model_type: The type of the setting's output model to be obtained.
        :param setting_database_data: Either `None` or a dictionary containing the setting data as would be returned
                                      by a `find_one` query.
        :param setting_out_data: Either `None` or a dictionary containing the setting data as would be required for the
                                 `Out` database model.
        """
        self._expected_setting_out = out_model_type(**setting_out_data) if setting_out_data is not None else None
        self._expect_return_before_aggregate = setting_database_data is None or (
            len(setting_database_data.keys()) == 2 and "_lock" in setting_database_data
        )

        RepositoryTestHelpers.mock_find_one(self.settings_collection, setting_database_data)

        if out_model_type is SparesDefinitionOut:
            self.settings_collection.aggregate.return_value = [setting_out_data] if setting_out_data is not None else []

    def call_get(self, out_model_type: Type[SettingOutBaseT]) -> None:
        """
        Calls the `SettingRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param out_model_type: The type of the setting's output model to be obtained.
        """

        self._obtained_out_model_type = out_model_type
        self._obtained_setting = self.setting_repo.get(out_model_type, session=self.mock_session)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.settings_collection.find_one.assert_called_once_with(
            {"_id": self._obtained_out_model_type.SETTING_ID}, session=self.mock_session
        )

        if not self._expect_return_before_aggregate:
            if self._obtained_out_model_type is SparesDefinitionOut:
                self.settings_collection.aggregate.assert_called_once_with(
                    SPARES_DEFINITION_GET_AGGREGATION_PIPELINE, session=self.mock_session
                )

        assert self._obtained_setting == self._expected_setting_out


class TestGet(GetDSL):
    """Tests for getting a setting."""

    def test_get(self):
        """Test getting a setting."""

        self.mock_get(ExampleSettingOut, {"_id": "example_setting"}, {"_id": "example_setting"})
        self.call_get(ExampleSettingOut)
        self.check_get_success()

    def test_get_non_existent(self):
        """Test getting a setting that is non-existent."""

        self.mock_get(ExampleSettingOut, None, None)
        self.call_get(ExampleSettingOut)
        self.check_get_success()

    def test_get_existent_but_not_assigned(self):
        """Test getting a setting that is existent but only due to a write lock."""

        self.mock_get(ExampleSettingOut, {"_id": "example_setting", "_lock": None}, None)
        self.call_get(ExampleSettingOut)
        self.check_get_success()

    def test_get_spares_definition(self):
        """Test getting the spares definition setting."""

        self.mock_get(
            SparesDefinitionOut,
            SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED,
            SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED,
        )
        self.call_get(SparesDefinitionOut)
        self.check_get_success()

    def test_get_non_existent_spares_definition(self):
        """Test getting the spares definition setting when it is non-existent."""

        self.mock_get(SparesDefinitionOut, None, None)
        self.call_get(SparesDefinitionOut)
        self.check_get_success()

    def test_get_existent_spares_definition_but_not_assinged(self):
        """Test getting the spares definition setting when it is existent but only due to a write lock."""

        self.mock_get(
            SparesDefinitionOut, {"_id": SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED["_id"], "_lock": None}, None
        )
        self.call_get(SparesDefinitionOut)
        self.check_get_success()


class WriteLockDSL(SettingRepoDSL):
    """Base class for `write_lock` tests."""

    _write_lock_out_model_type: Type[SettingOutBaseT]

    def call_write_lock(self, out_model_type: Type[SettingOutBaseT]) -> None:
        """
        Calls the `SettingRepo` `write_lock` method with the appropriate data from a prior call to `mock_get`.

        :param out_model_type: The type of the setting's output model to be obtained.
        """

        self._write_lock_out_model_type = out_model_type
        self.setting_repo.write_lock(out_model_type, self.mock_session)

    def check_write_lock_success(self) -> None:
        """Checks that a prior call to `call_write_lock` worked as expected."""

        self.settings_collection.update_one.assert_called_once_with(
            {"_id": self._write_lock_out_model_type.SETTING_ID},
            {"$set": {"_lock": None}},
            upsert=True,
            session=self.mock_session,
        )


class TestWriteLock(WriteLockDSL):
    """Tests for write locking a setting."""

    def test_write_lock(self):
        """Test write locking a setting."""

        self.call_write_lock(ExampleSettingOut)
        self.check_write_lock_success()
