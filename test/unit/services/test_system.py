"""
Unit tests for the `SystemService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments

from test.mock_data import (
    SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
    SYSTEM_IN_DATA_NO_PARENT_A,
    SYSTEM_IN_DATA_NO_PARENT_B,
    SYSTEM_POST_DATA_NO_PARENT_A,
    SYSTEM_POST_DATA_NO_PARENT_B,
    SYSTEM_TYPE_GET_DATA_OPERATIONAL,
    SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
    SYSTEM_TYPE_OUT_DATA_STORAGE,
)
from test.unit.services.conftest import ServiceTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidActionError,
    MissingRecordError,
)
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.system import SystemService


class SystemServiceDSL:
    """Base class for `SystemService` unit tests."""

    wrapped_utils: Mock
    mock_system_repository: Mock
    mock_system_type_repository: Mock
    mock_setting_repository: Mock
    mock_start_session_transaction: Mock
    system_service: SystemService

    mock_transaction_session: Mock
    _expected_spares_definition_out: Optional[SparesDefinitionOut]
    _expect_transaction: bool

    @pytest.fixture(autouse=True)
    def setup(
        self,
        system_repository_mock,
        system_type_repository_mock,
        setting_repository_mock,
        system_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures."""

        self.mock_system_repository = system_repository_mock
        self.mock_system_type_repository = system_type_repository_mock
        self.mock_setting_repository = setting_repository_mock
        self.system_service = system_service

        with patch("inventory_management_system_api.services.system.utils", wraps=utils) as wrapped_utils:
            with patch(
                "inventory_management_system_api.services.system.start_session_transaction"
            ) as mocked_start_session_transaction:
                self.wrapped_utils = wrapped_utils
                self.mock_start_session_transaction = mocked_start_session_transaction
                yield

    def _mock_start_transaction_effected_by_spares_calculation(
        self,
        spares_definition_out_data: Optional[dict],
        system: SystemPatchSchema,
        stored_system: SystemOut,
        update_data: dict,
    ) -> None:
        """
        Mocks methods appropriately for when the `_start_transaction_effected_by_spares_calculation` service method
        will be called.

        :param spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as would
                                           be required for a `SparesDefinitionOut` database model.
        :param system: System containing the fields to be updated.
        :param stored_system: Current stored system from the database.
        :param update_data: Dictionary containing the update data.
        """

        # Only require the transaction there is a spares definition, the `type_id` is being changed, and the
        # current/new `parent_system_id` is None
        self._expect_transaction = (
            spares_definition_out_data
            and ("type_id" in update_data and system.type_id != stored_system.type_id)
            and (system.parent_id is None if "parent_id" in update_data else stored_system.parent_id is None)
        )

        # Mock the transaction session itself - this will be the value ultimately returned by
        # _start_transaction_effected_by_spares_calculation
        self.mock_transaction_session = MagicMock() if self._expect_transaction else None
        self.mock_start_session_transaction.return_value.__enter__.return_value = self.mock_transaction_session

        # Mock the spares definition get
        self._expected_spares_definition_out = (
            SparesDefinitionOut(**spares_definition_out_data)
            if spares_definition_out_data
            and (system.type_id and system.type_id != stored_system.type_id)
            and (system.parent_id is None if system.parent_id else stored_system.parent_id is None)
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_setting_repository, self._expected_spares_definition_out)

    def _check_start_transaction_effected_by_spares_calculation_performed_expected_calls(
        self,
        expected_action_description: str,
        expected_system_id: str,
    ) -> None:
        """
        Checks that a call to `_start_transaction_effected_by_spares_calculation` performed the expected function
        calls.

        :param expected_action_description: Expected `action_description` the function should have been called with.
        :param expected_system_id: Expected `system_id` the function should have been called with.
        """

        self.mock_setting_repository.get.assert_called_once_with(SparesDefinitionOut)

        if self._expect_transaction:
            self.mock_start_session_transaction.assert_called_once_with(expected_action_description)
            self.mock_start_session_transaction.return_value.__enter__.assert_called_once()

            self.mock_system_repository.write_lock.assert_called_once_with(
                expected_system_id, self.mock_transaction_session
            )


class CreateDSL(SystemServiceDSL):
    """Base class for `create` tests."""

    _system_post: SystemPostSchema
    _expected_system_in: SystemIn
    _expected_system_out: SystemOut
    _created_system: SystemOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        system_post_data: dict,
        system_type_out_data: Optional[dict] = None,
        parent_system_in_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param system_post_data: Dictionary containing the basic system data as would be required for a
                                 `SystemPostSchema` (i.e. no ID, code or created and modified times required).
        :param system_type_out_data: Either `None` or a dictionary containing the system type data as would be required
                                     for a `SystemTypeOut` database model.
        :param parent_system_in_data: Either `None` or a dictionary containing the parent system data as would be
                                      required for a `SystemIn` database model.
        """

        # System type
        ServiceTestHelpers.mock_get(
            self.mock_system_type_repository, SystemTypeOut(**system_type_out_data) if system_type_out_data else None
        )

        # Parent system
        if system_post_data["parent_id"]:
            ServiceTestHelpers.mock_get(
                self.mock_system_repository,
                (
                    SystemOut(
                        **{
                            **SystemIn(**parent_system_in_data).model_dump(by_alias=True),
                            "_id": system_post_data["parent_id"],
                        }
                    )
                    if parent_system_in_data
                    else None
                ),
            )

        # System
        self._system_post = SystemPostSchema(**system_post_data)

        self._expected_system_in = SystemIn(
            **system_post_data, code=utils.generate_code(system_post_data["name"], "system")
        )
        self._expected_system_out = SystemOut(**self._expected_system_in.model_dump(), id=ObjectId())

        ServiceTestHelpers.mock_create(self.mock_system_repository, self._expected_system_out)

    def call_create(self) -> None:
        """Calls the `SystemService` `create` method with the appropriate data from a prior call to `mock_create`."""

        self._created_system = self.system_service.create(self._system_post)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemService` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_service.create(self._system_post)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        self.mock_system_type_repository.get.assert_called_once_with(self._system_post.type_id)

        if self._system_post.parent_id is not None:
            self.mock_system_repository.get.assert_called_once_with(self._system_post.parent_id)
        else:
            self.mock_system_repository.get.assert_not_called()

        self.wrapped_utils.generate_code.assert_called_once_with(self._expected_system_out.name, "system")
        self.mock_system_repository.create.assert_called_once_with(self._expected_system_in)

        assert self._created_system == self._expected_system_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.wrapped_utils.generate_code.assert_not_called()
        self.mock_system_repository.create.assert_not_called()
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a system."""

    def test_create(self):
        """Test creating a system."""

        self.mock_create(SYSTEM_POST_DATA_NO_PARENT_A, system_type_out_data=SYSTEM_TYPE_OUT_DATA_STORAGE)
        self.call_create()
        self.check_create_success()

    def test_create_with_parent_id(self):
        """Test creating a system with a `parent_id`."""

        self.mock_create(
            {**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            system_type_out_data=SYSTEM_TYPE_OUT_DATA_STORAGE,
            parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_parent_id(self):
        """Test creating a system with a non-existent `parent_id`."""

        parent_id = str(ObjectId())

        self.mock_create(
            {**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": parent_id},
            system_type_out_data=SYSTEM_TYPE_OUT_DATA_STORAGE,
            parent_system_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No parent system found with ID: {parent_id}")

    def test_create_with_different_type_id_to_parent(self):
        """Test creating a system with a different `type_id` to its parent."""

        self.mock_create(
            {
                **SYSTEM_POST_DATA_NO_PARENT_A,
                "parent_id": str(ObjectId()),
                "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"],
            },
            system_type_out_data=SYSTEM_TYPE_OUT_DATA_STORAGE,
            parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
        )
        self.call_create_expecting_error(InvalidActionError)
        self.check_create_failed_with_exception("Cannot use a different type_id to the parent system")

    def test_create_with_non_existent_type_id(self):
        """Test creating a system with a non-existent `type_id`."""

        type_id = str(ObjectId())

        self.mock_create(
            {**SYSTEM_POST_DATA_NO_PARENT_A, "type_id": type_id},
            system_type_out_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No system type found with ID: {type_id}")


class GetDSL(SystemServiceDSL):
    """Base class for `get` tests."""

    _obtained_system_id: str
    _expected_system: MagicMock
    _obtained_system: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_system = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_system_repository, self._expected_system)

    def call_get(self, system_id: str) -> None:
        """
        Calls the `SystemService` `get` method.

        :param system_id: ID of the system to be obtained.
        """

        self._obtained_system_id = system_id
        self._obtained_system = self.system_service.get(system_id)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.mock_system_repository.get.assert_called_once_with(self._obtained_system_id)
        assert self._obtained_system == self._expected_system


class TestGet(GetDSL):
    """Tests for getting a system."""

    def test_get(self):
        """Test getting a system."""

        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class GetBreadcrumbsDSL(SystemServiceDSL):
    """Base class for `get_breadcrumbs` tests."""

    _expected_breadcrumbs: MagicMock
    _obtained_breadcrumbs: MagicMock
    _obtained_system_id: str

    def mock_get_breadcrumbs(self) -> None:
        """Mocks repo methods appropriately to test the `get_breadcrumbs` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_breadcrumbs = MagicMock()
        ServiceTestHelpers.mock_get_breadcrumbs(self.mock_system_repository, self._expected_breadcrumbs)

    def call_get_breadcrumbs(self, system_id: str) -> None:
        """
        Calls the `SystemService` `get_breadcrumbs` method.

        :param system_id: ID of the system to obtain the breadcrumbs of.
        """

        self._obtained_system_id = system_id
        self._obtained_breadcrumbs = self.system_service.get_breadcrumbs(system_id)

    def check_get_breadcrumbs_success(self) -> None:
        """Checks that a prior call to `call_get_breadcrumbs` worked as expected."""

        self.mock_system_repository.get_breadcrumbs.assert_called_once_with(self._obtained_system_id)
        assert self._obtained_breadcrumbs == self._expected_breadcrumbs


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting the breadcrumbs of a system."""

    def test_get_breadcrumbs(self):
        """Test getting a system's breadcrumbs."""

        self.mock_get_breadcrumbs()
        self.call_get_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_success()


class ListDSL(SystemServiceDSL):
    """Base class for `list` tests."""

    _parent_id_filter: Optional[str]
    _expected_systems: MagicMock
    _obtained_systems: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_systems = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_system_repository, self._expected_systems)

    def call_list(self, parent_id: Optional[str]) -> None:
        """
        Calls the `SystemService` `list` method.

        :param parent_id: ID of the parent system to query by, or `None`.
        """

        self._parent_id_filter = parent_id
        self._obtained_systems = self.system_service.list(parent_id)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_system_repository.list.assert_called_once_with(self._parent_id_filter)
        assert self._obtained_systems == self._expected_systems


class TestList(ListDSL):
    """Tests for listing systems."""

    def test_list(self):
        """Test listing systems."""

        self.mock_list()
        self.call_list(str(ObjectId()))
        self.check_list_success()


class UpdateDSL(SystemServiceDSL):
    """Base class for `update` tests"""

    _stored_system: Optional[SystemOut]
    _system_patch: SystemPatchSchema
    _expected_system_in: SystemIn
    _expected_system_out: MagicMock
    _updated_system_id: str
    _updated_system: MagicMock
    _update_exception: pytest.ExceptionInfo

    _type_id_changing: bool
    _parent_id_changing: bool

    def mock_update(
        self,
        system_id: str,
        system_patch_data: dict,
        stored_system_post_data: Optional[dict],
        stored_parent_system_in_data: Optional[dict] = None,
        stored_spares_definition_out_data: Optional[dict] = None,
        new_system_type_out_data: Optional[dict] = None,
        new_parent_system_in_data: Optional[dict] = None,
        has_child_elements: bool = False,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `update` service method.

        :param system_id: ID of the system that will be obtained.
        :param system_patch_data: Dictionary containing the patch data as would be required for a
                                  `SystemPatchSchema` (i.e. no ID, code, or created and modified times required).
        :param stored_system_post_data: Dictionary containing the system data for the existing stored system.
                                        as would be required for a `SystemPostSchema` (i.e. no ID, code or created and
                                        modified times required).
        :param stored_parent_system_in_data: Either `None` or a dictionary containing the stored parent system data as
                                             would be required for a `SystemIn` database model.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for `SparesDefinitionOut` database model.
        :param new_system_type_out_data: Either `None` or a dictionary containing the new system type data as would be
                                         required for a `SystemTypeOut` database model.
        :param new_parent_system_in_data: Either `None` or a dictionary containing the new parent system data as would
                                      be required for a `SystemIn` database model.
        :param has_child_elements: Boolean of whether the system being updated has child elements or not.
        """

        # Stored system
        self._stored_system = (
            SystemOut(
                **SystemIn(
                    **stored_system_post_data, code=utils.generate_code(stored_system_post_data["name"], "system")
                ).model_dump(),
                id=CustomObjectId(system_id),
            )
            if stored_system_post_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_system_repository, self._stored_system)

        self._type_id_changing = (
            "type_id" in system_patch_data
            and self._stored_system is not None
            and self._stored_system.type_id != system_patch_data["type_id"]
        )
        self._parent_id_changing = (
            "parent_id" in system_patch_data
            and self._stored_system is not None
            and self._stored_system.parent_id != system_patch_data["parent_id"]
        )
        if self._type_id_changing or self._parent_id_changing:
            if self._type_id_changing:
                self.mock_system_repository.has_child_elements.return_value = has_child_elements

                ServiceTestHelpers.mock_get(
                    self.mock_system_type_repository,
                    SystemTypeOut(**new_system_type_out_data) if new_system_type_out_data is not None else None,
                )

            if self._parent_id_changing:
                if system_patch_data["parent_id"] is not None:
                    ServiceTestHelpers.mock_get(
                        self.mock_system_repository,
                        (
                            SystemOut(
                                **SystemIn(
                                    **new_parent_system_in_data,
                                ).model_dump(),
                                id=CustomObjectId(system_id),
                            )
                            if new_parent_system_in_data
                            else None
                        ),
                    )
            elif self._stored_system.parent_id is not None:
                ServiceTestHelpers.mock_get(
                    self.mock_system_repository,
                    (
                        SystemOut(
                            **SystemIn(
                                **stored_parent_system_in_data,
                            ).model_dump(),
                            id=CustomObjectId(system_id),
                        )
                        if stored_parent_system_in_data
                        else None
                    ),
                )

        # Patch schema
        self._system_patch = SystemPatchSchema(**system_patch_data)

        self._mock_start_transaction_effected_by_spares_calculation(
            stored_spares_definition_out_data, self._system_patch, self._stored_system, system_patch_data
        )

        # Updated system
        self._expected_system_out = MagicMock()
        ServiceTestHelpers.mock_update(self.mock_system_repository, self._expected_system_out)

        # Construct the expected input for the repository
        merged_system_data = {**(stored_system_post_data or {}), **system_patch_data}
        self._expected_system_in = SystemIn(
            **merged_system_data,
            code=utils.generate_code(merged_system_data["name"], "system"),
        )

    def call_update(self, system_id: str) -> None:
        """
        Calls the `SystemService` `update` method with the appropriate data from a prior call to `mock_update`.

        :param system_id: ID of the system to be updated.
        """

        self._updated_system_id = system_id
        self._updated_system = self.system_service.update(system_id, self._system_patch)

    def call_update_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemService` `update` method with the appropriate data from a prior call to `mock_update`
        while expecting an error to be raised.

        :param system_id: ID of the system to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_service.update(system_id, self._system_patch)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        # Obtain a list of expected system get calls
        expected_system_get_calls = []

        # Ensure obtained old system
        expected_system_get_calls.append(call(self._updated_system_id))

        self._check_start_transaction_effected_by_spares_calculation_performed_expected_calls(
            "updating system", self._updated_system_id
        )

        # Ensure obtained parent if needed
        if self._type_id_changing or self._parent_id_changing:
            # Ensure checking children and obtained type id if needed
            if self._type_id_changing:
                self.mock_system_repository.has_child_elements.assert_called_once_with(self._updated_system_id)
                self.mock_system_type_repository.get.assert_called_once_with(self._system_patch.type_id)

            if self._parent_id_changing:
                if self._system_patch.parent_id is not None:
                    expected_system_get_calls.append(call(self._system_patch.parent_id))
            elif self._stored_system.parent_id is not None:
                expected_system_get_calls.append(call(self._stored_system.parent_id))

        self.mock_system_repository.get.assert_has_calls(expected_system_get_calls)

        # Ensure new code was obtained if patching name
        if self._system_patch.name:
            self.wrapped_utils.generate_code.assert_called_once_with(self._system_patch.name, "system")
        else:
            self.wrapped_utils.generate_code.assert_not_called()

        # Ensure updated with expected data
        self.mock_system_repository.update.assert_called_once_with(
            self._updated_system_id, self._expected_system_in, session=self.mock_transaction_session
        )

        assert self._updated_system == self._expected_system_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_system_repository.update.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a system."""

    def test_update_all_fields_except_type_and_parent_id(self):
        """Test updating all fields of a system except its type and parent ID."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data=SYSTEM_POST_DATA_NO_PARENT_B,
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_type_id_without_parent(self):
        """Test updating the type ID of a system that doesn't have a parent."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_type_id_without_parent_with_spares_definition_defined(self):
        """Test updating the type ID of a system that doesn't have a parent when there is a spares definition
        defined."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_type_id_with_parent(self):
        """Test updating the type ID of a system that has a parent."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data={**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_parent_system_in_data={
                **SYSTEM_IN_DATA_NO_PARENT_B,
                "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"],
            },
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_type_id_with_parent_with_spares_definition_defined(self):
        """Test updating the type ID of a system that has a parent when there is a spares definition defined."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data={**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_parent_system_in_data={
                **SYSTEM_IN_DATA_NO_PARENT_B,
                "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"],
            },
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_with_non_existent_type_id(self):
        """Test updating a system's `type_id` to a non-existent type."""

        system_id = str(ObjectId())
        new_type_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"type_id": new_type_id},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_system_type_out_data=None,
        )
        self.call_update_expecting_error(system_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No system type found with ID: {new_type_id}")

    def test_update_parent_id_from_none(self):
        """Test updating the parent ID of a system from a value of None."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": str(ObjectId())},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_one_with_a_different_type(self):
        """Test updating the parent ID of a system to one that has a different type."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": str(ObjectId())},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_parent_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_B, "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
        )
        self.call_update_expecting_error(system_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot move a system into one with a different type")

    def test_update_parent_id_to_one_with_a_different_type_while_changing_type(self):
        """Test updating the parent ID of a system to one that has a different type while also changing the type to
        match."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": str(ObjectId()), "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
            new_parent_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_B, "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_one_with_a_different_type_while_changing_type_with_spares_definition_defined(self):
        """Test updating the parent ID of a system to one that has a different type while also changing the type to
        match when there is a spares definition defined."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": str(ObjectId()), "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
            new_parent_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_B, "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_one_with_a_different_type_while_changing_type_with_child_elements(self):
        """Test updating the parent ID of a system to one that has a different type while also changing the type to
        match when the system has child elements."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": str(ObjectId()), "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
            new_parent_system_in_data={**SYSTEM_IN_DATA_NO_PARENT_B, "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            has_child_elements=True,
        )
        self.call_update_expecting_error(system_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot change the type of a system when it has children")

    def test_update_parent_id_to_none(self):
        """Test updating the parent ID of a system from a value to none."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": None},
            stored_system_post_data={**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            new_parent_system_in_data=None,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_none_with_spares_definition_defined(self):
        """Test updating the parent ID of a system from a value to none when there is a spares definition defined."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": None},
            stored_system_post_data={**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            new_parent_system_in_data=None,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_none_while_changing_type(self):
        """Test updating the parent ID of a system to None while also changing the type ID."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": None, "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data={**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            new_system_type_out_data=SYSTEM_TYPE_OUT_DATA_OPERATIONAL,
            new_parent_system_in_data=None,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_parent_id_to_none_while_changing_type_with_child_elements(self):
        """Test updating the parent ID of a system to None while also changing the type ID."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": None, "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]},
            stored_system_post_data={**SYSTEM_POST_DATA_NO_PARENT_A, "parent_id": str(ObjectId())},
            stored_parent_system_in_data=SYSTEM_IN_DATA_NO_PARENT_B,
            new_parent_system_in_data=None,
            has_child_elements=True,
        )
        self.call_update_expecting_error(system_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot change the type of a system when it has children")

    def test_update_with_non_existent_parent_id(self):
        """Test updating a system's `parent_id` to a non-existent system."""

        system_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"parent_id": new_parent_id},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
            new_parent_system_in_data=None,
        )
        self.call_update_expecting_error(system_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No parent system found with ID: {new_parent_id}")

    def test_update_description_only(self):
        """Test updating system's description field only (code should not need regenerating as name doesn't change)."""

        system_id = str(ObjectId())

        self.mock_update(
            system_id,
            system_patch_data={"description": "A new description"},
            stored_system_post_data=SYSTEM_POST_DATA_NO_PARENT_A,
        )
        self.call_update(system_id)
        self.check_update_success()

    def test_update_with_non_existent_id(self):
        """Test updating a system with a non-existent ID."""

        system_id = str(ObjectId())

        self.mock_update(system_id, system_patch_data=SYSTEM_POST_DATA_NO_PARENT_B, stored_system_post_data=None)
        self.call_update_expecting_error(system_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No system found with ID: {system_id}")


class DeleteDSL(SystemServiceDSL):
    """Base class for `delete` tests."""

    _delete_system_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(self, has_child_elements: Optional[bool] = False) -> None:
        """
        Mocks repo methods appropriately to test the `delete` service method.

        :param has_child_elements: Whether the system being deleted has child elements or not.
        """

        self.mock_system_repository.has_child_elements.return_value = has_child_elements

    def call_delete(self, system_id: str) -> None:
        """
        Calls the `SystemService` `delete` method.

        :param system_id: ID of the system to be deleted.
        """

        self._delete_system_id = system_id
        self.system_service.delete(system_id)

    def call_delete_expecting_error(self, system_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `SystemService` `delete` method while expecting an error to be raised.

        :param system_id: ID of the system to be deleted.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.system_service.delete(system_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.mock_system_repository.delete.assert_called_once_with(self._delete_system_id)

    def check_delete_failed_with_exception(self, message: str) -> None:
        """
        Check that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_system_repository.delete.assert_not_called()
        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting a system."""

    def test_delete(self):
        """Test deleting a system."""

        self.mock_delete(has_child_elements=False)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_child_elements(self):
        """Test deleting a system when it has child elements."""

        system_id = str(ObjectId())

        self.mock_delete(has_child_elements=True)
        self.call_delete_expecting_error(system_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(f"System with ID {system_id} has child elements and cannot be deleted")
