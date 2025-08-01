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
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    ITEM_DATA_ALL_VALUES_NO_PROPERTIES,
    ITEM_DATA_REQUIRED_VALUES_ONLY,
    ITEM_DATA_WITH_ALL_PROPERTIES,
    ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
    SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
    SYSTEM_IN_DATA_NO_PARENT_A,
    USAGE_STATUS_IN_DATA_IN_USE,
    USAGE_STATUS_IN_DATA_NEW,
    USAGE_STATUS_OUT_DATA_NEW,
)
from test.unit.services.conftest import BaseCatalogueServiceDSL, ServiceTestHelpers
from typing import List, Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

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
    ) -> None:
        """
        Checks that a call to `_start_transaction_impacting_number_of_spares` performed the expected function calls.

        :param expected_action_description: Expected `action_description` the function should have been called with.
        :param expected_catalogue_item_id: Expected `catalogue_item_id` the function should have been called with.
        """

        self.mock_setting_repository.get.assert_called_once_with(SparesDefinitionOut)

        # The rest of the calls only occur if there is a spares definition
        if self._expected_spares_definition_out:
            if self._raise_write_conflict_once:
                assert self.mock_start_session_transaction.call_args_list == [
                    call(expected_action_description),
                    call(expected_action_description),
                ]
                self.mock_start_session_transaction.return_value.__enter__.assert_has_calls([call(), call()])

                self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.assert_called_once_with(
                    expected_catalogue_item_id,
                    [system_type.id for system_type in self._expected_spares_definition_out.system_types],
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

                self.mock_item_repository.count_in_catalogue_item_with_system_type_one_of.assert_called_once_with(
                    expected_catalogue_item_id,
                    [system_type.id for system_type in self._expected_spares_definition_out.system_types],
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
    _usage_status_out: Optional[UsageStatusOut]
    _item_post: ItemPostSchema
    _expected_item_in: ItemIn
    _expected_item_out: ItemOut
    _created_item: ItemOut
    _create_exception: pytest.ExceptionInfo

    _expected_merged_properties: List[PropertyPostSchema]

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    # pylint:disable=too-many-locals
    def mock_create(
        self,
        item_data: dict,
        catalogue_item_data: Optional[dict] = None,
        catalogue_category_in_data: Optional[dict] = None,
        usage_status_in_data: Optional[dict] = None,
        stored_spares_definition_out_data: Optional[dict] = None,
        raise_write_conflict_once: bool = False,
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
        :param usage_status_in_data: Dictionary containing the basic usage status data as would be required for a
                                     `UsageStatusIn` database model.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for a `SparesDefinitionOut` database model.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.
        """

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

        self._created_item = self.item_service.create(self._item_post)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `create` method with the appropriate data from a prior call to `mock_create` while
        expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_service.create(self._item_post)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        # This is the get for the catalogue item
        self.mock_catalogue_item_repository.get.assert_called_once_with(self._item_post.catalogue_item_id)

        # This is the get for the catalogue category
        self.mock_catalogue_category_repository.get.assert_called_once_with(
            self._catalogue_item_out.catalogue_category_id
        )

        # This is the get for the usage status
        self.mock_usage_status_repository.get.assert_called_once_with(self._item_post.usage_status_id)

        self.wrapped_utils.process_properties.assert_called_once_with(
            self._catalogue_category_out.properties, self._expected_merged_properties
        )

        self._check_start_transition_impacting_number_of_spares_performed_expected_calls(
            "creating item", str(self._expected_item_in.catalogue_item_id)
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
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_no_properties_provided(self):
        """Test creating an item when none of the properties present in the catalogue item are defined in the item."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_all_properties_provided(self):
        """Test creating an item when all properties present in the catalogue item are defined in the item."""

        self.mock_create(
            ITEM_DATA_WITH_ALL_PROPERTIES,
            catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_spares_definition_defined(self):
        """Test creating an item when there is a spares definition defined."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_spares_definition_defined_write_conflict(self):
        """Test creating an item when there is a spares definition defined and a write conflict occurs."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
            raise_write_conflict_once=True,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_catalogue_item_id(self):
        """Test creating an item with a non-existent catalogue item ID."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=None,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No catalogue item found with ID: {self._item_post.catalogue_item_id}")

    def test_create_with_catalogue_item_with_non_existent_catalogue_category_id(self):
        """Test creating an item with a catalogue item that has a non-existent catalogue category ID."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=None,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create_expecting_error(DatabaseIntegrityError)
        self.check_create_failed_with_exception(
            f"No catalogue category found with ID: {self._catalogue_item_out.catalogue_category_id}"
        )

    def test_create_with_non_existent_usage_status_id(self):
        """Test creating an item with a non-existent usage status ID."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            usage_status_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No usage status found with ID: {self._item_post.usage_status_id}")


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
    _stored_catalogue_item_out: Optional[CatalogueItemOut]
    _stored_catalogue_category_out: Optional[CatalogueCategoryOut]
    _item_patch: ItemPatchSchema
    _expected_item_in: ItemIn
    _expected_item_out: MagicMock
    _updated_item_id: str
    _updated_item: MagicMock
    _update_exception: pytest.ExceptionInfo

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
        stored_catalogue_item_data: Optional[dict] = None,
        stored_catalogue_category_in_data: Optional[dict] = None,
        stored_spares_definition_out_data: Optional[dict] = None,
        new_system_in_data: Optional[dict] = None,
        new_usage_status_in_data: Optional[dict] = None,
        raise_write_conflict_once: bool = False,
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
        :param stored_catalogue_item_data: Either `None` or a dictionary containing the catalogue basic catalogue item
                                 data for the existing stored catalogue item as would be required for a
                                 `CatalogueItemPostSchema` but without any mandatory IDs or property IDs.
        :param stored_catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data
                                                  for the existing stored catalogue category as would be required for a
                                                  `CatalogueCategoryIn` database model.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for `SparesDefinitionOut` database model.
        :param new_system_in_data: Either `None` or a dictionary containing the system data for the new stored system as
                                   would be required for a `SystemIn` database model.
        :param new_usage_status_in_data: Either `None` or a dictionary containing the usage status data for the new
                                         stored usage status as would be required for a `UsageStatus` database model.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.
        """

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

        # Stored system
        self._moving_system = (
            "system_id" in item_update_data
            and self._stored_item is not None
            and self._stored_item.system_id != item_update_data["system_id"]
        )

        if self._moving_system:
            ServiceTestHelpers.mock_get(
                self.mock_system_repository,
                (
                    SystemOut(
                        **{
                            **SystemIn(**new_system_in_data).model_dump(),
                            "_id": item_update_data["system_id"],
                        },
                    )
                    if new_system_in_data
                    else None
                ),
            )

        # Stored usage status
        self._updating_usage_status = "usage_status_id" in item_update_data and (
            stored_item_data and item_update_data["usage_status_id"] != stored_item_data["usage_status_id"]
        )

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

        # Item

        self._updating_properties = "properties" in item_update_data

        # When properties are given need to add any property `id`s and ensure the expected data inserts them as well
        property_post_schemas = []
        expected_properties_in = []
        if self._updating_properties:
            # Catalogue item
            ServiceTestHelpers.mock_get(self.mock_catalogue_item_repository, self._stored_catalogue_item_out)

            # Catalogue category
            self._stored_catalogue_category_out = (
                CatalogueCategoryOut(
                    **stored_catalogue_category_in.model_dump(by_alias=True),
                    id=self._stored_catalogue_item_out.catalogue_category_id,
                )
                if stored_catalogue_category_in_data
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
        self._updated_item = self.item_service.update(item_id, self._item_patch)

    def call_update_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `update` method with the appropriate data from a prior call to
        `mock_update` while expecting an error to be raised.

        :param item_id: ID of the item to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.item_service.update(item_id, self._item_patch)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        self.mock_item_repository.get.assert_called_once_with(self._updated_item_id)

        if self._moving_system:
            self.mock_system_repository.get.assert_called_once_with(self._item_patch.system_id)

        if self._updating_usage_status:
            self.mock_usage_status_repository.get.assert_called_once_with(self._item_patch.usage_status_id)

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

        if self._moving_system:
            self._check_start_transition_impacting_number_of_spares_performed_expected_calls(
                "updating item", self._stored_item.catalogue_item_id
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


class TestUpdate(UpdateDSL):
    """Tests for updating an item."""

    def test_update_all_fields_except_ids_or_properties(self):
        """Test updating all fields of an item except any of its `_id` fields or properties."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_ALL_VALUES_NO_PROPERTIES,
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_properties_with_all(self):
        """Test updating an item's `properties` while populating all available properties."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_ALL_VALUES_NO_PROPERTIES,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            # Strictly speaking we wouldn't allow this in the first place - the stored data is missing a mandatory
            # property but it is irrelevant for this test and saves creating a new version
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
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
            item_update_data=ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            # Strictly speaking we wouldn't allow this in the first place - the stored data is missing a mandatory
            # property but it is irrelevant for this test and saves creating a new version
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
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
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
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
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_id_with_spares_definition_defined(self):
        """Test updating an item's `system_id` when there is a spares definition defined."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId())},
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_system_id_with_spares_definition_defined_write_conflict(self):
        """Test updating an item's `system_id` when there is a spares definition defined and a write conflict occurs."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"system_id": str(ObjectId())},
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=SYSTEM_IN_DATA_NO_PARENT_A,
            stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE,
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
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_system_in_data=None,
        )
        self.call_update_expecting_error(item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No system found with ID: {system_id}")

    def test_update_usage_status_id(self):
        """Test updating an item's `usage_status_id`."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"usage_status_id": USAGE_STATUS_OUT_DATA_NEW["id"]},
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_usage_status_in_data=USAGE_STATUS_IN_DATA_NEW,
        )
        self.call_update(item_id)
        self.check_update_success()

    def test_update_with_non_existent_usage_status_id(self):
        """Test updating an item's `usage_status_id` to a non-existent usage status."""

        item_id = str(ObjectId())
        usage_status_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data={"usage_status_id": usage_status_id},
            stored_item_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
            new_usage_status_in_data=None,
        )
        self.call_update_expecting_error(item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No usage status found with ID: {usage_status_id}")

    def test_update_with_non_existent_id(self):
        """Test updating an item with a non-existent ID."""

        item_id = str(ObjectId())

        self.mock_update(
            item_id,
            item_update_data=ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_item_data=None,
            stored_usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_update_expecting_error(item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No item found with ID: {item_id}")


class DeleteDSL(ItemServiceDSL):
    """Base class for `delete` tests."""

    _stored_item: Optional[ItemOut]
    _delete_item_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self,
        stored_item_data: Optional[dict],
        stored_spares_definition_out_data: Optional[dict] = None,
        raise_write_conflict_once: bool = False,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `delete` service method.

        :param stored_item_data: Either `None` or a dictionary containing the basic item data for the existing stored
                                 item as would be required for an `ItemPostSchema` but without any mandatory IDs or
                                 property IDs.
        :param stored_spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as
                                                  would be required for a `SparesDefinitionOut` database model.
        :param raise_write_conflict_once: Whether to raise a write conflict during the number of spares update to
                                          test the retrying functionality.
        """

        self._stored_item = (
            ItemOut(
                **ItemIn(
                    **stored_item_data,
                    catalogue_item_id=str(ObjectId()),
                    system_id=str(ObjectId()),
                    # Need a value here but doesn't matter if it matches the usage status or not
                    usage_status="test",
                ).model_dump(),
                id=str(ObjectId()),
            )
            if stored_item_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_item_repository, self._stored_item)

        self._mock_start_transaction_impacting_number_of_spares(
            stored_spares_definition_out_data, raise_write_conflict_once
        )

    def call_delete(self, item_id: str) -> None:
        """
        Calls the `ItemService` `delete` method.

        :param item_id: ID of the item to be deleted.
        """

        self._delete_item_id = item_id
        self.item_service.delete(item_id)

    def call_delete_expecting_error(self, item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `ItemService` `delete` method.

        :param item_id: ID of the item to be deleted.
        :param error_type: Expected exception to be raised.
        """

        self._delete_item_id = item_id
        with pytest.raises(error_type) as exc:
            self.item_service.delete(item_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.mock_item_repository.get.assert_called_once_with(self._delete_item_id)
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

        self.mock_delete(ITEM_DATA_REQUIRED_VALUES_ONLY)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_spares_definition_defined(self):
        """Test deleting an item when there is a spares definition defined."""

        self.mock_delete(
            ITEM_DATA_REQUIRED_VALUES_ONLY, stored_spares_definition_out_data=SETTING_SPARES_DEFINITION_OUT_DATA_STORAGE
        )
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_spares_definition_defined_write_conflict(self):
        """Test deleting an item when there is a spares definition defined and a write conflict occurs."""

        self.mock_delete(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
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
        self.check_delete_failed_with_exception(f"No item found with ID: {item_id}")
