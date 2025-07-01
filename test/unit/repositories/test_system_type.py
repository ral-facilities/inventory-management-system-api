"""
Unit tests for the `SystemTypeRepo` repository.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import SYSTEM_TYPES_OUT_DATA
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.repositories.system_type import SystemTypeRepo


class SystemTypeRepoDSL:
    """Base class for `SystemTypeRepo` unit tests."""

    mock_database: Mock
    system_type_repository: SystemTypeRepo
    system_types_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures."""

        self.mock_database = database_mock
        self.system_type_repository = SystemTypeRepo(database_mock)
        self.system_types_collection = database_mock.system_types


class GetDSL(SystemTypeRepoDSL):
    """Base class for `get` tests."""

    _obtained_system_type_id: str
    _expected_system_type_out: Optional[SystemTypeOut]
    _obtained_system_type: Optional[SystemTypeOut]
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, system_type_out_data: Optional[dict]) -> None:
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param system_type_out_data: Either `None` or a dictionary containing the system type data as would be required
                                     for a `SystemTypeOut` database model.
        """

        self._expected_system_type_out = SystemTypeOut(**system_type_out_data) if system_type_out_data else None

        RepositoryTestHelpers.mock_find_one(self.system_types_collection, system_type_out_data)

    def call_get(self, system_type_id: str) -> None:
        """
        Calls the `SystemTypeRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param system_type_id: ID of the system type to be obtained.
        """

        self._obtained_system_type_id = system_type_id
        self._obtained_system_type = self.system_type_repository.get(system_type_id, session=self.mock_session)

    def call_get_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemTypeRepo` `get` method with the appropriate data from a prior call to `mock_get`
        while expecting an error to be raised.

        :param system_type_id: ID of the system type to be obtained.
        :param error_type: Expected exception to be raised.
        """

        self._obtained_system_type_id = system_id
        with pytest.raises(error_type) as exc:
            self.system_type_repository.get(system_id)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.system_types_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_system_type_id)}, session=self.mock_session
        )
        assert self._obtained_system_type == self._expected_system_type_out

    def check_get_failed_with_exception(self, message: str, assert_find: bool = False) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        :param assert_find: If `True` it asserts whether a `find_one` call was made, else it asserts that no call was
                            made.
        """

        if assert_find:
            self.system_types_collection.find_one.assert_called_once_with(
                {"_id": CustomObjectId(self._obtained_system_type_id)}, session=None
            )
        else:
            self.system_types_collection.find_one.assert_not_called()

        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a system type."""

    def test_get(self):
        """Test getting a system type."""

        system_type_id = str(SYSTEM_TYPES_OUT_DATA[0]["_id"])

        self.mock_get(SYSTEM_TYPES_OUT_DATA[0])
        self.call_get(system_type_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Test getting a system type with a non-existent ID."""

        system_type_id = str(ObjectId())

        self.mock_get(None)
        self.call_get_expecting_error(system_type_id, MissingRecordError)
        self.check_get_failed_with_exception(f"No system type found with ID: {system_type_id}", assert_find=True)

    def test_get_with_invalid_id(self):
        """Test getting a system type with an invalid ID."""

        system_type_id = "invalid-id"

        self.call_get_expecting_error(system_type_id, InvalidObjectIdError)
        self.check_get_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class ListDSL(SystemTypeRepoDSL):
    """Base class for `list` tests."""

    _expected_systems_types_out: list[SystemTypeOut]
    _obtained_system_types_out: list[SystemTypeOut]

    def mock_list(self, system_types_out_data: list[dict]):
        """
        Mocks database methods appropriately to test the `list` repo method.

        :param system_types_out_data: List of dictionaries containing the system type data as would be required for a
                                      `SystemTypeOut` database model.
        """

        self._expected_systems_types_out = [
            SystemTypeOut(**system_type_out_data) for system_type_out_data in system_types_out_data
        ]
        RepositoryTestHelpers.mock_find(self.system_types_collection, system_types_out_data)

    def call_list(self):
        """Calls the `SystemTypeRepo` `list` method."""

        self._obtained_system_types_out = self.system_type_repository.list(session=self.mock_session)

    def check_list_success(self):
        """Checks that a prior call to `call_list` worked as expected."""

        self.system_types_collection.find.assert_called_once_with(session=self.mock_session)
        assert self._obtained_system_types_out == self._expected_systems_types_out


class TestList(ListDSL):
    """Tests for listing system types."""

    def test_list(self):
        """Test listing all system types."""

        self.mock_list(SYSTEM_TYPES_OUT_DATA)
        self.call_list()
        self.check_list_success()

    def test_list_with_no_results(self):
        """Test listing all system types returning no results."""

        self.mock_list([])
        self.call_list()
        self.check_list_success()
