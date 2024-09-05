"""
Unit tests for the `UnitRepo` repository
"""

from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    UNIT_IN_DATA_CM,
    UNIT_IN_DATA_MM,
)
from test.unit.repositories.conftest import RepositoryTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfCatalogueCategoryError,
)
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.repositories.unit import UnitRepo


class UnitRepoDSL:
    """Base class for `UnitRepo` unit tests."""

    mock_database: Mock
    unit_repository: UnitRepo
    units_collection: Mock
    catalogue_categories_collection: Mock

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures"""
        self.mock_database = database_mock
        self.unit_repository = UnitRepo(database_mock)
        self.units_collection = database_mock.units
        self.catalogue_categories_collection = database_mock.catalogue_categories

        self.mock_session = MagicMock()
        yield

    def mock_is_duplicate_unit(self, duplicate_unit_in_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `_is_duplicate_unit` repo method will be called.

        :param duplicate_unit_in_data: Either `None` or a dictionary containing unit data for a duplicate unit.
        """
        RepositoryTestHelpers.mock_find_one(
            self.units_collection,
            ({**UnitIn(**duplicate_unit_in_data).model_dump(), "_id": ObjectId()} if duplicate_unit_in_data else None),
        )

    def get_is_duplicate_unit_expected_find_one_call(self, unit_in: UnitIn, expected_unit_id: Optional[CustomObjectId]):
        """
        Returns the expected `find_one` calls that should occur when `_is_duplicate_unit` is called.

        :param unit_in: `UnitIn` model containing the data about the unit.
        :param expected_unit_id: Expected `unit_id` provided to `_is_duplicate_unit`.
        :return: Expected `find_one` calls.
        """
        return call({"code": unit_in.code, "_id": {"$ne": expected_unit_id}}, session=self.mock_session)


class CreateDSL(UnitRepoDSL):
    """Base class for `create` tests."""

    _unit_in: UnitIn
    _expected_unit_out: UnitOut
    _created_unit: UnitOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(self, unit_in_data: dict, duplicate_unit_in_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately to test the `create` repo method.

        :param unit_in_data: Dictionary containing the unit data as would be required for a
            `UnitIn` database model (i.e. no ID or created and modified times required).
        :param duplicate_unit_in_data: Either `None` or a dictionary containing unit data for a
            duplicate unit.
        """
        inserted_unit_id = CustomObjectId(str(ObjectId()))

        # Pass through UnitIn first as need creation and modified times
        self._unit_in = UnitIn(**unit_in_data)

        self._expected_unit_out = UnitOut(**self._unit_in.model_dump(), id=inserted_unit_id)

        self.mock_is_duplicate_unit(duplicate_unit_in_data)
        # Mock `insert one` to return object for inserted unit
        RepositoryTestHelpers.mock_insert_one(self.units_collection, inserted_unit_id)
        # Mock `find_one` to return the inserted unit document
        RepositoryTestHelpers.mock_find_one(
            self.units_collection, {**self._unit_in.model_dump(), "_id": inserted_unit_id}
        )

    def call_create(self) -> None:
        """Calls the `UnitRepo` `create` method with the appropriate data from a prior call to `mock_create`."""
        self._created_unit = self.unit_repository.create(self._unit_in, session=self.mock_session)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `UnitRepo` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.unit_repository.create(self._unit_in, session=self.mock_session)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""
        unit_in_data = self._unit_in.model_dump()

        # Obtain a list of expected find_one calls
        expected_find_one_calls = [
            # This is the check for the duplicate
            self.get_is_duplicate_unit_expected_find_one_call(self._unit_in, None),
            # This is the check for the newly inserted unit get
            call({"_id": CustomObjectId(self._expected_unit_out.id)}, session=self.mock_session),
        ]
        self.units_collection.insert_one.assert_called_once_with(unit_in_data, session=self.mock_session)
        self.units_collection.find_one.assert_has_calls(expected_find_one_calls)

        assert self._created_unit == self._expected_unit_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """
        self.units_collection.insert_one.assert_not_called()
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a unit."""

    def test_create(self):
        """Test creating a unit."""
        self.mock_create(UNIT_IN_DATA_MM)
        self.call_create()
        self.check_create_success()

    def test_create_with_duplicate_name(self):
        """Test creating a unit with a duplicate unit being found."""
        self.mock_create(UNIT_IN_DATA_MM, duplicate_unit_in_data=UNIT_IN_DATA_MM)
        self.call_create_expecting_error(DuplicateRecordError)
        self.check_create_failed_with_exception("Duplicate unit found")


class GetDSL(UnitRepoDSL):
    """Base class for `get` tests."""

    _obtained_unit_id: str
    _expected_unit_out: Optional[UnitOut]
    _obtained_unit_out: UnitOut
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, unit_id: str, unit_in_data: Optional[dict]) -> None:
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param unit_id: ID of the unit to be obtained.
        :param unit_in_data: Either `None` or a dictionary containing the unit data as would be required
            for a `UnitIn` database model (i.e. no ID or created and modified times required).
        """
        self._expected_unit_out = (
            UnitOut(**UnitIn(**unit_in_data).model_dump(), id=CustomObjectId(unit_id)) if unit_in_data else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.units_collection,
            self._expected_unit_out.model_dump() if self._expected_unit_out else None,
        )

    def call_get(self, unit_id: str) -> None:
        """
        Calls the `UnitRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param unit_id: ID of the unit to be obtained.
        """
        self._obtained_unit_id = unit_id
        self._obtained_unit_out = self.unit_repository.get(unit_id, session=self.mock_session)

    def call_get_expecting_error(self, unit_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `UnitRepo` `get` method with the appropriate data from a prior call to `mock_get` while
        expecting an error to be raised.

        :param unit_id: ID of the unit to be obtained.
        :param error_type: Expected exception to be raised.
        """
        with pytest.raises(error_type) as exc:
            self.unit_repository.get(unit_id, session=self.mock_session)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""
        self.units_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_unit_id)}, session=self.mock_session
        )
        assert self._obtained_unit_out == self._expected_unit_out

    def check_get_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception with the correct
        message.

        :param message: Expected message of the raised exception.
        """
        self.units_collection.find_one.assert_not_called()
        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a unit."""

    def test_get(self):
        """Test getting a unit."""
        unit_id = str(ObjectId())

        self.mock_get(unit_id, UNIT_IN_DATA_MM)
        self.call_get(unit_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Testing getting a unit with a non-existent ID."""
        unit_id = str(ObjectId())

        self.mock_get(unit_id, None)
        self.call_get(unit_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting a unit with an invalid ID."""
        unit_id = "invalid-id"

        self.call_get_expecting_error(unit_id, InvalidObjectIdError)
        self.check_get_failed_with_exception(f"Invalid ObjectId value '{unit_id}'")


class ListDSL(UnitRepoDSL):
    """Base class for `list` tests."""

    _expected_units_out: list[UnitOut]
    _obtained_units_out: list[UnitOut]

    def mock_list(self, units_in_data: list[dict]) -> None:
        """
        Mocks database methods appropriately to test the `list` repo method.

        :param units_in_data: List of dictionaries containing the unit data as would be required for a
            `UnitIn` database model (i.e. no ID or created and modified times required).
        """
        self._expected_units_out = [
            UnitOut(**UnitIn(**unit_in_data).model_dump(), id=ObjectId()) for unit_in_data in units_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.units_collection,
            [unit_out.model_dump() for unit_out in self._expected_units_out],
        )

    def call_list(self) -> None:
        """Calls the `UnitRepo` `list method` method."""
        self._obtained_units_out = self.unit_repository.list(session=self.mock_session)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""
        self.units_collection.find.assert_called_once_with(session=self.mock_session)
        assert self._obtained_units_out == self._expected_units_out


class TestList(ListDSL):
    """Tests for listing units."""

    def test_list(self):
        """Test listing all units."""
        self.mock_list([UNIT_IN_DATA_MM, UNIT_IN_DATA_CM])
        self.call_list()
        self.check_list_success()

    def test_list_with_no_results(self):
        """Test listing all units returning no results."""
        self.mock_list([])
        self.call_list()
        self.check_list_success()


class DeleteDSL(UnitRepoDSL):
    """Base class for `delete` tests."""

    _delete_unit_id: str
    _delete_exception: pytest.ExceptionInfo
    _mock_catalogue_category_data: Optional[dict]

    def mock_delete(self, deleted_count: int, catalogue_category_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        :param catalogue_item_data: Dictionary containing a catalogue item's data (or `None`).
        """
        self.mock_is_unit_in_catalogue_category(catalogue_category_data)
        RepositoryTestHelpers.mock_delete_one(self.units_collection, deleted_count)

    def call_delete(self, unit_id: str) -> None:
        """
        Calls the `UnitRepo` `delete` method with the appropriate data from a prior call to `mock_delete`.

        :param unit_id: ID of the unit to be deleted.
        """
        self._delete_unit_id = unit_id
        self.unit_repository.delete(unit_id, session=self.mock_session)

    def call_delete_expecting_error(self, unit_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `UnitRepo` `delete` method with the appropriate data from a prior call to `mock_delete` while
        expecting an error to be raised.

        :param unit_id: ID of the unit to be deleted.
        :param error_type: Expected exception to be raised.
        """
        self._delete_unit_id = unit_id
        with pytest.raises(error_type) as exc:
            self.unit_repository.delete(unit_id, session=self.mock_session)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""
        self.check_is_unit_in_catalogue_item_performed_expected_calls(self._delete_unit_id)
        self.units_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_unit_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """
        if not expecting_delete_one_called:
            self.units_collection.delete_one.assert_not_called()
        else:
            self.units_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_unit_id)}, session=self.mock_session
            )

        assert str(self._delete_exception.value) == message

    def mock_is_unit_in_catalogue_category(self, catalogue_category_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `_is_unit_in_catalogue_item` repo method will be
        called.

        :param catalogue_category_data: Dictionary containing a catalogue category's data (or `None`).
        """
        self._mock_catalogue_category_data = catalogue_category_data
        RepositoryTestHelpers.mock_find_one(self.catalogue_categories_collection, catalogue_category_data)

    def check_is_unit_in_catalogue_item_performed_expected_calls(self, expected_unit_id: str) -> None:
        """Checks that a call to `_is_unit_in_catalogue_item` performed the expected method calls.

        :param expected_unit_id: Expected unit ID used in the database calls.
        """
        self.catalogue_categories_collection.find_one.assert_called_once_with(
            {"properties.unit_id": CustomObjectId(expected_unit_id)}, session=self.mock_session
        )


class TestDelete(DeleteDSL):
    """Tests for deleting a unit."""

    def test_delete(self):
        """Test deleting a unit."""
        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_when_part_of_catalogue_category(self):
        """Test deleting a unit when it is part of a catalogue category."""
        unit_id = str(ObjectId())

        self.mock_delete(
            deleted_count=1,
            catalogue_category_data={
                **CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
                "properties": [
                    {
                        **CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
                        "unit_id": unit_id,
                    }
                ],
            },
        )
        self.call_delete_expecting_error(unit_id, PartOfCatalogueCategoryError)
        self.check_delete_failed_with_exception(f"The unit with ID {unit_id} is a part of a Catalogue category")

    def test_delete_non_existent_id(self):
        """Test deleting a unit with a non-existent ID."""
        unit_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(unit_id, MissingRecordError)
        self.check_delete_failed_with_exception(f"No unit found with ID: {unit_id}", expecting_delete_one_called=True)

    def test_delete_with_invalid_id(self):
        """Test deleting a unit with an invalid ID."""
        unit_id = "invalid-id"

        self.call_delete_expecting_error(unit_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception(f"Invalid ObjectId value '{unit_id}'")
