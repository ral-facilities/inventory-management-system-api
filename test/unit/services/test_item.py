"""
Unit tests for the `ItemService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code

from test.mock_data import (
    BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
    BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES,
    ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
    ITEM_DATA_NEW_WITH_ALL_PROPERTIES,
    ITEM_DATA_NEW_WITH_MANDATORY_PROPERTIES_ONLY,
    SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
    SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
    SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
    SYSTEM_TYPE_GET_DATA_OPERATIONAL,
    USAGE_STATUS_GET_DATA_IN_USE,
    USAGE_STATUS_IN_DATA_IN_USE,
    USAGE_STATUS_IN_DATA_NEW,
)
from test.unit.services.conftest import BaseCatalogueServiceDSL, ServiceTestHelpers
from typing import List, Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidActionError,
    MissingRecordError,
    WriteConflictError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut
from inventory_management_system_api.models.item import ItemIn, ItemOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.schemas.catalogue_item import PropertyPostSchema
from inventory_management_system_api.schemas.item import ItemPatchSchema, ItemPostSchema
from inventory_management_system_api.schemas.validation import (
    BulkValidationResultSchema,
    ValidationErrorSchema,
    ValidationResultSchema,
)
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.item import ItemService


class ItemServiceDSL(BaseCatalogueServiceDSL):
    """Base class for `ItemService` unit tests."""

    # pylint:disable=too-many-instance-attributes
    wrapped_utils: Mock
    mock_item_repository: Mock
    mock_catalogue_item_repository: Mock
    mock_catalogue_category_repository: Mock
    mock_system_repository: Mock
    mock_usage_status_repository: Mock
    mock_rule_repository: Mock
    mock_setting_repository: Mock
    mock_start_session_transaction: Mock
    item_service: ItemService

    mock_transaction_session: Mock
    _raise_write_conflict_once: bool
    _expected_spares_definition_out: Optional[SparesDefinitionOut]

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    @pytest.fixture(autouse=True)
    def setup(
        self,
        item_repository_mock,
        catalogue_item_repository_mock,
        catalogue_category_repository_mock,
        system_repository_mock,
        usage_status_repository_mock,
        rule_repository_mock,
        setting_repository_mock,
        item_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""

        self.mock_item_repository = item_repository_mock
        self.mock_catalogue_item_repository = catalogue_item_repository_mock
        self.mock_catalogue_category_repository = catalogue_category_repository_mock
        self.mock_system_repository = system_repository_mock
        self.mock_usage_status_repository = usage_status_repository_mock
        self.mock_rule_repository = rule_repository_mock
        self.mock_setting_repository = setting_repository_mock
        self.item_service = item_service

        with patch("inventory_management_system_api.services.item.utils", wraps=utils) as wrapped_utils:
            with patch(
                "inventory_management_system_api.services.item.start_session_transaction"
            ) as mocked_start_session_transaction:
                self.wrapped_utils = wrapped_utils
                self.mock_start_session_transaction = mocked_start_session_transaction
                yield

    def _mock_start_transaction_impacting_number_of_spares(
        self, spares_definition_out_data: Optional[dict], raise_write_conflict_once: bool
    ) -> None:
        """
        Mocks methods appropriately for when the `_start_transaction_impacting_number_of_spares` repo method will be
        called.

        :param spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as would
                                           be required for a `SparesDefinitionOut` database model.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.
        """

        # Mock the transaction session itself - this will be the value ultimately returned by
        # _start_transaction_impacting_number_of_spares
        self.mock_transaction_session = MagicMock() if spares_definition_out_data else None
        self.mock_start_session_transaction.return_value.__enter__.return_value = self.mock_transaction_session

        # Mock the spares definition get
        self._expected_spares_definition_out = (
            SparesDefinitionOut(**spares_definition_out_data) if spares_definition_out_data else None
        )
        ServiceTestHelpers.mock_get(self.mock_setting_repository, self._expected_spares_definition_out)

        # Raise a write conflict if requested
        self._raise_write_conflict_once = raise_write_conflict_once
        if self._raise_write_conflict_once:
            # Strictly speaking this error is not right, it would give an OperationFailure that
            # start_session_transaction will turn into a write conflict, but as that's mocked we just raise it directly
            # here instead
            self.mock_catalogue_item_repository.update_number_of_spares.side_effect = [
                WriteConflictError("Test"),
                None,
                None,
            ]

    def _check_start_transition_impacting_number_of_spares_performed_expected_calls(
        self,
        expected_action_description: str,
        expected_catalogue_item_id: str,
        expected_dest_system_id: Optional[str] = None,
    ) -> None:
        """
        Checks that a call to `_start_transaction_impacting_number_of_spares` performed the expected function calls.

        :param expected_action_description: Expected `action_description` the function should have been called with.
        :param expected_catalogue_item_id: Expected `catalogue_item_id` the function should have been called with.
        :param expected_dest_system_id: Expected `dest_system_id` the function should have been called with.
        """

        expected_catalogue_item_id = CustomObjectId(expected_catalogue_item_id)

        self.mock_setting_repository.get.assert_called_once_with(SparesDefinitionOut)

        # The rest of the calls only occur if there is a spares definition
        if self._expected_spares_definition_out:
            if self._raise_write_conflict_once:
                assert self.mock_start_session_transaction.call_args_list == [
                    call(expected_action_description),
                    call(expected_action_description),
                ]
                self.mock_start_session_transaction.return_value.__enter__.assert_has_calls([call(), call()])

                if expected_dest_system_id:
                    self.mock_system_repository.write_lock.assert_called_once_with(
                        expected_dest_system_id, self.mock_transaction_session
                    )
                else:
                    self.mock_system_repository.write_lock.assert_not_called()

                self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.assert_called_once_with(
                    expected_catalogue_item_id,
                    [
                        CustomObjectId(system_type.id)
                        for system_type in self._expected_spares_definition_out.system_types
                    ],
                    session=self.mock_transaction_session,
                )

                self.mock_catalogue_item_repository.update_number_of_spares.assert_has_calls(
                    [
                        call(expected_catalogue_item_id, None, session=self.mock_transaction_session),
                        call(expected_catalogue_item_id, None, session=self.mock_transaction_session),
                        call(
                            expected_catalogue_item_id,
                            self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.return_value,
                            session=self.mock_transaction_session,
                        ),
                    ]
                )
            else:
                self.mock_start_session_transaction.assert_called_once_with(expected_action_description)
                self.mock_start_session_transaction.return_value.__enter__.assert_called_once()

                if expected_dest_system_id:
                    self.mock_system_repository.write_lock.assert_called_once_with(
                        expected_dest_system_id, self.mock_transaction_session
                    )
                else:
                    self.mock_system_repository.write_lock.assert_not_called()

                self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.assert_called_once_with(
                    expected_catalogue_item_id,
                    [
                        CustomObjectId(system_type.id)
                        for system_type in self._expected_spares_definition_out.system_types
                    ],
                    session=self.mock_transaction_session,
                )
                self.mock_catalogue_item_repository.update_number_of_spares.assert_has_calls(
                    [
                        call(expected_catalogue_item_id, None, session=self.mock_transaction_session),
                        call(
                            expected_catalogue_item_id,
                            self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.return_value,
                            session=self.mock_transaction_session,
                        ),
                    ]
                )


class CreateDSL(ItemServiceDSL):
    """Base class for `create` tests."""

    # pylint:disable=too-many-instance-attributes
    _catalogue_item_out: Optional[CatalogueItemOut]
    _catalogue_category_out: Optional[CatalogueCategoryOut]
    _system_out: Optional[SystemOut]
    _usage_status_out: Optional[UsageStatusOut]
    _item_post: ItemPostSchema
    _expected_item_in: ItemIn
    _expected_item_out: ItemOut
    _created_item: ItemOut
    _create_exception: pytest.ExceptionInfo
    _user_authorised: bool

    _expected_merged_properties: List[PropertyPostSchema]

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    # pylint:disable=too-many-locals
    def mock_create(
        self,
        item_data: dict,
        catalogue_item_data: Optional[dict] = None,
        catalogue_category_in_data: Optional[dict] = None,
        system_in_data: Optional[dict] = None,
        usage_status_in_data: Optional[dict] = None,
        stored_spares_definition_out_data: Optional[dict] = None,
        stored_rule_exists: bool = True,
        raise_write_conflict_once: bool = False,
        user_is_authorised=False,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param item_data: Dictionary containing the basic item data as would be required for an `ItemPostSchema` but
                          with any mandatory IDs missing as they will be added automatically.
        :param catalogue_item_data: Either `None` or a dictionary containing the basic catalogue item data as would be
                                    required for a `CatalogueItemPostSchema` but with any mandatory IDs missing as they
                                    will be added automatically.
        :param catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data as would
                                           be required for a `CatalogueCategoryIn` database model.
        :param system_in_data: Either `None` or a dictionary containing the system data as would be required for
                               `SystemIn` database model.
        :param usage_status_in_data: Either `None` or a dictionary containing the basic usage status data as would be
                                     required for a `UsageStatusIn` database model.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for a `SparesDefinitionOut` database model.
        :param stored_rule_exists: Whether a stored rule exists for the create operation.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.
        :param user_is_authorised: Whether the request is authorised to bypass functionality such as checking rules.
        """

        self._user_authorised = user_is_authorised

        # Generate mandatory IDs to be inserted where needed
        catalogue_item_id = str(ObjectId())
        system_id = str(ObjectId())

        ids_to_insert = {
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
        }

        # Catalogue category
        catalogue_category_in = None
        if catalogue_category_in_data:
            catalogue_category_in = CatalogueCategoryIn(**catalogue_category_in_data)

        catalogue_category_id = str(ObjectId())
        self._catalogue_category_out = (
            CatalogueCategoryOut(
                **{
                    **catalogue_category_in.model_dump(by_alias=True),
                    "_id": catalogue_category_id,
                },
            )
            if catalogue_category_in
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._catalogue_category_out)

        # Catalogue item

        # When properties are given need to add any property `id`s and ensure the expected data inserts them as well
        catalogue_item_expected_properties_in = []
        if catalogue_item_data and "properties" in catalogue_item_data and catalogue_item_data["properties"]:
            catalogue_item_expected_properties_in, catalogue_item_property_post_schemas = (
                self.construct_properties_in_and_post_with_ids(
                    catalogue_category_in.properties, catalogue_item_data["properties"]
                )
            )
            catalogue_item_expected_properties_in = utils.process_properties(
                self._catalogue_category_out.properties, catalogue_item_property_post_schemas
            )

        catalogue_item_in = (
            CatalogueItemIn(
                **{
                    **catalogue_item_data,
                    "catalogue_category_id": catalogue_category_id,
                    "manufacturer_id": str(ObjectId()),
                    "properties": catalogue_item_expected_properties_in,
                },
                number_of_spares=None,
            )
            if catalogue_item_data
            else None
        )
        self._catalogue_item_out = (
            CatalogueItemOut(**catalogue_item_in.model_dump(), id=catalogue_item_id) if catalogue_item_in else None
        )
        ServiceTestHelpers.mock_get(self.mock_catalogue_item_repository, self._catalogue_item_out)

        # System
        system_in = None
        if system_in_data:
            system_in = SystemIn(**system_in_data)

        self._system_out = SystemOut(**system_in.model_dump(), id=system_id) if system_in else None
        ServiceTestHelpers.mock_get(self.mock_system_repository, self._system_out)

        # Usage status
        usage_status_in = None
        if usage_status_in_data:
            usage_status_in = UsageStatusIn(**usage_status_in_data)

        self._usage_status_out = (
            UsageStatusOut(**{**usage_status_in.model_dump(), "_id": item_data["usage_status_id"]})
            if usage_status_in
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_usage_status_repository, self._usage_status_out)

        # Rule
        self.mock_rule_repository.check_exists.return_value = stored_rule_exists

        # Item

        # When properties are given need to add any property `id`s and ensure the expected data inserts them as well
        property_post_schemas = []
        expected_properties_in = []
        if "properties" in item_data and item_data["properties"]:
            _, property_post_schemas = self.construct_properties_in_and_post_with_ids(
                catalogue_category_in.properties, item_data["properties"]
            )

        self._item_post = ItemPostSchema(**{**item_data, **ids_to_insert, "properties": property_post_schemas})

        # Any missing properties should be inherited from the catalogue item
        supplied_properties = property_post_schemas
        supplied_properties_dict = {
            supplied_property.id: supplied_property for supplied_property in supplied_properties
        }
        self._expected_merged_properties = []

        if self._catalogue_item_out and self._catalogue_category_out:
            for prop in self._catalogue_item_out.properties:
                supplied_property = supplied_properties_dict.get(prop.id)
                self._expected_merged_properties.append(
                    supplied_property if supplied_property else PropertyPostSchema(**prop.model_dump())
                )

            expected_properties_in = utils.process_properties(
                self._catalogue_category_out.properties, self._expected_merged_properties
            )

        self._mock_start_transaction_impacting_number_of_spares(
            stored_spares_definition_out_data, raise_write_conflict_once
        )

        self._expected_item_in = ItemIn(
            **{
                **item_data,
                **ids_to_insert,
                "usage_status": self._usage_status_out.value if self._usage_status_out else "unknown",
                "properties": expected_properties_in,
            }
        )
        self._expected_item_out = ItemOut(**self._expected_item_in.model_dump(), id=ObjectId())

        ServiceTestHelpers.mock_create(self.mock_item_repository, self._expected_item_out)

    def call_create(self) -> None:
        """Calls the `ItemService` `create` method with the appropriate data from a prior call to `mock_create`."""

        self._created_item = self.item_service.create(self._item_post, self._user_authorised)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_service.create(self._item_post, self._user_authorised)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        # This is the get for the catalogue item
        self.mock_catalogue_item_repository.get.assert_called_once_with(self._item_post.catalogue_item_id)

        # This is the get for the catalogue category
        self.mock_catalogue_category_repository.get.assert_called_once_with(
            self._catalogue_item_out.catalogue_category_id
        )

        # This is the get for the system
        self.mock_system_repository.get.assert_called_once_with(self._item_post.system_id)

        # This is the get for the usage status
        self.mock_usage_status_repository.get.assert_called_once_with(self._item_post.usage_status_id)

        # Would only be called if not bypassing rule
        if not self._user_authorised:
            # This is the get for the rule
            self.mock_rule_repository.check_exists.assert_called_once_with(
                src_system_type_id=None,
                dst_system_type_id=self._system_out.type_id,
                dst_usage_status_id=self._item_post.usage_status_id,
            )

        self.wrapped_utils.process_properties.assert_called_once_with(
            self._catalogue_category_out.properties, self._expected_merged_properties
        )

        self._check_start_transition_impacting_number_of_spares_performed_expected_calls(
            "creating item", str(self._expected_item_in.catalogue_item_id), str(self._expected_item_in.system_id)
        )

        self.mock_item_repository.create.assert_called_once_with(
            self._expected_item_in, session=self.mock_transaction_session
        )

        assert self._created_item == self._expected_item_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_item_repository.create.assert_not_called()
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating an item."""

    def test_create_without_properties(self):
        """Test creating an item without any properties in the catalogue item or item."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_no_properties_provided(self):
        """Test creating an item when none of the properties present in the catalogue item are defined in the item."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_all_properties_provided(self):
        """Test creating an item when all properties present in the catalogue item are defined in the item."""

        self.mock_create(
            ITEM_DATA_NEW_WITH_ALL_PROPERTIES,
            catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_spares_definition_defined(self):
        """Test creating an item when there is a spares definition defined."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_spares_definition_defined_write_conflict_once(self):
        """Test creating an item when there is a spares definition defined and a write conflict occurs once and then
        the create succeeds on retry."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            raise_write_conflict_once=True,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_catalogue_item_id(self):
        """Test creating an item with a non-existent catalogue item ID."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=None,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No catalogue item found with ID '{self._item_post.catalogue_item_id}'"
        )

    def test_create_with_catalogue_item_with_non_existent_catalogue_category_id(self):
        """Test creating an item with a catalogue item that has a non-existent catalogue category ID."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=None,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create_expecting_error(DatabaseIntegrityError)
        self.check_create_failed_with_exception(
            f"No catalogue category found with ID '{self._catalogue_item_out.catalogue_category_id}'"
        )

    def test_create_with_non_existent_system_id(self):
        """Test creating an item with a non-existent system ID."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=None,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No system found with ID '{self._item_post.system_id}'")

    def test_create_with_non_existent_usage_status_id(self):
        """Test creating an item with a non-existent usage status ID."""

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No usage status found with ID '{self._item_post.usage_status_id}'")

    def test_create_with_non_existent_rule(self):
        """
        Test creating an item when there isn't a creation rule defined that allows items to be created in the
        specified system with the specified usage status.
        """

        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_rule_exists=False,
        )
        self.call_create_expecting_error(InvalidActionError)
        self.check_create_failed_with_exception(
            "No rule found for creating items in the specified system with the specified usage status"
        )

    def test_create_with_non_existent_rule_when_authorised(self):
        """
        Test creating an item when there isn't a creation rule defined, but the user is authorised
        """
        self.mock_create(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_rule_exists=False,
            user_is_authorised=True,
        )
        self.call_create()
        self.check_create_success()


class GetDSL(ItemServiceDSL):
    """Base class for `get` tests."""

    _obtained_item_id: str
    _expected_item: MagicMock
    _obtained_item: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_item = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_item_repository, self._expected_item)

    def call_get(self, item_id: str) -> None:
        """
        Calls the `ItemService` `get` method.

        :param item_id: ID of the item to be obtained.
        """

        self._obtained_item_id = item_id
        self._obtained_item = self.item_service.get(item_id)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.mock_item_repository.get.assert_called_once_with(self._obtained_item_id)
        assert self._obtained_item == self._expected_item


class TestGet(GetDSL):
    """Tests for getting an item."""

    def test_get(self):
        """Test getting an item."""

        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class ListDSL(ItemServiceDSL):
    """Base class for `list` tests"""

    _system_id_filter: Optional[str]
    _catalogue_item_id_filter: Optional[str]
    _expected_items: MagicMock
    _obtained_items: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_items = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_item_repository, self._expected_items)

    def call_list(self, system_id: Optional[str], catalogue_item_id: Optional[str]) -> None:
        """
        Calls the `CatalogueItemService` `list` method.

        :param system_id: ID of the system to query by, or `None`.
        :param catalogue_item_id: ID of the catalogue item to query by, or `None`.
        """

        self._system_id_filter = system_id
        self._catalogue_item_id_filter = catalogue_item_id
        self._obtained_items = self.item_service.list(system_id, catalogue_item_id)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_item_repository.list.assert_called_once_with(self._system_id_filter, self._catalogue_item_id_filter)

        assert self._obtained_items == self._expected_items


class TestList(ListDSL):
    """Tests for listing items."""

    def test_list(self):
        """Test listing items."""

        self.mock_list()
        self.call_list(str(ObjectId()), str(ObjectId()))
        self.check_list_success()


# pylint:disable=too-many-instance-attributes
class UpdateDSL(ItemServiceDSL):
    """Base class for `update` tests."""

    _stored_item: Optional[ItemOut]
    _stored_system_out: Optional[SystemOut]
    _stored_catalogue_item_out: Optional[CatalogueItemOut]
    _stored_catalogue_category_out: Optional[CatalogueCategoryOut]
    _new_system_out: Optional[SystemOut]
    _item_patch: ItemPatchSchema
    _expected_item_in: ItemIn
    _expected_item_out: MagicMock
    _updated_item_id: str
    _updated_item: MagicMock
    _update_exception: pytest.ExceptionInfo

    _user_authorised: bool
    _moving_system: bool
    _updating_usage_status: bool
    _updating_properties: bool
    _expected_merged_properties: List[PropertyPostSchema]

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    # pylint:disable=too-many-locals
    def mock_update(
        self,
        item_id: str,
        item_update_data: dict,
        stored_item_data: Optional[dict],
        stored_usage_status_in_data: dict,
        stored_system_in_data: Optional[dict] = None,
        stored_catalogue_item_data: Optional[dict] = None,
        stored_catalogue_category_in_data: Optional[dict] = None,
        stored_spares_definition_out_data: Optional[dict] = None,
        stored_rule_exists: Optional[bool] = None,
        new_usage_status_in_data: Optional[dict] = None,
        new_system_in_data: Optional[dict] = None,
        raise_write_conflict_once: bool = False,
        user_is_authorised=False,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `update` service method.

        :param item_id: ID of the item that will be obtained.
        :param item_update_data: Dictionary containing the basic patch data as would be required for a `ItemPatchSchema`
                                 but without mandatory IDs (except usage_status_id) or property IDs.
        :param stored_item_data: Either `None` or a dictionary containing the catalogue basic catalogue item data for
                                 the existing stored catalogue item as would be required for a `ItemPostSchema` but
                                 without mandatory (except usage_status_id) IDs or property IDs.
        :param stored_usage_status_in_data: Dictionary containing the basic usage status data as would be required for a
                                     `UsageStatusIn` database model.
        :param stored_system_in_data: Dictionary containing the system data for the current stored system as would be
                                      required for a `SystemIn` database model.
        :param stored_catalogue_item_data: Either `None` or a dictionary containing the catalogue basic catalogue item
                                 data for the existing stored catalogue item as would be required for a
                                 `CatalogueItemPostSchema` but without any mandatory IDs or property IDs.
        :param stored_catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data
                                                  for the existing stored catalogue category as would be required for a
                                                  `CatalogueCategoryIn` database model.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for `SparesDefinitionOut` database model.
        :param stored_rule_exists: Whether a stored rule exists for the update operation (only applicable for moving
                                   between systems of different types).
        :param new_usage_status_in_data: Either `None` or a dictionary containing the usage status data for the new
                                         stored usage status as would be required for a `UsageStatus` database model.
        :param new_system_in_data: Either `None` or a dictionary containing the system data for the new stored system as
                                   would be required for a `SystemIn` database model.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.
        :param user_is_authorised: Whether the request is authorised to bypass functionality such as checking rules.
        """

        self._user_authorised = user_is_authorised

        # Add property ids to the stored catalogue item and item if needed

        catalogue_category_id = str(ObjectId())

        # pylint:disable=fixme
        # TODO: Could simplify - copied from catalogue items - including the stored part below
        stored_catalogue_category_in = (
            CatalogueCategoryIn(**stored_catalogue_category_in_data) if stored_catalogue_category_in_data else None
        )

        expected_stored_catalogue_item_properties_in = []
        if (
            stored_catalogue_category_in
            and "properties" in stored_catalogue_item_data
            and stored_catalogue_item_data["properties"]
        ):
            expected_stored_catalogue_item_properties_in, _ = self.construct_properties_in_and_post_with_ids(
                stored_catalogue_category_in.properties, stored_catalogue_item_data["properties"]
            )

        # Stored catalogue item
        self._stored_catalogue_item_out = (
            CatalogueItemOut(
                **CatalogueItemIn(
                    **{
                        **stored_catalogue_item_data,
                        "catalogue_category_id": catalogue_category_id,
                        "manufacturer_id": str(ObjectId()),
                        "properties": expected_stored_catalogue_item_properties_in,
                    },
                    number_of_spares=None,
                ).model_dump(),
                id=str(ObjectId()),
            )
            if stored_catalogue_item_data
            else None
        )

        expected_stored_item_properties_in = []
        if stored_item_data and "properties" in stored_item_data and stored_item_data["properties"]:
            expected_stored_item_properties_in, _ = self.construct_properties_in_and_post_with_ids(
                stored_catalogue_category_in.properties, stored_item_data["properties"]
            )

        # Generate mandatory IDs to be inserted where needed
        stored_ids_to_insert = {
            "catalogue_item_id": catalogue_category_id,
            "system_id": str(ObjectId()),
        }

        # Stored item
        self._stored_item = (
            ItemOut(
                **ItemIn(
                    **{
                        **stored_item_data,
                        **stored_ids_to_insert,
                        "usage_status": stored_usage_status_in_data["value"],
                        "properties": expected_stored_item_properties_in,
                    },
                ).model_dump(),
                id=item_id,
            )
            if stored_item_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_item_repository, self._stored_item)

        self._moving_system = (
            "system_id" in item_update_data
            and self._stored_item is not None
            and self._stored_item.system_id != item_update_data["system_id"]
        )

        self._mock_handle_system_and_usage_status_id_update(
            item_update_data,
            stored_item_data,
            stored_system_in_data,
            stored_rule_exists,
            new_usage_status_in_data,
            new_system_in_data,
        )

        expected_properties_in = []
        self._updating_properties = "properties" in item_update_data
        if self._updating_properties:
            expected_properties_in = self._mock_handle_properties_update(item_update_data, stored_catalogue_category_in)

        self._mock_start_transaction_impacting_number_of_spares(
            stored_spares_definition_out_data, raise_write_conflict_once
        )

        # Updated item
        self._expected_item_out = MagicMock()
        ServiceTestHelpers.mock_update(self.mock_item_repository, self._expected_item_out)

        # Patch schema
        self._item_patch = ItemPatchSchema(**item_update_data)

        # Construct the expected input for the repository
        merged_item_data = {
            **(self._stored_item.model_dump() if self._stored_item else {}),
            **stored_ids_to_insert,
            "usage_status": stored_usage_status_in_data["value"],
            **item_update_data,
        }
        self._expected_item_in = ItemIn(**{**merged_item_data, "properties": expected_properties_in})

    def call_update(self, item_id: str) -> None:
        """
        Calls the `ItemService` `update` method with the appropriate data from a prior call to `mock_update`.

        :param item_id: ID of the item to be updated.
        """

        self._updated_item_id = item_id
        self._updated_item = self.item_service.update(item_id, self._item_patch, self._user_authorised)

    def call_update_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `update` method with the appropriate data from a prior call to
        `mock_update` while expecting an error to be raised.

        :param item_id: ID of the item to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_service.update(item_id, self._item_patch, self._user_authorised)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        self.mock_item_repository.get.assert_called_once_with(self._updated_item_id)

        self._check_handle_system_and_usage_status_id_update_success()
        self._check_handle_properties_update_success()

        if self._moving_system:
            self._check_start_transition_impacting_number_of_spares_performed_expected_calls(
                "updating item",
                self._stored_item.catalogue_item_id,
                str(self._expected_item_in.system_id),
            )
            self.mock_item_repository.update.assert_called_once_with(
                self._updated_item_id, self._expected_item_in, session=self.mock_transaction_session
            )
        else:
            self.mock_item_repository.update.assert_called_once_with(self._updated_item_id, self._expected_item_in)

        assert self._updated_item == self._expected_item_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_item_repository.update.assert_not_called()

        assert str(self._update_exception.value) == message

    def _mock_handle_system_and_usage_status_id_update(
        self,
        item_update_data: dict,
        stored_item_data: Optional[dict],
        stored_system_in_data: Optional[dict],
        stored_rule_exists: Optional[bool],
        new_usage_status_in_data: Optional[dict],
        new_system_in_data: Optional[dict],
    ) -> None:
        """
        Mocks repository methods appropriately for a call to `_handle_system_and_usage_status_id_update`.

        :param item_update_data: Dictionary containing the basic patch data as would be required for a `ItemPatchSchema`
                                 but without mandatory IDs (except usage_status_id) or property IDs.
        :param stored_item_data: Either `None` or a dictionary containing the catalogue basic catalogue item data for
                                 the existing stored catalogue item as would be required for a `ItemPostSchema` but
                                 without mandatory (except usage_status_id) IDs or property IDs.
        :param stored_system_in_data: Dictionary containing the system data for the current stored system as would be
                                      required for a `SystemIn` database model.
        :param stored_rule_exists: Whether a stored rule exists for the update operation (only applicable for moving
                                   between systems of different types).
        :param new_usage_status_in_data: Either `None` or a dictionary containing the usage status data for the new
                                         stored usage status as would be required for a `UsageStatus` database model.
        :param new_system_in_data: Either `None` or a dictionary containing the system data for the new stored system as
                                   would be required for a `SystemIn` database model.
        """

        self._updating_usage_status = "usage_status_id" in item_update_data and (
            stored_item_data and item_update_data["usage_status_id"] != stored_item_data["usage_status_id"]
        )

        # Stored system
        if self._moving_system:
            self._new_system_out = (
                SystemOut(
                    **{
                        **SystemIn(**new_system_in_data).model_dump(),
                        "_id": item_update_data["system_id"],
                    },
                )
                if new_system_in_data
                else None
            )
            ServiceTestHelpers.mock_get(self.mock_system_repository, self._new_system_out)

            self._stored_system_out = (
                SystemOut(
                    **{
                        **SystemIn(**stored_system_in_data).model_dump(),
                        "_id": self._stored_item.system_id,
                    },
                )
                if stored_system_in_data
                else None
            )
            ServiceTestHelpers.mock_get(
                self.mock_system_repository,
                self._stored_system_out,
            )

            if (
                self._stored_system_out
                and self._new_system_out
                and self._stored_system_out.type_id != self._new_system_out.type_id
            ):
                self.mock_rule_repository.check_exists.return_value = stored_rule_exists

        # Stored usage status
        if self._updating_usage_status:
            item_update_data["usage_status"] = (
                new_usage_status_in_data["value"] if new_usage_status_in_data else "unknown"
            )

            ServiceTestHelpers.mock_get(
                self.mock_usage_status_repository,
                (
                    UsageStatusOut(
                        **{
                            **UsageStatusIn(**new_usage_status_in_data).model_dump(),
                            "_id": item_update_data["usage_status_id"],
                        },
                    )
                    if new_usage_status_in_data
                    else None
                ),
            )

    def _mock_handle_properties_update(
        self, item_update_data: dict, stored_catalogue_category_in: Optional[CatalogueCategoryIn]
    ) -> List[dict]:
        """
        Mocks repository methods appropriately for a call to `_handle_properties_update`.

        Also inserts the relevant IDs into the properties in `item_update_data`.

        :param item_update_data: Dictionary containing the basic patch data as would be required for a `ItemPatchSchema`
                                 but without mandatory IDs (except usage_status_id) or property IDs.
        :param stored_catalogue_category_in: Stored catalogue category in database model.
        :return: A list of expected processed and validated supplied properties for the Item.
        """

        # When properties are given need to add any property `id`s and ensure the expected data inserts them as well
        property_post_schemas = []
        expected_properties_in = []

        # Catalogue item
        ServiceTestHelpers.mock_get(self.mock_catalogue_item_repository, self._stored_catalogue_item_out)

        # Catalogue category
        self._stored_catalogue_category_out = (
            CatalogueCategoryOut(
                **stored_catalogue_category_in.model_dump(by_alias=True),
                id=self._stored_catalogue_item_out.catalogue_category_id,
            )
            if stored_catalogue_category_in
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._stored_catalogue_category_out)

        if self._updating_properties and item_update_data["properties"]:
            _, property_post_schemas = self.construct_properties_in_and_post_with_ids(
                stored_catalogue_category_in.properties, item_update_data["properties"]
            )

        # Any missing properties should be inherited from the catalogue item
        supplied_properties = property_post_schemas
        supplied_properties_dict = {
            supplied_property.id: supplied_property for supplied_property in supplied_properties
        }
        self._expected_merged_properties = []

        if self._stored_catalogue_item_out and self._stored_catalogue_category_out:
            for prop in self._stored_catalogue_item_out.properties:
                supplied_property = supplied_properties_dict.get(prop.id)
                self._expected_merged_properties.append(
                    supplied_property if supplied_property else PropertyPostSchema(**prop.model_dump())
                )

            expected_properties_in = utils.process_properties(
                self._stored_catalogue_category_out.properties, self._expected_merged_properties
            )

        item_update_data["properties"] = property_post_schemas

        return expected_properties_in

    def _check_handle_system_and_usage_status_id_update_success(self) -> None:
        """Checks that a call to `_handle_system_and_usage_status_id_update` worked as expected."""

        if self._moving_system:
            self.mock_system_repository.get.assert_has_calls(
                [call(self._item_patch.system_id), call(self._stored_item.system_id)]
            )

            if self._stored_system_out.type_id != self._new_system_out.type_id and not self._user_authorised:
                self.mock_rule_repository.check_exists.assert_called_once_with(
                    src_system_type_id=self._stored_system_out.type_id,
                    dst_system_type_id=self._new_system_out.type_id,
                    dst_usage_status_id=(
                        self._item_patch.usage_status_id
                        if self._updating_usage_status
                        else self._stored_item.usage_status_id
                    ),
                )
            else:
                self.mock_rule_repository.check_exists.assert_not_called()
        else:
            self.mock_rule_repository.check_exists.assert_not_called()

        if self._updating_usage_status:
            self.mock_usage_status_repository.get.assert_called_once_with(self._item_patch.usage_status_id)

    def _check_handle_properties_update_success(self) -> None:
        """Checks that a call to `_handle_properties_update` worked as expected."""

        if self._updating_properties:
            self.mock_catalogue_item_repository.get.assert_called_once_with(self._stored_item.catalogue_item_id)

            self.mock_catalogue_category_repository.get.assert_called_once_with(
                self._stored_catalogue_item_out.catalogue_category_id
            )

            self.wrapped_utils.process_properties.assert_called_once_with(
                self._stored_catalogue_category_out.properties, self._expected_merged_properties
            )
        else:
            self.mock_catalogue_category_repository.get.assert_not_called()
            self.wrapped_utils.process_properties.assert_not_called()


class TestUpdate(UpdateDSL):
    """Tests for updating an item."""

    def test_update_all_fields_except_ids_or_properties(self):
        """Test updating all fields of an item except any of its `_id` fields or properties."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES,
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_properties_with_all(self):
        """Test updating an item's `properties` while populating all available properties."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            # Strictly speaking we wouldn't allow this in the first place - the stored data is missing a mandatory
            # property but it is irrelevant for this test and saves creating a new version
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            stored_catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_properties_with_mandatory_only(self):
        """Test updating an item's `properties` while only populating the mandatory properties."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_NEW_WITH_MANDATORY_PROPERTIES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            # Strictly speaking we wouldn't allow this in the first place - the stored data is missing a mandatory
            # property but it is irrelevant for this test and saves creating a new version
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            stored_catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_catalogue_item_id(self):
        """Test updating an item's `catalogue_item_id`."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"catalogue_item_id": str(ObjectId())},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_update_expecting_error(item_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot change the catalogue item the item belongs to")

    def test_update_system_id(self):
        """Test updating an item's `system_id`."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId())},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            new_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_id_with_spares_definition_defined(self):
        """Test updating an item's `system_id` when there is a spares definition defined."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId())},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            new_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_id_with_spares_definition_defined_write_conflict_once(self):
        """Test updating an item's `system_id` when there is a spares definition defined and a write conflict occurs
        once and then the update succeeds on a retry."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId())},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            new_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
            raise_write_conflict_once=True,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_with_non_existent_system_id(self):
        """Test updating an item's `system_id` to a non-existent system."""

        item_id = str(ObjectId())
        system_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": system_id},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=None,
        )
        self.call_update_expecting_error(item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No system found with ID '{system_id}'")

    def test_update_system_and_usage_status_ids(self):
        """Test updating an item's `system_id` and `usage_status_id`."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId()), "usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_rule_exists=True,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data={
                **SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
                "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"],
            },
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_and_usage_status_ids_when_authorised(self):
        """Test updating an item's `system_id` and `usage_status_id` when the user is authorised."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId()), "usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_rule_exists=False,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data={
                **SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
                "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"],
            },
            user_is_authorised=True,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_and_usage_status_ids_with_non_existent_rule(self):
        """Test updating an item's `system_id` and `usage_status_id` when there isn't a rule defined for the change
        of system types."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId()), "usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_rule_exists=False,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data={
                **SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
                "type_id": SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"],
            },
        )
        self.call_update_expecting_error(item_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "No rule found for moving between the given system's types with the same final usage status"
        )

    def test_update_system_and_usage_status_ids_when_systems_have_same_type(self):
        """Test updating an item's `system_id` and `usage_status_id` when the current and new systems have the same
        type."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId()), "usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
        )
        self.call_update_expecting_error(item_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot change usage status of an item when moving between two systems of the same type"
        )

    def test_update_system_and_usage_status_ids_when_systems_have_same_type_when_authorised(self):
        """Test updating an item's `system_id` and `usage_status_id` when the current and new systems have the same
        type, and when the user is authorised."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId()), "usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_B,
            user_is_authorised=True,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_and_usage_status_ids_with_non_existent_usage_status_id(self):
        """Test updating an item's `system_id` while also updating its `usage_status_id` to a non-existent usage
        status."""

        item_id = str(ObjectId())
        usage_status_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId()), "usage_status_id": usage_status_id},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_usage_status_in_data=None,
        )
        self.call_update_expecting_error(item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No usage status found with ID '{usage_status_id}'")

    def test_update_usage_status_id(self):
        """Test updating an item's `usage_status_id`."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_update_expecting_error(item_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot change usage status without moving between systems according to a defined rule"
        )

    def test_update_usage_status_id_when_authorised(self):
        """Test updating an item's `usage_status_id` when the user is authorised"""
        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"usage_status_id": USAGE_STATUS_GET_DATA_IN_USE["id"]},
            stored_item_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
            user_is_authorised=True,
        )

        self.call_update(item_id)
        self.check_update_success()

    def test_update_with_non_existent_id(self):
        """Test updating an item with a non-existent ID."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            stored_item_data=None,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_update_expecting_error(item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No item found with ID '{item_id}'")


class DeleteDSL(ItemServiceDSL):
    """Base class for `delete` tests."""

    _stored_item: Optional[ItemOut]
    _system_out: Optional[SystemOut]
    _delete_item_id: str
    _delete_exception: pytest.ExceptionInfo
    _user_authorised: bool

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def mock_delete(
        self,
        stored_item_data: Optional[dict],
        system_in_data: Optional[dict] = None,
        stored_spares_definition_out_data: Optional[dict] = None,
        stored_rule_exists: bool = True,
        raise_write_conflict_once: bool = False,
        user_is_authorised: bool = False,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `delete` service method.

        :param stored_item_data: Either `None` or a dictionary containing the basic item data for the existing stored
                                 item as would be required for an `ItemPostSchema` but without any mandatory IDs or
                                 property IDs.
        :param system_in_data: Either `None` or a dictionary containing the system data as would be required for a
                               `SystemIn` database model.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for a `SparesDefinitionOut` database model.
        :param stored_rule_exists: Whether a stored rule exists for the delete operation.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.

        :param user_is_authorised: Whether the request is authorised to bypass functionality such as checking rules.
        """

        self._user_authorised = user_is_authorised

        # Generate mandatory IDs to be inserted where needed
        system_id = str(ObjectId())

        # Item
        self._stored_item = (
            ItemOut(
                **ItemIn(
                    **stored_item_data,
                    catalogue_item_id=str(ObjectId()),
                    system_id=system_id,
                    # Need a value here but doesn't matter if it matches the usage status or not
                    usage_status="test",
                ).model_dump(),
                id=str(ObjectId()),
            )
            if stored_item_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_item_repository, self._stored_item)

        # System
        system_in = None
        if system_in_data:
            system_in = SystemIn(**system_in_data)

        self._system_out = SystemOut(**system_in.model_dump(), id=system_id) if system_in else None
        ServiceTestHelpers.mock_get(self.mock_system_repository, self._system_out)

        # Rule
        self.mock_rule_repository.check_exists.return_value = stored_rule_exists

        self._mock_start_transaction_impacting_number_of_spares(
            stored_spares_definition_out_data, raise_write_conflict_once
        )

    def call_delete(self, item_id: str) -> None:
        """
        Calls the `ItemService` `delete` method.

        :param item_id: ID of the item to be deleted.
        """

        self._delete_item_id = item_id
        self.item_service.delete(item_id, self._user_authorised)

    def call_delete_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `delete` method.

        :param item_id: ID of the item to be deleted.
        :param error_type: Expected exception to be raised.
        """

        self._delete_item_id = item_id
        with pytest.raises(error_type) as exc:
            self.item_service.delete(item_id, self._user_authorised)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        # This is the get for the item
        self.mock_item_repository.get.assert_called_once_with(self._delete_item_id)

        # This is the get for the system
        self.mock_system_repository.get.assert_called_once_with(self._stored_item.system_id)

        # Would only be called if not bypassing rules
        if not self._user_authorised:
            # This is the get for the rule
            self.mock_rule_repository.check_exists.assert_called_once_with(
                src_system_type_id=self._system_out.type_id,
                dst_system_type_id=None,
                dst_usage_status_id=None,
            )

        self._check_start_transition_impacting_number_of_spares_performed_expected_calls(
            "deleting item", self._stored_item.catalogue_item_id
        )
        self.mock_item_repository.delete.assert_called_once_with(
            self._delete_item_id, session=self.mock_transaction_session
        )

    def check_delete_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_item_repository.get.assert_called_once_with(self._delete_item_id)
        self.mock_item_repository.delete.assert_not_called()

        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting an item."""

    def test_delete(self):
        """Test deleting an item."""

        self.mock_delete(ITEM_DATA_NEW_REQUIRED_VALUES_ONLY, system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_spares_definition_defined(self):
        """Test deleting an item when there is a spares definition defined."""

        self.mock_delete(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
        )
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_spares_definition_defined_write_conflict_once(self):
        """Test deleting an item when there is a spares definition defined and a write conflict occurs once and then
        the delete succeeds on a retry."""

        self.mock_delete(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            raise_write_conflict_once=True,
        )
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_non_existent_id(self):
        """Test deleting an item with a non-existent ID."""

        item_id = str(ObjectId())

        self.mock_delete(None)
        self.call_delete_expecting_error(item_id, MissingRecordError)
        self.check_delete_failed_with_exception(f"No item found with ID '{item_id}'")

    def test_delete_with_non_existent_system_id(self):
        """Test deleting an item that has a non-existent system ID."""
        self.mock_delete(ITEM_DATA_NEW_REQUIRED_VALUES_ONLY, system_in_data=None)
        self.call_delete_expecting_error(str(ObjectId()), DatabaseIntegrityError)
        self.check_delete_failed_with_exception(f"No system found with ID '{self._stored_item.system_id}'")

    def test_delete_with_non_existent_rule(self):
        """
        Test deleting an item when there isn't a delete rule defined that allows items to be deleted from the current
        system.
        """
        self.mock_delete(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_rule_exists=False,
        )
        self.call_delete_expecting_error(str(ObjectId()), InvalidActionError)
        self.check_delete_failed_with_exception("No rule found for deleting items from the current system")

    def test_delete_with_non_existent_rule_when_authorised(self):
        """
        Test deleting an item when there isn't a delete rule defined, but the user is authorised.
        """
        self.mock_delete(
            ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            stored_rule_exists=False,
            user_is_authorised=True,
        )
        self.call_delete(str(ObjectId()))
        self.check_delete_success()


class ValidateCreateDSL(ItemServiceDSL):
    """Base class for `_validate_create` tests."""

    _catalogue_item_out: Optional[CatalogueItemOut]
    _item_data: dict
    _is_duplicate_serial_number_in_data: bool
    _is_duplicate_serial_number_in_db: bool
    _validate_create_result: ValidationResultSchema
    _validate_create_exception: pytest.ExceptionInfo

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def mock_validate_create(
        self,
        item_data: dict,
        catalogue_item_out_data: Optional[dict] = None,
        catalogue_category_out_data: Optional[dict] = None,
        system_in_data: Optional[dict] = None,
        usage_status_in_data: Optional[dict] = None,
        stored_rule_exists: bool = True,
        is_duplicate_serial_number_in_data: bool = False,
        is_duplicate_serial_number_in_db: bool = False,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `_validate_create` service method.

        :param item_data: Dictionary containing the item data to validate. The `system_id` is added automatically if
                          `system_in_data` is given, but any other mandatory IDs (e.g. `catalogue_item_id`) must be
                          included already, referencing the relevant `_id` of the corresponding `*_out_data` given.
        :param catalogue_item_out_data: Either `None` or a dictionary containing the catalogue item data as would be
                                        required for a `CatalogueItemOut` database model.
        :param catalogue_category_out_data: Either `None` or a dictionary containing the catalogue category data as
                                            would be required for a `CatalogueCategoryOut` database model.
        :param system_in_data: Either `None` or a dictionary containing the system data as would be required for a
                               `SystemIn` database model.
        :param usage_status_in_data: Either `None` or a dictionary containing the usage status data as would be required
                                     for a `UsageStatusIn` database model.
        :param stored_rule_exists: Whether a stored rule exists for the create operation.
        :param is_duplicate_serial_number_in_data: Whether another item within the provided bulk data shares this item's
                                                   serial number.
        :param is_duplicate_serial_number_in_db: Whether an item with the same serial number already exists in the
                                                 database.
        """

        self._item_data = {**item_data}
        self._is_duplicate_serial_number_in_data = is_duplicate_serial_number_in_data
        self._is_duplicate_serial_number_in_db = is_duplicate_serial_number_in_db

        # Catalogue item
        self._catalogue_item_out = CatalogueItemOut(**catalogue_item_out_data) if catalogue_item_out_data else None
        ServiceTestHelpers.mock_get(self.mock_catalogue_item_repository, self._catalogue_item_out)

        # Catalogue category (looked up via the catalogue item)
        ServiceTestHelpers.mock_get(
            self.mock_catalogue_category_repository,
            CatalogueCategoryOut(**catalogue_category_out_data) if catalogue_category_out_data else None,
        )

        # System
        system_in = SystemIn(**system_in_data) if system_in_data else None
        system_out = SystemOut(**system_in.model_dump(), id=ObjectId()) if system_in else None
        ServiceTestHelpers.mock_get(self.mock_system_repository, system_out)
        if system_out:
            self._item_data["system_id"] = system_out.id

        # Usage status
        usage_status_in = UsageStatusIn(**usage_status_in_data) if usage_status_in_data else None
        usage_status_out = (
            UsageStatusOut(**{**usage_status_in.model_dump(), "_id": self._item_data["usage_status_id"]})
            if usage_status_in and "usage_status_id" in self._item_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_usage_status_repository, usage_status_out)

        # Rule
        self.mock_rule_repository.check_exists.return_value = stored_rule_exists

    def call_validate_create(self) -> None:
        """Calls the `ItemService` `_validate_create` method with the appropriate data from a prior call to
        `mock_validate_create`."""

        self._validate_create_result = self.item_service._validate_create(  # pylint:disable=protected-access
            index=0,
            item_data=self._item_data,
            is_duplicate_serial_number_in_data=self._is_duplicate_serial_number_in_data,
            is_duplicate_serial_number_in_db=self._is_duplicate_serial_number_in_db,
        )

    def call_validate_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `_validate_create` method with the appropriate data from a prior call to
        `mock_validate_create` while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_service._validate_create(  # pylint:disable=protected-access
                index=0,
                item_data=self._item_data,
                is_duplicate_serial_number_in_data=self._is_duplicate_serial_number_in_data,
                is_duplicate_serial_number_in_db=self._is_duplicate_serial_number_in_db,
            )
        self._validate_create_exception = exc

    def check_validate_create_success(
        self, expected_warnings: list[ValidationErrorSchema], expected_errors: list[ValidationErrorSchema]
    ) -> None:
        """Checks that a prior call to `call_validate_create` worked as expected.

        :param expected_warnings: Expected validation warnings.
        :param expected_errors: Expected validation errors.
        """

        if "catalogue_item_id" in self._item_data:
            self.mock_catalogue_item_repository.get.assert_called_once_with(self._item_data["catalogue_item_id"])

        if "system_id" in self._item_data:
            self.mock_system_repository.get.assert_called_once_with(self._item_data["system_id"])

        if "usage_status_id" in self._item_data:
            self.mock_usage_status_repository.get.assert_called_once_with(self._item_data["usage_status_id"])

        assert self._validate_create_result == ValidationResultSchema(
            index=0, warnings=expected_warnings, errors=expected_errors
        )

    def check_validate_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_validate_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        assert str(self._validate_create_exception.value) == message


class TestValidateCreate(ValidateCreateDSL):
    """Tests for validating item data for creation."""

    def test_validate_create_with_valid_data(self):
        """Test validating item data for creation with valid data."""

        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(expected_warnings=[], expected_errors=[])

    def test_validate_create_with_invalid_schema(self):
        """Test validating item data for creation when the schema itself is invalid."""

        item_data = {
            "is_defective": "not-a-boolean",
            "usage_status_id": str(ObjectId()),
            "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
        }
        self.mock_validate_create(
            item_data,
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="bool_parsing",
                    loc=["is_defective"],
                    msg="Input should be a valid boolean, unable to interpret input",
                    input="not-a-boolean",
                )
            ],
        )

    def test_validate_create_with_non_existent_catalogue_item_id(self):
        """Test validating item data for creation with a non-existent catalogue item ID."""

        catalogue_item_id = str(ObjectId())
        self.mock_validate_create(
            {**ITEM_DATA_NEW_REQUIRED_VALUES_ONLY, "catalogue_item_id": catalogue_item_id},
            catalogue_item_out_data=None,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="missing_record",
                    loc=["catalogue_item_id"],
                    msg=f"No catalogue item found with ID '{catalogue_item_id}'",
                    input=catalogue_item_id,
                )
            ],
        )

    def test_validate_create_with_catalogue_item_with_non_existent_catalogue_category_id(self):
        """Test validating item data for creation with a catalogue item that has a non-existent catalogue category
        ID. This indicates a database integrity issue so is expected to raise rather than be reported as a
        warning/error."""

        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=None,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create_expecting_error(DatabaseIntegrityError)
        self.check_validate_create_failed_with_exception(
            f"No catalogue category found with ID '{self._catalogue_item_out.catalogue_category_id}'"
        )

    def test_validate_create_with_non_existent_system_id(self):
        """Test validating item data for creation with a non-existent system ID."""

        system_id = str(ObjectId())
        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
                "system_id": system_id,
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=None,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="missing_record",
                    loc=["system_id"],
                    msg=f"No system found with ID '{system_id}'",
                    input=system_id,
                )
            ],
        )

    def test_validate_create_with_non_existent_usage_status_id(self):
        """Test validating item data for creation with a non-existent usage status ID."""

        usage_status_id = ITEM_DATA_NEW_REQUIRED_VALUES_ONLY["usage_status_id"]
        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=None,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="missing_record",
                    loc=["usage_status_id"],
                    msg=f"No usage status found with ID '{usage_status_id}'",
                    input=usage_status_id,
                )
            ],
        )

    def test_validate_create_with_non_existent_rule(self):
        """Test validating item data for creation when there isn't a creation rule defined. This should be reported as a
        warning as privileged users are allowed to bypass the rule."""

        usage_status_id = ITEM_DATA_NEW_REQUIRED_VALUES_ONLY["usage_status_id"]
        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
            stored_rule_exists=False,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[
                ValidationErrorSchema(
                    type="missing_rule",
                    loc=["usage_status_id"],
                    msg="No rule found for creating items in the specified system with the specified usage status",
                    input=usage_status_id,
                )
            ],
            expected_errors=[],
        )

    def test_validate_create_with_duplicate_serial_number_in_database(self):
        """Test validating item data for creation with a serial number that is a duplicate of one in the database."""

        serial_number = ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES["serial_number"]
        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
            is_duplicate_serial_number_in_db=True,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[
                ValidationErrorSchema(
                    type="duplicate_record",
                    loc=["serial_number"],
                    msg=f"Duplicate record found with the same serial number '{serial_number}'",
                    input=serial_number,
                )
            ],
            expected_errors=[],
        )

    def test_validate_create_with_duplicate_serial_number_in_data(self):
        """Test validating item data for creation with a serial number that is a duplicate of another provided item."""

        serial_number = ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES["serial_number"]
        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
            is_duplicate_serial_number_in_data=True,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[
                ValidationErrorSchema(
                    type="duplicate_record",
                    loc=["serial_number"],
                    msg=f"Duplicate serial number '{serial_number}' found within the provided items",
                    input=serial_number,
                )
            ],
            expected_errors=[],
        )

    def test_validate_create_with_duplicate_serial_number_in_data_and_database(self):
        """Test validating item data for creation with a serial number that is a duplicate both within the provided
        data and in the database only returns the "duplicate in data" warning, as it takes precedence."""

        serial_number = ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES["serial_number"]
        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_ALL_VALUES_NO_PROPERTIES,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
            is_duplicate_serial_number_in_data=True,
            is_duplicate_serial_number_in_db=True,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[
                ValidationErrorSchema(
                    type="duplicate_record",
                    loc=["serial_number"],
                    msg=f"Duplicate serial number '{serial_number}' found within the provided items",
                    input=serial_number,
                )
            ],
            expected_errors=[],
        )

    def test_validate_create_with_non_string_serial_number(self):
        """Test validating item data for creation with a non-string serial number is reported as a schema error
        rather than crashing or participating in duplicate detection."""

        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
                "serial_number": 12345,
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="string_type",
                    loc=["serial_number"],
                    msg="Input should be a valid string",
                    input=12345,
                ),
            ],
        )

    def test_validate_create_with_non_list_properties(self):
        """Test validating item data for creation with a non-list `properties` value does not crash and is reported
        as a schema error."""

        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
                "properties": 5,
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="list_type",
                    loc=["properties"],
                    msg="Input should be a valid list",
                    input=5,
                ),
            ],
        )

    def test_validate_create_with_non_dict_property(self):
        """Test validating item data for creation with a non-dictionary entry in `properties` does not crash and is
        reported as a schema error."""

        self.mock_validate_create(
            {
                **ITEM_DATA_NEW_REQUIRED_VALUES_ONLY,
                "catalogue_item_id": str(CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES["_id"]),
                "properties": [5],
            },
            catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            system_in_data=SYSTEM_IN_DATA_STORAGE_NO_PARENT_A,
            usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="model_type",
                    loc=["properties", 0],
                    msg="Input should be a valid dictionary or instance of PropertyPostSchema",
                    input=5,
                ),
            ],
        )


class BulkValidateCreateDSL(ItemServiceDSL):
    """Base class for `bulk_validate_create` tests."""

    _mock_results: List[ValidationResultSchema]
    _mock_validate_create: MagicMock
    _result: BulkValidationResultSchema

    def mock_bulk_validate_create(self, mock_items: list[dict], is_duplicate_serial_number_side_effect=None) -> None:
        """
        Mocks `_validate_create` and the item repository's `is_duplicate_serial_number` appropriately to test the
        `bulk_validate_create` service method.

        :param mock_items: List of mock item data dictionaries to validate.
        :param is_duplicate_serial_number_side_effect: Callable to use as the `is_duplicate_serial_number` mock's
                                                        side effect, or `None` to have it always return `False`.
        """

        self._mock_results = [
            ValidationResultSchema(index=index, warnings=[], errors=[]) for index in range(len(mock_items))
        ]
        self._mock_validate_create = MagicMock(side_effect=self._mock_results)

        if is_duplicate_serial_number_side_effect is not None:
            self.mock_item_repository.is_duplicate_serial_number.side_effect = is_duplicate_serial_number_side_effect
        else:
            self.mock_item_repository.is_duplicate_serial_number.return_value = False

    def call_bulk_validate_create(self, mock_items: list[dict]) -> None:
        """
        Calls the `ItemService` `bulk_validate_create` method with the appropriate data from a prior call to
        `mock_bulk_validate_create`.

        :param mock_items: List of mock item data dictionaries to validate.
        """

        with patch.object(self.item_service, "_validate_create", self._mock_validate_create):
            self._result = self.item_service.bulk_validate_create(mock_items)

    def check_bulk_validate_create_success(self, expected_validate_create_calls: list) -> None:
        """
        Checks that a prior call to `call_bulk_validate_create` worked as expected.

        :param expected_validate_create_calls: Expected calls that should have been made to `_validate_create`.
        """

        assert self._mock_validate_create.call_args_list == expected_validate_create_calls
        assert self._result == BulkValidationResultSchema(results=self._mock_results)


class TestBulkValidateCreate(BulkValidateCreateDSL):
    """Tests for bulk validating items data for creation."""

    def test_bulk_validate_create(self):
        """Test bulk validate correctly returns a list of validation results for the individual items."""

        mock_items = [{"serial_number": "1"}, {"serial_number": "2"}, {"serial_number": "3"}]
        self.mock_bulk_validate_create(mock_items)

        self.call_bulk_validate_create(mock_items)

        # No item shares a serial number with another, so none are flagged as duplicates in the data
        self.check_bulk_validate_create_success(
            expected_validate_create_calls=[
                call(index, mock_item, is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=False)
                for index, mock_item in enumerate(mock_items)
            ]
        )

    def test_bulk_validate_create_detects_duplicate_serial_numbers_in_data(self):
        """Test bulk validate flags items sharing a serial number as duplicates."""

        mock_items = [
            # Duplicate pair sharing a serial number (serial numbers are unique regardless of catalogue item)
            {"catalogue_item_id": str(ObjectId()), "serial_number": "duplicate"},
            {"catalogue_item_id": str(ObjectId()), "serial_number": "duplicate"},
            # Different serial number, so not a duplicate
            {"catalogue_item_id": str(ObjectId()), "serial_number": "unique"},
            # No serial number, so not a duplicate
            {"catalogue_item_id": str(ObjectId())},
        ]
        self.mock_bulk_validate_create(mock_items)

        self.call_bulk_validate_create(mock_items)

        # "duplicate" is never queried, as it is already known to be a duplicate within the data (see the dedicated
        # precedence test below); only "unique" is queried
        assert self.mock_item_repository.is_duplicate_serial_number.call_args_list == [call("unique")]
        self.check_bulk_validate_create_success(
            expected_validate_create_calls=[
                call(0, mock_items[0], is_duplicate_serial_number_in_data=True, is_duplicate_serial_number_in_db=False),
                call(1, mock_items[1], is_duplicate_serial_number_in_data=True, is_duplicate_serial_number_in_db=False),
                call(
                    2, mock_items[2], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=False
                ),
                call(
                    3, mock_items[3], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=False
                ),
            ]
        )

    def test_bulk_validate_create_detects_duplicate_serial_numbers_in_data_ignoring_case_and_whitespace(self):
        """Test bulk validate flags items sharing a serial number as duplicates even when they differ in case or
        leading/trailing whitespace."""

        mock_items = [
            {"catalogue_item_id": str(ObjectId()), "serial_number": "Duplicate"},
            {"catalogue_item_id": str(ObjectId()), "serial_number": "  duplicate  "},
            # Different serial number even once normalised, so not a duplicate
            {"catalogue_item_id": str(ObjectId()), "serial_number": "unique"},
            # Not a string, so should be ignored rather than causing an error
            {"catalogue_item_id": str(ObjectId()), "serial_number": 123},
        ]
        self.mock_bulk_validate_create(mock_items)

        self.call_bulk_validate_create(mock_items)

        # Both differently-cased/spaced variants normalise to "duplicate", which is never queried as it is already
        # known to be a duplicate within the data; only "unique" is queried
        assert self.mock_item_repository.is_duplicate_serial_number.call_args_list == [call("unique")]
        self.check_bulk_validate_create_success(
            expected_validate_create_calls=[
                call(0, mock_items[0], is_duplicate_serial_number_in_data=True, is_duplicate_serial_number_in_db=False),
                call(1, mock_items[1], is_duplicate_serial_number_in_data=True, is_duplicate_serial_number_in_db=False),
                call(
                    2, mock_items[2], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=False
                ),
                call(
                    3, mock_items[3], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=False
                ),
            ]
        )

    def test_bulk_validate_create_detects_duplicate_serial_numbers_in_database(self):
        """Test bulk validate flags an item with a serial number that already exists in the database, checking each
        distinct, non-duplicated serial number against the database independently."""

        mock_items = [
            {"catalogue_item_id": str(ObjectId()), "serial_number": "existing"},
            {"catalogue_item_id": str(ObjectId()), "serial_number": "new"},
        ]
        self.mock_bulk_validate_create(
            mock_items, is_duplicate_serial_number_side_effect=lambda serial_number: serial_number == "existing"
        )

        self.call_bulk_validate_create(mock_items)

        # Order is not guaranteed as the set of serial numbers to check is derived from a set difference
        assert sorted(self.mock_item_repository.is_duplicate_serial_number.call_args_list, key=str) == sorted(
            [call("existing"), call("new")], key=str
        )
        self.check_bulk_validate_create_success(
            expected_validate_create_calls=[
                call(0, mock_items[0], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=True),
                call(
                    1, mock_items[1], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=False
                ),
            ]
        )

    def test_bulk_validate_create_duplicate_in_data_takes_precedence_and_skips_database_check(self):
        """Test bulk validate does not query the database at all for a serial number that is already a duplicate
        within the provided data, as the "duplicate in data" warning always takes precedence over the database one."""

        mock_items = [
            # Duplicate pair - should never be checked against the database
            {"catalogue_item_id": str(ObjectId()), "serial_number": "duplicate"},
            {"catalogue_item_id": str(ObjectId()), "serial_number": "duplicate"},
            # Unique within the data, so still checked against the database
            {"catalogue_item_id": str(ObjectId()), "serial_number": "existing"},
        ]
        self.mock_bulk_validate_create(mock_items, is_duplicate_serial_number_side_effect=lambda _: True)

        self.call_bulk_validate_create(mock_items)

        # "duplicate" is never queried, even though it would also have matched in the database
        assert self.mock_item_repository.is_duplicate_serial_number.call_args_list == [call("existing")]
        self.check_bulk_validate_create_success(
            expected_validate_create_calls=[
                call(0, mock_items[0], is_duplicate_serial_number_in_data=True, is_duplicate_serial_number_in_db=False),
                call(1, mock_items[1], is_duplicate_serial_number_in_data=True, is_duplicate_serial_number_in_db=False),
                call(2, mock_items[2], is_duplicate_serial_number_in_data=False, is_duplicate_serial_number_in_db=True),
            ]
        )

    def test_bulk_validate_create_propagates_database_integrity_error(self):
        """Test bulk validate does not swallow a `DatabaseIntegrityError` raised by `_validate_create`."""

        mock_items = [{"serial_number": "1"}, {"serial_number": "2"}]
        mock_validate_create = MagicMock(
            side_effect=[
                ValidationResultSchema(index=0, warnings=[], errors=[]),
                DatabaseIntegrityError("No catalogue category found with ID 'test-id'"),
            ]
        )

        with patch.object(self.item_service, "_validate_create", mock_validate_create):
            with pytest.raises(DatabaseIntegrityError) as exc:
                self.item_service.bulk_validate_create(mock_items)

        assert str(exc.value) == "No catalogue category found with ID 'test-id'"
