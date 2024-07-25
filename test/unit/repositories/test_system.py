"""
Unit tests for the `SystemRepo` repository
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import SYSTEM_IN_DATA_NO_PARENT_A, SYSTEM_IN_DATA_NO_PARENT_B
from test.unit.repositories.conftest import RepositoryTestHelpers
from test.unit.repositories.test_utils import (
    MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH,
    MOCK_MOVE_QUERY_RESULT_INVALID,
    MOCK_MOVE_QUERY_RESULT_VALID,
)
from test.unit.services.test_item import ITEM_INFO
from typing import Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DuplicateRecordError,
    InvalidActionError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories.system import SystemRepo


class SystemRepoDSL:
    """Base class for `SystemRepo` unit tests."""

    # pylint:disable=too-many-instance-attributes
    mock_database: Mock
    mock_utils: Mock
    system_repository: SystemRepo
    systems_collection: Mock
    items_collection: Mock

    mock_session = MagicMock()

    # Internal data for utility functions
    _mock_child_system_data: Optional[dict]
    _mock_child_item_data: Optional[dict]

    @pytest.fixture(autouse=True)
    def setup(self, database_mock):
        """Setup fixtures"""

        self.mock_database = database_mock
        self.system_repository = SystemRepo(database_mock)
        self.systems_collection = database_mock.systems
        self.items_collection = database_mock.items

        self.mock_session = MagicMock()

        # Here we only wrap the utils so they keep their original functionality - this is done here
        # to avoid having to mock the code generation function as the output will be passed to `SystemOut`
        # with pydantic validation and so will error otherwise
        with patch("inventory_management_system_api.repositories.system.utils") as mock_utils:
            self.mock_utils = mock_utils
            yield

    def mock_has_child_elements(
        self, child_system_data: Optional[dict] = None, child_item_data: Optional[dict] = None
    ) -> None:
        """
        Mocks database methods appropriately for when the `_has_child_elements` repo method will be called.

        :param child_system_data: Dictionary containing a child system's data (or `None`).
        :param child_catalogue_item_data: Dictionary containing a child Item's data (or `None`).
        """

        self._mock_child_system_data = child_system_data
        self._mock_child_item_data = child_item_data

        RepositoryTestHelpers.mock_find_one(self.systems_collection, child_system_data)
        RepositoryTestHelpers.mock_find_one(self.items_collection, child_item_data)

    def check_has_child_elements_performed_expected_calls(self, expected_system_id: str) -> None:
        """
        Checks that a call to `_has_child_elements` performed the expected function calls.

        :param expected_system_id: Expected `system_id` used in the database calls.
        """

        self.systems_collection.find_one.assert_called_once_with(
            {"parent_id": CustomObjectId(expected_system_id)}, session=self.mock_session
        )
        # Will only call the second one if the first doesn't return anything
        if not self._mock_child_item_data:
            self.items_collection.find_one.assert_called_once_with(
                {"system_id": CustomObjectId(expected_system_id)}, session=self.mock_session
            )

    def mock_is_duplicate_system(self, duplicate_system_in_data: Optional[dict] = None) -> None:
        """
        Mocks database methods appropriately for when the `_is_duplicate_system` repo method will be called.

        :param duplicate_system_in_data: Either `None` or a dictionary containing system data for a duplicate system.
        """

        RepositoryTestHelpers.mock_find_one(
            self.systems_collection,
            (
                {**SystemIn(**duplicate_system_in_data).model_dump(), "_id": ObjectId()}
                if duplicate_system_in_data
                else None
            ),
        )

    def get_is_duplicate_system_expected_find_one_call(
        self, system_in: SystemIn, expected_system_id: Optional[CustomObjectId]
    ):
        """
        Returns the expected `find_one` calls from that should occur when `_is_duplicate_system` is called.

        :param system_in: `SystemIn` model containing the data about the system.
        :param expected_system_id: Expected `system_id` provided to `is_duplicate_system`.
        """

        return call(
            {
                "parent_id": system_in.parent_id,
                "code": system_in.code,
                "_id": {"$ne": expected_system_id},
            },
            session=self.mock_session,
        )


class CreateDSL(SystemRepoDSL):
    """Base class for `create` tests."""

    _system_in: SystemIn
    _expected_system_out: SystemOut
    _created_system: SystemOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        system_in_data: dict,
        parent_system_in_data: Optional[dict] = None,
        duplicate_system_in_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks database methods appropriately to test the `create` repo method.

        :param system_in_data: Dictionary containing the system data as would be required for a `SystemIn` database
                               model (i.e. no ID or created and modified times required).
        :param parent_system_in_data: Either `None` or a dictionary containing the parent system data as would be
                                      required for a `SystemIn` database model.
        :param duplicate_system_in_data: Either `None` or a dictionary containing system data for a duplicate system.
        """
        inserted_system_id = CustomObjectId(str(ObjectId()))

        # Pass through `SystemIn` first as need creation and modified times
        self._system_in = SystemIn(**system_in_data)

        self._expected_system_out = SystemOut(**self._system_in.model_dump(), id=inserted_system_id)

        # When a parent_id is given, need to mock the find_one for it too
        if system_in_data["parent_id"]:
            # If parent_system_data is given as None, then it is intentionally supposed to be, otherwise
            # pass through SystemIn first to ensure it has creation and modified times
            RepositoryTestHelpers.mock_find_one(
                self.systems_collection,
                (
                    {**SystemIn(**parent_system_in_data).model_dump(), "_id": system_in_data["parent_id"]}
                    if parent_system_in_data
                    else None
                ),
            )
        self.mock_is_duplicate_system(duplicate_system_in_data)
        RepositoryTestHelpers.mock_insert_one(self.systems_collection, inserted_system_id)
        RepositoryTestHelpers.mock_find_one(
            self.systems_collection, {**self._system_in.model_dump(), "_id": inserted_system_id}
        )

    def call_create(self) -> None:
        """Calls the `SystemRepo` `create` method with the appropriate data from a prior call to `mock_create`."""

        self._created_system = self.system_repository.create(self._system_in, session=self.mock_session)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemRepo` `create` method with the appropriate data from a prior call to `mock_create`
        while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_repository.create(self._system_in)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        system_in_data = self._system_in.model_dump()

        # Obtain a list of expected find_one calls
        expected_find_one_calls = []
        # This is the check for parent existence
        if self._system_in.parent_id:
            expected_find_one_calls.append(call({"_id": self._system_in.parent_id}, session=self.mock_session))
        # Also need checks for duplicate and the final newly inserted system get
        expected_find_one_calls.append(self.get_is_duplicate_system_expected_find_one_call(self._system_in, None))
        expected_find_one_calls.append(
            call(
                {"_id": CustomObjectId(self._expected_system_out.id)},
                session=self.mock_session,
            )
        )
        self.systems_collection.find_one.assert_has_calls(expected_find_one_calls)

        self.systems_collection.insert_one.assert_called_once_with(system_in_data, session=self.mock_session)
        assert self._created_system == self._expected_system_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Message of the raised exception.
        """

        self.systems_collection.insert_one.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a system."""

    def test_create(self):
        """Test creating a system."""

        self.mock_create(SYSTEM_IN_DATA_NO_PARENT_A)
        self.call_create()
        self.check_create_success()

    def test_create_with_parent_id(self):
        """Test creating a system with a valid `parent_id`."""

        self.mock_create(
            {**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_parent_id(self):
        """Test creating a system with a non-existent `parent_id`."""

        parent_id = str(ObjectId())

        self.mock_create({**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": parent_id}, parent_system_in_data=None)
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No parent system found with ID: {parent_id}")

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a system with a duplicate system being found in the parent system."""

        self.mock_create(
            {**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            duplicate_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
        )
        self.call_create_expecting_error(DuplicateRecordError)
        self.check_create_failed_with_exception("Duplicate system found within the parent system")


class GetDSL(SystemRepoDSL):
    """Base class for `get` tests."""

    _obtained_system_id: str
    _expected_system_out: Optional[SystemOut]
    _obtained_system: Optional[SystemOut]
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, system_id: str, system_in_data: Optional[dict]) -> None:
        """
        Mocks database methods appropriately to test the `get` repo method.

        :param system_id: ID of the system to be obtained.
        :param system_in_data: Either `None` or a dictionary containing the system data as would be required for a
                               `SystemIn` database model (i.e. No id or created and modified times required).
        """

        self._expected_system_out = (
            SystemOut(**SystemIn(**system_in_data).model_dump(), id=CustomObjectId(system_id))
            if system_in_data
            else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.systems_collection, self._expected_system_out.model_dump() if self._expected_system_out else None
        )

    def call_get(self, system_id: str) -> None:
        """
        Calls the `SystemRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param system_id: ID of the system to be obtained.
        """

        self._obtained_system_id = system_id
        self._obtained_system = self.system_repository.get(system_id, session=self.mock_session)

    def call_get_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemRepo` `get` method with the appropriate data from a prior call to `mock_get`
        while expecting an error to be raised.

        :param system_id: ID of the system to be obtained.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_repository.get(system_id)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.systems_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_system_id)}, session=self.mock_session
        )
        assert self._obtained_system == self._expected_system_out

    def check_get_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.systems_collection.find_one.assert_not_called()

        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a system."""

    def test_get(self):
        """Test getting a system."""

        system_id = str(ObjectId())

        self.mock_get(system_id, SYSTEM_IN_DATA_NO_PARENT_A)
        self.call_get(system_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Test getting a system with a non-existent ID."""

        system_id = str(ObjectId())

        self.mock_get(system_id, None)
        self.call_get(system_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting a system with an invalid ID."""

        system_id = "invalid-id"

        self.call_get_expecting_error(system_id, InvalidObjectIdError)
        self.check_get_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class GetBreadcrumbsDSL(SystemRepoDSL):
    """Base class for `get_breadcrumbs` tests."""

    _breadcrumbs_query_result: list[dict]
    _mock_aggregation_pipeline = MagicMock()
    _expected_breadcrumbs: MagicMock
    _obtained_system_id: str
    _obtained_breadcrumbs: MagicMock

    def mock_breadcrumbs(self, breadcrumbs_query_result: list[dict]) -> None:
        """Mocks database methods appropriately to test the `get_breadcrumbs` repo method.

        :param breadcrumbs_query_result: List of dictionaries containing the breadcrumbs query result from the
                                         aggregation pipeline.
        """
        self._breadcrumbs_query_result = breadcrumbs_query_result
        self._mock_aggregation_pipeline = MagicMock()
        self._expected_breadcrumbs = MagicMock()

        self.mock_utils.create_breadcrumbs_aggregation_pipeline.return_value = self._mock_aggregation_pipeline
        self.systems_collection.aggregate.return_value = breadcrumbs_query_result
        self.mock_utils.compute_breadcrumbs.return_value = self._expected_breadcrumbs

    def call_get_breadcrumbs(self, system_id: str) -> None:
        """
        Calls the SystemRepo `get_breadcrumbs` method.

        :param system_id: ID of the system to obtain the breadcrumbs of.
        """

        self._obtained_system_id = system_id
        self._obtained_breadcrumbs = self.system_repository.get_breadcrumbs(system_id, session=self.mock_session)

    def check_get_breadcrumbs_success(self):
        """Checks that a prior call to `call_get_breadcrumbs` worked as expected."""

        self.mock_utils.create_breadcrumbs_aggregation_pipeline.assert_called_once_with(
            entity_id=self._obtained_system_id, collection_name="systems"
        )
        self.systems_collection.aggregate.assert_called_once_with(
            self._mock_aggregation_pipeline, session=self.mock_session
        )
        self.mock_utils.compute_breadcrumbs.assert_called_once_with(
            list(self._breadcrumbs_query_result), entity_id=self._obtained_system_id, collection_name="systems"
        )

        assert self._obtained_breadcrumbs == self._expected_breadcrumbs


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting the breadcrumbs of a system."""

    def test_get_breadcrumbs(self):
        """Test getting a system's breadcrumbs."""

        self.mock_breadcrumbs(MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH)
        self.call_get_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_success()


class ListDSL(SystemRepoDSL):
    """Base class for `list` tests."""

    _expected_systems_out: list[SystemOut]
    _parent_id_filter: Optional[str]
    _obtained_systems_out: list[SystemOut]

    def mock_list(self, systems_in_data: list[dict]):
        """Mocks database methods appropriately to test the `list` repo method.

        :param systems_in_data: List of dictionaries containing the system data as would be required for a
                                `SystemIn` database model (i.e. no ID or created and modified times required).
        """

        self._expected_systems_out = [
            SystemOut(**SystemIn(**system_in_data).model_dump(), id=ObjectId()) for system_in_data in systems_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.systems_collection, [system_out.model_dump() for system_out in self._expected_systems_out]
        )

    def call_list(self, parent_id: Optional[str]):
        """
        Calls the `SystemRepo` `list` method.

        :param parent_id: ID of the parent system to query by, or `None`.
        """

        self._parent_id_filter = parent_id

        self._obtained_systems_out = self.system_repository.list(parent_id=parent_id, session=self.mock_session)

    def check_list_success(self):
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_utils.list_query.assert_called_once_with(self._parent_id_filter, "systems")
        self.systems_collection.find.assert_called_once_with(
            self.mock_utils.list_query.return_value, session=self.mock_session
        )

        assert self._obtained_systems_out == self._expected_systems_out


class TestList(ListDSL):
    """Tests for listing system's."""

    def test_list(self):
        """Test listing all systems."""

        self.mock_list([SYSTEM_IN_DATA_NO_PARENT_A, SYSTEM_IN_DATA_NO_PARENT_B])
        self.call_list(parent_id=None)
        self.check_list_success()

    def test_list_with_parent_id_filter(self):
        """Test listing all systems with a given `parent_id`."""

        self.mock_list([SYSTEM_IN_DATA_NO_PARENT_A, SYSTEM_IN_DATA_NO_PARENT_B])
        self.call_list(parent_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_null_parent_id_filter(self):
        """Test listing all systems with a 'null' `parent_id`."""

        self.mock_list([SYSTEM_IN_DATA_NO_PARENT_A, SYSTEM_IN_DATA_NO_PARENT_B])
        self.call_list(parent_id="null")
        self.check_list_success()

    def test_list_with_parent_id_with_no_results(self):
        """Test listing all systems with a `parent_id` filter returning no results."""

        self.mock_list([])
        self.call_list(parent_id=str(ObjectId()))
        self.check_list_success()


class UpdateDSL(SystemRepoDSL):
    """Base class for `update` tests."""

    # pylint:disable=too-many-instance-attributes
    _system_in: SystemIn
    _stored_system_out: Optional[SystemOut]
    _expected_system_out: SystemOut
    _updated_system_id: str
    _updated_system: SystemOut
    _moving_system: bool
    _update_exception: pytest.ExceptionInfo

    def set_update_data(self, new_system_in_data: dict):
        """
        Assigns the update data to use during a call to `call_update`.

        :param new_system_data: New system data as would be required for a `SystemIn` database model to supply to the
                                `SystemRepo` `update` method.
        """
        self._system_in = SystemIn(**new_system_in_data)

    # pylint:disable=too-many-arguments
    def mock_update(
        self,
        system_id: str,
        new_system_in_data: dict,
        stored_system_in_data: Optional[dict],
        new_parent_system_in_data: Optional[dict] = None,
        duplicate_system_in_data: Optional[dict] = None,
        valid_move_result: bool = True,
    ) -> None:
        """
        Mocks database methods appropriately to test the `update` repo method.

        :param system_id: ID of the system to be updated.
        :param new_system_in_data: Dictionary containing the new system data as would be required for a `SystemIn`
                                   database model (i.e. no ID or created and modified times required).
        :param stored_system_in_data: Dictionary containing the system data for the existing stored system
                                      as would be required for a `SystemIn` database model.
        :param new_parent_system_in_data: Either `None` or a dictionary containing the new parent system data as would
                                          be required for a `SystemIn` database model.
        :param duplicate_system_in_data: Either `None` or a dictionary containing the data for a duplicate system as
                                         would be required for a `SystemIn` database model.
        :param valid_move_result: Whether to mock in a valid or invalid move result i.e. when `True` will simulate
                                  moving the system to one of its own children.
        """
        self.set_update_data(new_system_in_data)

        # When a parent_id is given, need to mock the find_one for it too
        if new_system_in_data["parent_id"]:
            # If new_parent_system_data is given as none, then it is intentionally supposed to be, otherwise
            # pass through SystemIn first to ensure it has creation and modified times
            RepositoryTestHelpers.mock_find_one(
                self.systems_collection,
                (
                    {**SystemIn(**new_parent_system_in_data).model_dump(), "_id": new_system_in_data["parent_id"]}
                    if new_parent_system_in_data
                    else None
                ),
            )

        # Stored system
        self._stored_system_out = (
            SystemOut(**SystemIn(**stored_system_in_data).model_dump(), id=CustomObjectId(system_id))
            if stored_system_in_data
            else None
        )
        RepositoryTestHelpers.mock_find_one(
            self.systems_collection, self._stored_system_out.model_dump() if self._stored_system_out else None
        )

        # Duplicate check
        self._moving_system = stored_system_in_data is not None and (
            new_system_in_data["parent_id"] != stored_system_in_data["parent_id"]
        )
        if (self._stored_system_out and (self._system_in.name != self._stored_system_out.name)) or self._moving_system:
            self.mock_is_duplicate_system(duplicate_system_in_data)

        # Final system after update
        self._expected_system_out = SystemOut(**self._system_in.model_dump(), id=CustomObjectId(system_id))
        RepositoryTestHelpers.mock_find_one(self.systems_collection, self._expected_system_out.model_dump())

        if self._moving_system:
            mock_aggregation_pipeline = MagicMock()
            self.mock_utils.create_move_check_aggregation_pipeline.return_value = mock_aggregation_pipeline
            if valid_move_result:
                self.mock_utils.is_valid_move_result.return_value = True
                self.systems_collection.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_VALID
            else:
                self.mock_utils.is_valid_move_result.return_value = False
                self.systems_collection.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_INVALID

    def call_update(self, system_id: str) -> None:
        """
        Calls the `SystemRepo` `update` method with the appropriate data from a prior call to `mock_update` (or
        `set_update_data`).

        :param system_id: ID of the system to be updated.
        """

        self._updated_system_id = system_id
        self._updated_system = self.system_repository.update(system_id, self._system_in, session=self.mock_session)

    def call_update_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemRepo` `update` method with the appropriate data from a prior call to `mock_update` (or
        `set_update_data`) while expecting an error to be raised.

        :param system_id: ID of the system to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_repository.update(system_id, self._system_in)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        # Obtain a list of expected find_one calls
        expected_find_one_calls = []

        # Parent existence check
        if self._system_in.parent_id:
            expected_find_one_calls.append(call({"_id": self._system_in.parent_id}, session=self.mock_session))

        # Stored system
        expected_find_one_calls.append(
            call(
                {"_id": CustomObjectId(self._expected_system_out.id)},
                session=self.mock_session,
            )
        )

        # Duplicate check (which only runs if moving or changing the name)
        if (self._stored_system_out and (self._system_in.name != self._stored_system_out.name)) or self._moving_system:
            expected_find_one_calls.append(
                self.get_is_duplicate_system_expected_find_one_call(
                    self._system_in, CustomObjectId(self._updated_system_id)
                )
            )
        self.systems_collection.find_one.assert_has_calls(expected_find_one_calls)

        if self._moving_system:
            self.mock_utils.create_move_check_aggregation_pipeline.assert_called_once_with(
                entity_id=self._updated_system_id,
                destination_id=str(self._system_in.parent_id),
                collection_name="systems",
            )
            self.systems_collection.aggregate.assert_called_once_with(
                self.mock_utils.create_move_check_aggregation_pipeline.return_value, session=self.mock_session
            )

        self.systems_collection.update_one.assert_called_once_with(
            {
                "_id": CustomObjectId(self._updated_system_id),
            },
            {
                "$set": self._system_in.model_dump(),
            },
            session=self.mock_session,
        )

        assert self._updated_system == self._expected_system_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.systems_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a system."""

    def test_update(self):
        """Test updating a system."""

        system_id = str(ObjectId())

        self.mock_update(system_id, SYSTEM_IN_DATA_NO_PARENT_A, SYSTEM_IN_DATA_NO_PARENT_B)
        self.call_update(system_id)
        self.check_update_success()

    def test_update_no_changes(self):
        """Test updating a system to have exactly the same contents."""

        system_id = str(ObjectId())

        self.mock_update(system_id, SYSTEM_IN_DATA_NO_PARENT_A, SYSTEM_IN_DATA_NO_PARENT_A)
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id(self):
        """Test updating a system's `parent_id` to move it."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id=system_id,
            new_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
            new_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            duplicate_system_in_data=None,
            valid_move_result=True,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_child_of_self(self):
        """Test updating a system's `parent_id` to a child of it self (should prevent this)."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id=system_id,
            new_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            new_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            duplicate_system_in_data=None,
            valid_move_result=False,
        )
        self.call_update_expecting_error(system_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot move a system to one of its own children")

    def test_update_with_non_existent_parent_id(self):
        """Test updating a system's `parent_id` to a non-existent system."""

        system_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            system_id,
            {**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": new_parent_id},
            SYSTEM_IN_DATA_NO_PARENT_A,
            new_parent_system_in_data=None,
        )
        self.call_update_expecting_error(system_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No parent system found with ID: {new_parent_id}")

    def test_update_name_to_duplicate_within_parent(self):
        """Test updating a system's name to one that is a duplicate within the parent system."""

        system_id = str(ObjectId())
        duplicate_name = "New Duplicate Name"

        self.mock_update(
            system_id,
            {**SYSTEM_IN_DATA_NO_PARENT_A, "name": duplicate_name},
            SYSTEM_IN_DATA_NO_PARENT_A,
            duplicate_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_A, "name": duplicate_name},
        )
        self.call_update_expecting_error(system_id, DuplicateRecordError)
        self.check_update_failed_with_exception("Duplicate system found within the parent system")

    def test_update_parent_id_with_duplicate_within_parent(self):
        """Test updating a system's `parent_id` to one that contains a system with a duplicate name within the same
        parent system."""

        system_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            system_id,
            {**SYSTEM_IN_DATA_NO_PARENT_A, "parent_id": new_parent_id},
            SYSTEM_IN_DATA_NO_PARENT_A,
            new_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            duplicate_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
        )
        self.call_update_expecting_error(system_id, DuplicateRecordError)
        self.check_update_failed_with_exception("Duplicate system found within the parent system")

    def test_update_with_invalid_id(self):
        """Test updating a system with an invalid id."""

        system_id = "invalid-id"

        self.set_update_data(SYSTEM_IN_DATA_NO_PARENT_A)
        self.call_update_expecting_error(system_id, InvalidObjectIdError)
        self.check_update_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class DeleteDSL(SystemRepoDSL):
    """Base class for `delete` tests."""

    _delete_system_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self, deleted_count: int, child_system_data: Optional[dict] = None, child_item_data: Optional[dict] = None
    ) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        :param child_system_data: Dictionary containing a child system's data (or `None`).
        :param child_item_data: Dictionary containing a child item's data (or `None`).
        """

        self.mock_has_child_elements(child_system_data, child_item_data)
        RepositoryTestHelpers.mock_delete_one(self.systems_collection, deleted_count)

    def call_delete(self, system_id: str) -> None:
        """
        Calls the SystemRepo `delete` method.

        :param system_id: ID of the system to be deleted.
        """

        self._delete_system_id = system_id
        self.system_repository.delete(system_id, session=self.mock_session)

    def call_delete_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the SystemRepo `delete` method while expecting an error to be raised.

        :param system_id: ID of the system to be deleted.
        :param error_type: Expected exception to be raised.
        """

        self._delete_system_id = system_id
        with pytest.raises(error_type) as exc:
            self.system_repository.delete(system_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.check_has_child_elements_performed_expected_calls(self._delete_system_id)
        self.systems_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_system_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """

        if not expecting_delete_one_called:
            self.systems_collection.delete_one.assert_not_called()
        else:
            self.systems_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_system_id)}, session=None
            )

        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting a system."""

    def test_delete(self):
        """Test deleting a system."""

        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_child_system(self):
        """Test deleting a system when it has a child system."""

        system_id = str(ObjectId())

        self.mock_delete(deleted_count=1, child_system_data=SYSTEM_IN_DATA_NO_PARENT_A)
        self.call_delete_expecting_error(system_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(f"System with ID {system_id} has child elements and cannot be deleted")

    def test_delete_with_child_item(self):
        """Test deleting a system when it has a child Item."""

        system_id = str(ObjectId())

        # pylint:disable=fixme
        # TODO: Replace ITEM_INFO once item tests have been refactored
        self.mock_delete(deleted_count=1, child_item_data=ITEM_INFO)
        self.call_delete_expecting_error(system_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(f"System with ID {system_id} has child elements and cannot be deleted")

    def test_delete_non_existent_id(self):
        """Test deleting a system with a non-existent id."""

        system_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(system_id, MissingRecordError)
        self.check_delete_failed_with_exception(
            f"No system found with ID: {system_id}", expecting_delete_one_called=True
        )

    def test_delete_invalid_id(self):
        """Test deleting a system with an invalid id."""

        system_id = "invalid-id"

        self.call_delete_expecting_error(system_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception("Invalid ObjectId value 'invalid-id'")
