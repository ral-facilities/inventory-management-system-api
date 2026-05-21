"""
Unit tests for the `CatalogueCategoryService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code
# pylint:disable=too-many-arguments
# pylint:disable=too-many-positional-arguments

from copy import deepcopy
from test.mock_data import (
    BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
    BASE_CATALOGUE_CATEGORY_OUT_DATA_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_OUT_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    MANUFACTURER_IN_DATA_A,
    MANUFACTURER_OUT_DATA_A,
    PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42,
)
from test.unit.services.conftest import BaseCatalogueServiceDSL, ServiceTestHelpers
from typing import Optional
from unittest.mock import ANY, MagicMock, Mock, call, patch

import pytest
from bson import ObjectId
from pydantic import ValidationError

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidActionError,
    MissingRecordError,
    NonLeafCatalogueCategoryError,
    ReplacementForObsoleteCatalogueItemError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.schemas.catalogue_item import (
    CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS,
    CatalogueItemPatchSchema,
    CatalogueItemPostSchema,
    PropertyPostSchema,
)
from inventory_management_system_api.schemas.validation import (
    BulkValidationResultSchema,
    ValidationErrorSchema,
    ValidationResultSchema,
)
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.catalogue_item import CatalogueItemService


class CatalogueItemServiceDSL(BaseCatalogueServiceDSL):
    """Base class for `CatalogueItemService` unit tests."""

    wrapped_utils: Mock
    mock_catalogue_item_repository: Mock
    mock_catalogue_category_repository: Mock
    mock_manufacturer_repository: Mock
    mock_unit_repository: Mock
    mock_setting_repository: Mock
    catalogue_item_service: CatalogueItemService

    mock_session = MagicMock()

    @pytest.fixture(autouse=True)
    def setup(
        self,
        catalogue_item_repository_mock,
        catalogue_category_repository_mock,
        manufacturer_repository_mock,
        unit_repository_mock,
        setting_repository_mock,
        catalogue_item_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""

        self.mock_catalogue_item_repository = catalogue_item_repository_mock
        self.mock_catalogue_category_repository = catalogue_category_repository_mock
        self.mock_manufacturer_repository = manufacturer_repository_mock
        self.mock_unit_repository = unit_repository_mock
        self.mock_setting_repository = setting_repository_mock
        self.catalogue_item_service = catalogue_item_service

        with patch("inventory_management_system_api.services.catalogue_item.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield


class CreateDSL(CatalogueItemServiceDSL):
    """Base class for `create` tests."""

    _catalogue_category_out: Optional[CatalogueCategoryOut]
    _catalogue_item_post: CatalogueItemPostSchema
    _expected_catalogue_item_in: CatalogueItemIn
    _expected_catalogue_item_out: CatalogueItemOut
    _created_catalogue_item: CatalogueItemOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        catalogue_item_data: dict,
        catalogue_category_in_data: Optional[dict] = None,
        manufacturer_in_data: Optional[dict] = None,
        obsolete_replacement_catalogue_item_data: Optional[dict] = None,
        spares_definition_out_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required for a
                                    `CatalogueItemPostSchema` but with any mandatory IDs missing as they will be added
                                    automatically.
        :param catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data as would
                                           be required for a `CatalogueCategoryIn` database model.
        :param manufacturer_in_data: Either `None` or a dictionary containing the manufacturer data as would be required
                                     for a `ManufacturerIn` database model.
        :param obsolete_replacement_catalogue_item_data: Dictionary containing the basic catalogue item data for the
                                     obsolete replacement as would be required for a `CatalogueItemPostSchema` but with
                                     any `unit_id`'s replaced by the `unit` value in its properties as the IDs will be
                                     added automatically.
        :param spares_definition_out_data: Either `None` or a dictionary containing the spares definition data as would
                                           be required for a `SparesDefinitionOut` database model.
        """

        # Generate mandatory IDs to be inserted where needed
        catalogue_category_id = str(ObjectId())
        manufacturer_id = str(ObjectId())

        ids_to_insert = {"catalogue_category_id": catalogue_category_id, "manufacturer_id": manufacturer_id}

        # Catalogue category
        catalogue_category_in = None
        if catalogue_category_in_data:
            catalogue_category_in = CatalogueCategoryIn(**catalogue_category_in_data)

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

        # Manufacturer
        ServiceTestHelpers.mock_get(
            self.mock_manufacturer_repository,
            (
                ManufacturerOut(
                    **{
                        **ManufacturerIn(**manufacturer_in_data).model_dump(),
                        "_id": manufacturer_id,
                    },
                )
                if manufacturer_in_data
                else None
            ),
        )

        # Obsolete replacement catalogue item (Use the same mandatory IDs as the item for simplicity)
        ServiceTestHelpers.mock_get(
            self.mock_catalogue_item_repository,
            (
                CatalogueItemOut(
                    **{
                        **CatalogueItemIn(
                            **obsolete_replacement_catalogue_item_data, **ids_to_insert, number_of_spares=None
                        ).model_dump(),
                        "_id": catalogue_item_data["obsolete_replacement_catalogue_item_id"],
                    },
                )
                if obsolete_replacement_catalogue_item_data
                else None
            ),
        )

        # When properties are given need to add any property `id`s and ensure the expected data inserts them as well
        property_post_schemas = []
        expected_properties_in = []
        if "properties" in catalogue_item_data and catalogue_item_data["properties"]:
            expected_properties_in, property_post_schemas = self.construct_properties_in_and_post_with_ids(
                catalogue_category_in.properties, catalogue_item_data["properties"]
            )
            expected_properties_in = utils.process_properties(
                self._catalogue_category_out.properties, property_post_schemas
            )

        spares_definition_out = (
            SparesDefinitionOut(**spares_definition_out_data) if spares_definition_out_data else None
        )
        ServiceTestHelpers.mock_get(self.mock_setting_repository, spares_definition_out)

        self._catalogue_item_post = CatalogueItemPostSchema(
            **{**catalogue_item_data, **ids_to_insert, "properties": property_post_schemas}
        )

        self._expected_catalogue_item_in = CatalogueItemIn(
            **{
                **catalogue_item_data,
                **ids_to_insert,
                "properties": expected_properties_in,
            },
            number_of_spares=0 if spares_definition_out else None,
        )
        self._expected_catalogue_item_out = CatalogueItemOut(
            **self._expected_catalogue_item_in.model_dump(), id=ObjectId()
        )

        ServiceTestHelpers.mock_create(self.mock_catalogue_item_repository, self._expected_catalogue_item_out)

    def call_create(self) -> None:
        """Calls the `CatalogueItemService` `create` method with the appropriate data from a prior call to
        `mock_create`."""

        self._created_catalogue_item = self.catalogue_item_service.create(
            self._catalogue_item_post, session=self.mock_session
        )

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemService` `create` method with the appropriate data from a prior call to
        `mock_create` while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_item_service.create(self._catalogue_item_post)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        # This is the get for the catalogue category
        self.mock_catalogue_category_repository.get.assert_called_once_with(
            self._catalogue_item_post.catalogue_category_id
        )

        # This is the get for the manufacturer
        self.mock_manufacturer_repository.get.assert_called_once_with(self._catalogue_item_post.manufacturer_id)

        # This is the get for the obsolete replacement catalogue item
        if self._catalogue_item_post.obsolete_replacement_catalogue_item_id:
            self.mock_catalogue_item_repository.get.assert_called_once_with(
                self._catalogue_item_post.obsolete_replacement_catalogue_item_id
            )

        self.wrapped_utils.process_properties.assert_called_once_with(
            self._catalogue_category_out.properties, self._catalogue_item_post.properties
        )

        self.mock_catalogue_item_repository.create.assert_called_once_with(
            self._expected_catalogue_item_in, session=self.mock_session
        )

        assert self._created_catalogue_item == self._expected_catalogue_item_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_item_repository.create.assert_not_called()
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue item."""

    def test_create_without_properties(self):
        """Test creating a catalogue item without any properties in the catalogue category or catalogue item."""

        self.mock_create(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_all_properties(self):
        """Test creating a catalogue item when all properties present in the catalogue category are defined in the
        catalogue item."""

        self.mock_create(
            CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_catalogue_category_id(self):
        """Test creating a catalogue item with a non-existent catalogue category ID."""

        self.mock_create(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=None,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No catalogue category found with ID '{self._catalogue_item_post.catalogue_category_id}'"
        )

    def test_create_with_non_leaf_catalogue_category(self):
        """Test creating a catalogue item with a non-leaf catalogue category."""

        self.mock_create(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create_expecting_error(NonLeafCatalogueCategoryError)
        self.check_create_failed_with_exception("Cannot add catalogue item to a non-leaf catalogue category")

    def test_create_with_non_existent_manufacturer_id(self):
        """Test creating a catalogue item with a non-existent manufacturer ID."""

        self.mock_create(
            CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No manufacturer found with ID '{self._catalogue_item_post.manufacturer_id}'"
        )

    def test_create_with_obsolete_replacement_catalogue_item(self):
        """Test creating a catalogue item with an obsolete replacement catalogue item."""

        obsolete_replacement_catalogue_item_id = str(ObjectId())
        self.mock_create(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            },
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
            obsolete_replacement_catalogue_item_data=CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_obsolete_replacement_catalogue_item_id(self):
        """Test creating a catalogue item with a non-existent obsolete replacement catalogue item ID."""

        obsolete_replacement_catalogue_item_id = str(ObjectId())
        self.mock_create(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            },
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
            obsolete_replacement_catalogue_item_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No catalogue item found with ID '{obsolete_replacement_catalogue_item_id}'"
        )


class GetDSL(CatalogueItemServiceDSL):
    """Base class for `get` tests."""

    _obtained_catalogue_item_id: str
    _expected_catalogue_item: MagicMock
    _obtained_catalogue_item: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_catalogue_item = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_catalogue_item_repository, self._expected_catalogue_item)

    def call_get(self, catalogue_item_id: str) -> None:
        """
        Calls the `CatalogueItemService` `get` method.

        :param catalogue_item_id: ID of the catalogue item to be obtained.
        """

        self._obtained_catalogue_item_id = catalogue_item_id
        self._obtained_catalogue_item = self.catalogue_item_service.get(catalogue_item_id)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.mock_catalogue_item_repository.get.assert_called_once_with(self._obtained_catalogue_item_id)
        assert self._obtained_catalogue_item == self._expected_catalogue_item


class TestGet(GetDSL):
    """Tests for getting a catalogue item."""

    def test_get(self):
        """Test getting a catalogue item."""

        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class ListDSL(CatalogueItemServiceDSL):
    """Base class for `list` tests"""

    _catalogue_category_id_filter: Optional[str]
    _expected_catalogue_items: MagicMock
    _obtained_catalogue_items: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_catalogue_items = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_catalogue_item_repository, self._expected_catalogue_items)

    def call_list(self, catalogue_category_id: Optional[str]) -> None:
        """
        Calls the `CatalogueItemService` `list` method.

        :param catalogue_category_id: ID of the catalogue category to query by, or `None`.
        """

        self._catalogue_category_id_filter = catalogue_category_id
        self._obtained_catalogue_items = self.catalogue_item_service.list(catalogue_category_id)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_catalogue_item_repository.list.assert_called_once_with(self._catalogue_category_id_filter)

        assert self._obtained_catalogue_items == self._expected_catalogue_items


class TestList(ListDSL):
    """Tests for listing catalogue items."""

    def test_list(self):
        """Test listing catalogue items."""

        self.mock_list()
        self.call_list(str(ObjectId()))
        self.check_list_success()


# pylint:disable=too-many-instance-attributes
class UpdateDSL(CatalogueItemServiceDSL):
    """Base class for `update` tests."""

    _stored_catalogue_item: Optional[CatalogueItemOut]
    _stored_catalogue_category_in: Optional[CatalogueCategoryIn]
    _stored_catalogue_category_out: Optional[CatalogueCategoryOut]
    _new_catalogue_category_in: Optional[CatalogueCategoryIn]
    _new_catalogue_category_out: Optional[CatalogueCategoryOut]
    _catalogue_item_patch: CatalogueItemPatchSchema
    _expected_catalogue_item_in: CatalogueItemIn
    _expected_catalogue_item_out: MagicMock
    _updated_catalogue_item_id: str
    _updated_catalogue_item: MagicMock
    _update_exception: pytest.ExceptionInfo

    _expect_child_check: bool
    _moving_catalogue_item: bool
    _updating_manufacturer: bool
    _updating_obsolete_replacement_catalogue_item: bool
    _updating_properties: bool

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def mock_update(
        self,
        catalogue_item_id: str,
        catalogue_item_update_data: dict,
        stored_catalogue_item_data: Optional[dict],
        stored_catalogue_category_in_data: Optional[dict] = None,
        new_catalogue_category_in_data: Optional[dict] = None,
        new_manufacturer_in_data: Optional[dict] = None,
        new_obsolete_replacement_catalogue_item_data: Optional[dict] = None,
        has_child_elements: bool = False,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `update` service method.

        :param catalogue_item_id: ID of the catalogue item that will be obtained.
        :param catalogue_item_update_data: Dictionary containing the basic patch data as would be required for a
                                          `CatalogueItemPatchSchema` but without any mandatory IDs or property IDs.
        :param stored_catalogue_item_data: Either `None` or a dictionary containing the catalogue basic catalogue item
                                           data for the existing stored catalogue item as would be required for a
                                           `CatalogueItemPostSchema` but without any mandatory IDs or property IDs.
        :param stored_catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data
                                                  for the existing stored catalogue category as would be required for a
                                                  `CatalogueCategoryIn` database model.
        :param new_catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data for
                                               the new stored catalogue category as would be required for a
                                               `CatalogueCategoryIn` database model.
        :param new_manufacturer_in_data: Either `None` or a dictionary containing the manufacturer data for the new
                                         stored manufacturer as would be required for a `ManufacturerIn` database model.
        :param new_obsolete_replacement_catalogue_item_data: Either `None` or a dictionary containing the basic
                                         catalogue item data for the new stored obsolete replacement catalogue item as
                                         would be required for a `CatalogueItemPostSchema` but without any mandatory IDs
                                         or property IDs.
        :param has_child_elements: Boolean of whether the catalogue item being updated has child elements or not
        """

        # Add property ids to the stored catalogue item if needed
        self._stored_catalogue_category_in = (
            CatalogueCategoryIn(**stored_catalogue_category_in_data) if stored_catalogue_category_in_data else None
        )
        expected_stored_properties_in = []
        if (
            self._stored_catalogue_category_in
            and "properties" in stored_catalogue_item_data
            and stored_catalogue_item_data["properties"]
        ):
            expected_stored_properties_in, _ = self.construct_properties_in_and_post_with_ids(
                self._stored_catalogue_category_in.properties, stored_catalogue_item_data["properties"]
            )

        # Generate mandatory IDs to be inserted where needed
        stored_ids_to_insert = {"catalogue_category_id": str(ObjectId()), "manufacturer_id": str(ObjectId())}

        # Stored catalogue item
        self._stored_catalogue_item = (
            CatalogueItemOut(
                **CatalogueItemIn(
                    **{**stored_catalogue_item_data, "properties": expected_stored_properties_in},
                    **stored_ids_to_insert,
                    number_of_spares=None,
                ).model_dump(),
                id=CustomObjectId(catalogue_item_id),
            )
            if stored_catalogue_item_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_catalogue_item_repository, self._stored_catalogue_item)

        self._stored_catalogue_category_out = (
            CatalogueCategoryOut(
                **self._stored_catalogue_category_in.model_dump(by_alias=True),
                id=self._stored_catalogue_item.catalogue_category_id,
            )
            if stored_catalogue_category_in_data
            else None
        )

        # Need to mock has_child_elements only if the check is required
        self._expect_child_check = any(
            key in catalogue_item_update_data for key in CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS
        )
        if self._expect_child_check:
            self.mock_catalogue_item_repository.has_child_elements.return_value = has_child_elements

        # When moving i.e. changing the catalogue category id, the data for the new catalogue category needs to be
        # mocked
        self._moving_catalogue_item = (
            "catalogue_category_id" in catalogue_item_update_data and stored_catalogue_item_data is not None
        )

        self._updating_properties = "properties" in catalogue_item_update_data

        if self._moving_catalogue_item and catalogue_item_update_data["catalogue_category_id"]:
            self._new_catalogue_category_in = (
                CatalogueCategoryIn(**new_catalogue_category_in_data) if new_catalogue_category_in_data else None
            )
            self._new_catalogue_category_out = (
                CatalogueCategoryOut(
                    **{
                        **self._new_catalogue_category_in.model_dump(by_alias=True),
                        "_id": catalogue_item_update_data["catalogue_category_id"],
                    }
                )
                if new_catalogue_category_in_data
                else None
            )

            ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._new_catalogue_category_out)

            # Existing category is needed only if the new properties are not given
            if not self._updating_properties:
                ServiceTestHelpers.mock_get(
                    self.mock_catalogue_category_repository,
                    (
                        CatalogueCategoryOut(
                            **{
                                **self._stored_catalogue_category_in.model_dump(by_alias=True),
                                "_id": self._stored_catalogue_item.catalogue_category_id,
                            }
                        )
                        # Should not be None here, if properties is not given, then expect test to assign this too
                        if self._stored_catalogue_category_in
                        else None
                    ),
                )

        self._updating_manufacturer = (
            "manufacturer_id" in catalogue_item_update_data
            and catalogue_item_update_data["manufacturer_id"] != self._stored_catalogue_item.manufacturer_id
        )
        if self._updating_manufacturer:
            ServiceTestHelpers.mock_get(
                self.mock_manufacturer_repository,
                (
                    ManufacturerOut(
                        **{
                            **ManufacturerIn(**new_manufacturer_in_data).model_dump(),
                            "_id": catalogue_item_update_data["manufacturer_id"],
                        },
                    )
                    if new_manufacturer_in_data
                    else None
                ),
            )

        self._updating_obsolete_replacement_catalogue_item = (
            "obsolete_replacement_catalogue_item_id" in catalogue_item_update_data
            and catalogue_item_update_data["obsolete_replacement_catalogue_item_id"]
            != self._stored_catalogue_item.obsolete_replacement_catalogue_item_id
        )
        if self._updating_obsolete_replacement_catalogue_item:
            # Obsolete replacement catalogue item (Use the same mandatory IDs as the item for simplicity)
            ServiceTestHelpers.mock_get(
                self.mock_catalogue_item_repository,
                (
                    CatalogueItemOut(
                        **{
                            **CatalogueItemIn(
                                **new_obsolete_replacement_catalogue_item_data,
                                catalogue_category_id=str(ObjectId()),
                                manufacturer_id=str(ObjectId()),
                                number_of_spares=None,
                            ).model_dump(),
                            "_id": catalogue_item_update_data["obsolete_replacement_catalogue_item_id"],
                        },
                    )
                    if new_obsolete_replacement_catalogue_item_data
                    else None
                ),
            )

        # When properties are given need to add any property `id`s and ensure the expected data inserts them as well
        expected_properties_in = []
        if self._updating_properties:

            # When not moving to a different catalogue category the existing catalogue category will still need to be
            # mocked
            if not self._moving_catalogue_item:
                ServiceTestHelpers.mock_get(
                    self.mock_catalogue_category_repository, self._stored_catalogue_category_out
                )

            expected_properties_in, property_post_schemas = self.construct_properties_in_and_post_with_ids(
                (
                    self._new_catalogue_category_in.properties
                    if self._moving_catalogue_item
                    else self._stored_catalogue_category_in.properties
                ),
                catalogue_item_update_data["properties"],
            )
            expected_properties_in = utils.process_properties(
                (
                    self._new_catalogue_category_out.properties
                    if self._moving_catalogue_item
                    else self._stored_catalogue_category_out.properties
                ),
                property_post_schemas,
            )

            catalogue_item_update_data["properties"] = property_post_schemas

        # Updated catalogue item
        self._expected_catalogue_item_out = MagicMock()
        ServiceTestHelpers.mock_update(self.mock_catalogue_item_repository, self._expected_catalogue_item_out)

        # Patch schema
        self._catalogue_item_patch = CatalogueItemPatchSchema(**catalogue_item_update_data)

        # Construct the expected input for the repository
        merged_catalogue_item_data = {
            **(stored_catalogue_item_data or {}),
            **stored_ids_to_insert,
            **catalogue_item_update_data,
        }
        self._expected_catalogue_item_in = CatalogueItemIn(
            **{**merged_catalogue_item_data, "properties": expected_properties_in, "number_of_spares": None}
        )

    def call_update(self, catalogue_item_id: str) -> None:
        """
        Calls the `CatalogueItemService` `update` method with the appropriate data from a prior call to
        `mock_update`.

        :param catalogue_item_id: ID of the catalogue item to be updated.
        """

        self._updated_catalogue_item_id = catalogue_item_id
        self._updated_catalogue_item = self.catalogue_item_service.update(catalogue_item_id, self._catalogue_item_patch)

    def call_update_expecting_error(self, catalogue_item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemService` `update` method with the appropriate data from a prior call to
        `mock_update` while expecting an error to be raised.

        :param catalogue_item_id: ID of the catalogue item to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_item_service.update(catalogue_item_id, self._catalogue_item_patch)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        # Obtain a list of expected catalogue item get calls
        expected_catalogue_item_get_calls = []

        # Ensure obtained old catalogue item
        expected_catalogue_item_get_calls.append(call(self._updated_catalogue_item_id))

        # Ensure checking children if needed
        if self._expect_child_check:
            self.mock_catalogue_item_repository.has_child_elements.assert_called_once_with(
                self._updated_catalogue_item_id
            )

        # Ensure obtained new catalogue category if moving
        expected_catalogue_category_get_calls = []
        if self._moving_catalogue_item and self._catalogue_item_patch.catalogue_category_id:
            expected_catalogue_category_get_calls.append(call(self._catalogue_item_patch.catalogue_category_id))

            # Expect additional call from existing catalogue category to compare properties if new properties aren't
            # given
            if self._catalogue_item_patch.properties is None:
                expected_catalogue_category_get_calls.append(call(self._stored_catalogue_item.catalogue_category_id))

            self.mock_catalogue_category_repository.get.assert_has_calls(expected_catalogue_category_get_calls)

        # Ensure obtained new manufacturer if needed
        if self._updating_manufacturer and self._catalogue_item_patch.manufacturer_id:
            self.mock_manufacturer_repository.get.assert_called_once_with(self._catalogue_item_patch.manufacturer_id)

        self.mock_catalogue_item_repository.get.assert_has_calls(expected_catalogue_item_get_calls)

        if self._updating_properties:
            if self._moving_catalogue_item:
                expected_catalogue_category_get_calls.append(call(self._stored_catalogue_item.catalogue_category_id))

            self.wrapped_utils.process_properties.assert_called_once_with(
                (
                    self._new_catalogue_category_out.properties
                    if self._moving_catalogue_item
                    else self._stored_catalogue_category_out.properties
                ),
                self._catalogue_item_patch.properties,
            )
        else:
            self.wrapped_utils.process_properties.assert_not_called()

        assert self._updated_catalogue_item == self._expected_catalogue_item_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_item_repository.update.assert_not_called()

        assert str(self._update_exception.value) == message


# pylint: disable=too-many-public-methods
class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue item."""

    def test_update_all_fields_except_ids_or_properties_with_no_children(self):
        """Test updating all fields of a catalogue item except any of its `_id` fields or properties when it has no
        children."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data=CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_all_fields_except_ids_or_properties_with_children(self):
        """Test updating all fields of a catalogue item except any of its `_id` fields or properties it has children."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data=CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            has_child_elements=True,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_catalogue_category_id_no_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` when no properties are involved."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            new_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_catalogue_category_id_with_same_defined_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` when both the old and new catalogue category has
        identical properties.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_catalogue_category_id_and_properties_with_same_defined_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` and `properties` when both the old and new
        catalogue category has identical properties.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={
                "catalogue_category_id": str(ObjectId()),
                "properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"],
            },
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_catalogue_category_id_with_same_defined_properties_different_order(self):
        """Test updating the catalogue item's `catalogue_category_id` when both the old and new catalogue category has
        identical properties but in a different order.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
                "properties": CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM["properties"][::-1],
            },
        )
        self.call_update_expecting_error(catalogue_item_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot move catalogue item to a category with different properties "
            "without specifying the new properties"
        )

    def test_update_catalogue_category_id_and_properties_with_same_defined_properties_different_order(self):
        """Test updating the catalogue item's `catalogue_category_id` and `properties` when both the old and new
        catalogue category has identical properties but in a different order.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={
                "catalogue_category_id": str(ObjectId()),
                "properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"][::-1],
            },
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
                "properties": CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM["properties"][::-1],
            },
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_catalogue_category_id_with_different_defined_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` when the old and new catalogue category have
        different properties.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            },
        )
        self.call_update_expecting_error(catalogue_item_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot move catalogue item to a category with different properties "
            "without specifying the new properties"
        )

    def test_update_catalogue_category_id_and_properties_with_different_defined_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` and `properties` when the old and new catalogue
        category have different properties.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={
                "catalogue_category_id": str(ObjectId()),
                "properties": [PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42],
            },
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
                "properties": [CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT],
            },
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_catalogue_category_id_while_removing_all_defined_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` when the old catalogue category and item has
        properties but the new one does not.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_update_expecting_error(catalogue_item_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot move catalogue item to a category with different properties "
            "without specifying the new properties"
        )

    def test_update_catalogue_category_id_and_properties_while_removing_all_defined_properties(self):
        """Test updating the catalogue item's `catalogue_category_id` and `properties` when the old catalogue category
        and item has properties but the new one does not.
        """

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": str(ObjectId()), "properties": []},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            new_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_with_non_leaf_catalogue_category_id(self):
        """Test updating the catalogue item's `catalogue_category_id` to a leaf catalogue category."""

        catalogue_item_id = str(ObjectId())
        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": catalogue_category_id},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            new_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_update_expecting_error(catalogue_item_id, NonLeafCatalogueCategoryError)
        self.check_update_failed_with_exception("Cannot add catalogue item to a non-leaf catalogue category")

    def test_update_with_non_existent_catalogue_category_id(self):
        """Test updating the catalogue item's `catalogue_category_id` to a non-existent catalogue category."""

        catalogue_item_id = str(ObjectId())
        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"catalogue_category_id": catalogue_category_id},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
        )
        self.call_update_expecting_error(catalogue_item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No catalogue category found with ID '{catalogue_category_id}'")

    def test_update_manufacturer_id_with_no_children(self):
        """Test updating the catalogue item's `manufacturer_id` when it has no children."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"manufacturer_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            new_manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_manufacturer_id_with_children(self):
        """Test updating the catalogue item's `manufacturer_id` when it has children."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"manufacturer_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            new_manufacturer_in_data=MANUFACTURER_IN_DATA_A,
            has_child_elements=True,
        )
        self.call_update_expecting_error(catalogue_item_id, ChildElementsExistError)
        self.check_update_failed_with_exception(
            f"Catalogue item with ID '{catalogue_item_id}' has child elements and cannot be updated"
        )

    def test_update_properties_with_no_children(self):
        """Test updating the catalogue item's `properties` when it has no children."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"]},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_properties_with_children(self):
        """Test updating the catalogue item's `properties` when it has children."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"properties": CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["properties"]},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            has_child_elements=True,
        )
        self.call_update_expecting_error(catalogue_item_id, ChildElementsExistError)
        self.check_update_failed_with_exception(
            f"Catalogue item with ID '{catalogue_item_id}' has child elements and cannot be updated"
        )

    def test_update_with_non_existent_manufacturer_id(self):
        """Test updating the catalogue item's `manufacturer_id` to a non-existent manufacturer."""

        catalogue_item_id = str(ObjectId())
        manufacturer_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"manufacturer_id": manufacturer_id},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            new_manufacturer_in_data=None,
        )
        self.call_update_expecting_error(catalogue_item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No manufacturer found with ID '{manufacturer_id}'")

    def test_update_obsolete_replacement_catalogue_item_id(self):
        """Test updating the catalogue item's `obsolete_replacement_catalogue_item_id`."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={"obsolete_replacement_catalogue_item_id": str(ObjectId())},
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            new_obsolete_replacement_catalogue_item_data=CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
        )
        self.call_update(catalogue_item_id)
        self.check_update_success()

    def test_update_with_non_existent_obsolete_replacement_catalogue_item_id(self):
        """Test updating the catalogue item's `obsolete_replacement_catalogue_item_id` to a non-existent catalogue
        item."""

        catalogue_item_id = str(ObjectId())
        obsolete_replacement_catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data={
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id
            },
            stored_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            new_obsolete_replacement_catalogue_item_data=None,
        )
        self.call_update_expecting_error(catalogue_item_id, MissingRecordError)
        self.check_update_failed_with_exception(
            f"No catalogue item found with ID '{obsolete_replacement_catalogue_item_id}'"
        )

    def test_update_with_non_existent_id(self):
        """Test updating a catalogue item with a non-existent ID."""

        catalogue_item_id = str(ObjectId())

        self.mock_update(
            catalogue_item_id,
            catalogue_item_update_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
            stored_catalogue_item_data=None,
        )
        self.call_update_expecting_error(catalogue_item_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No catalogue item found with ID '{catalogue_item_id}'")


class DeleteDSL(CatalogueItemServiceDSL):
    """Base class for `delete` tests."""

    _delete_catalogue_item_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self, has_child_elements: Optional[bool] = False, is_replacement_for: Optional[bool] = False
    ) -> None:
        """
        Mocks repo methods appropriately to test the `delete` service method.

        :param has_child_elements: Whether the catalogue item being deleted has child elements or not.
        :param is_replacement_for: Whether the catalogue item being deleted is the replacement for another catalogue
                                   item or not.
        """

        self.mock_catalogue_item_repository.has_child_elements.return_value = has_child_elements
        self.mock_catalogue_item_repository.is_replacement_for.return_value = is_replacement_for

    def call_delete(self, catalogue_item_id: str) -> None:
        """
        Calls the `CatalogueItemService` `delete` method.

        :param catalogue_item_id: ID of the catalogue item to be deleted.
        """

        self._delete_catalogue_item_id = catalogue_item_id
        self.catalogue_item_service.delete(catalogue_item_id)

    def call_delete_expecting_error(self, catalogue_item_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueItemService` `delete` method while expecting an error to be raised.

        :param catalogue_item_id: ID of the catalogue item to be deleted.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_item_service.delete(catalogue_item_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.mock_catalogue_item_repository.delete.assert_called_once_with(self._delete_catalogue_item_id)

    def check_delete_failed_with_exception(self, message: str) -> None:
        """
        Check that a prior call to `call_delete_expecting_error` worked as expected, raising an exception with the
        correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_item_repository.delete.assert_not_called()
        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue item."""

    def test_delete(self):
        """Test deleting a catalogue item."""

        self.mock_delete(has_child_elements=False)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_child_elements(self):
        """Test deleting a catalogue item when it has child elements."""

        catalogue_item_id = str(ObjectId())

        self.mock_delete(has_child_elements=True)
        self.call_delete_expecting_error(catalogue_item_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(
            f"Catalogue item with ID '{catalogue_item_id}' has child elements and cannot be deleted"
        )

    def test_delete_when_is_replacement_for(self):
        """Test deleting a catalogue item when it is the replacement for at least one obsolete catalogue item."""

        catalogue_item_id = str(ObjectId())

        self.mock_delete(is_replacement_for=True)
        self.call_delete_expecting_error(catalogue_item_id, ReplacementForObsoleteCatalogueItemError)
        self.check_delete_failed_with_exception(
            f"Catalogue item with ID '{catalogue_item_id}' is the replacement for at least one obsolete catalogue item "
            "and cannot be deleted"
        )


class ValidateDSL(CatalogueItemServiceDSL):
    """Base class for `validate` tests."""

    _catalogue_category_out: Optional[CatalogueCategoryOut]
    _catalogue_item_data: dict
    _validate_create_result: ValidationResultSchema

    def mock_validate_create(
        self,
        catalogue_item_data: dict,
        catalogue_category_out_data: Optional[dict] = None,
        manufacturer_out_data: Optional[dict] = None,
        obsolete_replacement_catalogue_item_out_data: Optional[dict] = None,
        has_duplicate_name: bool = False,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `validate_create` service method.

        :param catalogue_item_data: Dictionary containing the catalogue item data to validate.
        :param catalogue_category_out_data: Either `None` or a dictionary containing the catalogue category data as
                                            would be required for a `CatalogueCategoryOut` database model.
        :param manufacturer_out_data: Either `None` or a dictionary containing the manufacturer data as would be
                                      required for a `ManufacturerOut` database model.
        :param obsolete_replacement_catalogue_item_out_data: Either `None` or a dictionary containing the catalogue
                                        category data as would be required for a `CatalogueCategoryOut` database model.
        :param has_duplicate_name: Whether the catalogue item should have a duplicate name as one existing
        """

        # Catalogue category
        if catalogue_category_out_data:
            self._catalogue_category_out = CatalogueCategoryOut(**catalogue_category_out_data)
        ServiceTestHelpers.mock_get(
            self.mock_catalogue_category_repository,
            self._catalogue_category_out if catalogue_category_out_data else None,
        )

        # Manufacturer
        ServiceTestHelpers.mock_get(
            self.mock_manufacturer_repository,
            (ManufacturerOut(**manufacturer_out_data) if manufacturer_out_data else None),
        )

        # Obsolete replacement catalogue item
        ServiceTestHelpers.mock_get(
            self.mock_catalogue_item_repository,
            (
                CatalogueItemOut(**obsolete_replacement_catalogue_item_out_data)
                if obsolete_replacement_catalogue_item_out_data
                else None
            ),
        )

        # Add any property ids automatically from the category (unit tests here should not retest logic tested in
        # utils.validate_properties)
        self._catalogue_item_data = deepcopy(catalogue_item_data)
        if "properties" in self._catalogue_item_data:
            property_name_id_map = {prop["name"]: prop["id"] for prop in catalogue_category_out_data["properties"]}
            for prop in self._catalogue_item_data["properties"]:
                name = prop["name"]
                if name in property_name_id_map:
                    prop["id"] = str(property_name_id_map[name])

        self.mock_catalogue_item_repository.is_duplicate_name.return_value = has_duplicate_name

    def call_validate_create(self) -> None:
        """Calls the `CatalogueItemService` `validate_create` method with the appropriate data from a prior call to
        `mock_validate_create`."""

        # Easier to mock a single validation than a whole list, so do proper testing with single, then have a test
        # for multiple
        self._validate_create_result = self.catalogue_item_service._validate_create(  # pylint:disable=protected-access
            index=0, catalogue_item_data=self._catalogue_item_data
        )

    def check_validate_create_success(
        self, expected_warnings: list[ValidationErrorSchema], expected_errors: list[ValidationErrorSchema]
    ) -> None:
        """Checks that a prior call to `call_validate_create` worked as expected.

        :param expected_warnings: Expected validation warnings.
        :param expected_errors: Expected validation errors.
        """

        if "catalogue_category_id" in self._catalogue_item_data:
            self.mock_catalogue_category_repository.get.assert_called_once_with(
                self._catalogue_item_data["catalogue_category_id"]
            )

        if "obsolete_replacement_catalogue_item_id" in self._catalogue_item_data:
            self.mock_catalogue_item_repository.get.assert_called_once_with(
                self._catalogue_item_data["obsolete_replacement_catalogue_item_id"]
            )

        if "manufacturer_id" in self._catalogue_item_data:
            self.mock_manufacturer_repository.get.assert_called_once_with(self._catalogue_item_data["manufacturer_id"])

        if "name" in self._catalogue_item_data:
            self.mock_catalogue_item_repository.is_duplicate_name.assert_called_once_with(
                self._catalogue_item_data["name"]
            )

        if "properties" in self._catalogue_item_data:
            property_schemas = []

            for property_data in self._catalogue_item_data["properties"]:
                try:
                    property_schemas.append(PropertyPostSchema(**property_data))
                except ValidationError:
                    pass

            if self._catalogue_category_out:
                self.wrapped_utils.validate_properties.assert_called_once_with(
                    # Use ANY for errors as its mutable and changes after running to include the actual errors
                    self._catalogue_category_out.properties,
                    property_schemas,
                    ANY,
                )

        assert self._validate_create_result == ValidationResultSchema(
            index=0, warnings=expected_warnings, errors=expected_errors
        )


class TestValidateCreate(ValidateDSL):
    """Tests for validating catalogue item data for creation."""

    def test_validate_create_with_all_properties(self):
        """Test validating catalogue item data for creation when all properties present in the catalogue category are
        defined in the catalogue item."""

        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
                "catalogue_category_id": str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"]),
                "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
            },
            catalogue_category_out_data=BASE_CATALOGUE_CATEGORY_OUT_DATA_WITH_PROPERTIES_MM,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
        )
        self.call_validate_create()
        self.check_validate_create_success(expected_warnings=[], expected_errors=[])

    def test_validate_create_with_duplicate_name(self):
        """Test validating catalogue item data for creation when it is using a duplicate name as an already existing
        catalogue item."""

        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
                "catalogue_category_id": str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"]),
                "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
            },
            catalogue_category_out_data=BASE_CATALOGUE_CATEGORY_OUT_DATA_WITH_PROPERTIES_MM,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
            has_duplicate_name=True,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[
                ValidationErrorSchema(
                    type="duplicate_record",
                    loc=["name"],
                    msg="Duplicate record found with the same name "
                    f"'{CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES["name"]}'",
                    input="Catalogue Item With All Properties",
                )
            ],
            expected_errors=[],
        )

    def test_validate_create_with_invalid_schema(self):
        """Test validating catalogue item data for creation when the schema itself is invalid."""

        catalogue_item_data = {
            **{"name": 42, "days_to_replace": False},
            "catalogue_category_id": str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"]),
            "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
        }
        self.mock_validate_create(
            catalogue_item_data,
            catalogue_category_out_data=BASE_CATALOGUE_CATEGORY_OUT_DATA_WITH_PROPERTIES_MM,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(type="string_type", loc=["name"], msg="Input should be a valid string", input=42),
                ValidationErrorSchema(
                    type="missing",
                    loc=["cost_gbp"],
                    msg="Field required",
                    input=catalogue_item_data,
                ),
                ValidationErrorSchema(
                    type="missing",
                    loc=["is_obsolete"],
                    msg="Field required",
                    input=catalogue_item_data,
                ),
            ],
        )

    def test_validate_create_with_non_existent_catalogue_category_id(self):
        """Test validating catalogue item data for creation with a non-existent catalogue category ID."""

        catalogue_category_id = str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"])
        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_category_id": catalogue_category_id,
                "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
            },
            catalogue_category_out_data=None,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="missing_record",
                    loc=["catalogue_category_id"],
                    msg=f"No catalogue category found with ID '{catalogue_category_id}'",
                    input=catalogue_category_id,
                )
            ],
        )

    def test_validate_create_with_non_leaf_catalogue_category(self):
        """Test validating catalogue item data for creation with a non-leaf catalogue category."""

        catalogue_category_id = str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"])
        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_category_id": catalogue_category_id,
                "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
            },
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="non_leaf_catalogue_category",
                    loc=["catalogue_category_id"],
                    msg="Cannot add catalogue item to a non-leaf catalogue category",
                    input=catalogue_category_id,
                )
            ],
        )

    def test_validate_create_with_non_existent_manufacturer_id(self):
        """Test validating catalogue item data for creation with a non-existent manufacturer ID."""

        manufacturer_id = str(MANUFACTURER_OUT_DATA_A["_id"])
        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
                "catalogue_category_id": str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"]),
                "manufacturer_id": manufacturer_id,
            },
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_out_data=None,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="missing_record",
                    loc=["manufacturer_id"],
                    msg=f"No manufacturer found with ID '{manufacturer_id}'",
                    input=manufacturer_id,
                )
            ],
        )

    def test_validate_create_with_obsolete_replacement_catalogue_item(self):
        """Test validating catalogue item data for creation with an obsolete replacement catalogue item."""

        obsolete_replacement_catalogue_item_id = str(ObjectId())
        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "catalogue_category_id": str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"]),
                "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            },
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
            obsolete_replacement_catalogue_item_out_data=CATALOGUE_ITEM_OUT_DATA_NOT_OBSOLETE_NO_PROPERTIES,
        )
        self.call_validate_create()
        self.check_validate_create_success(expected_warnings=[], expected_errors=[])

    def test_validate_create_with_non_existent_obsolete_replacement_catalogue_item_id(self):
        """Test validating catalogue item data for creation with a non-existent obsolete replacement catalogue item
        ID."""

        obsolete_replacement_catalogue_item_id = str(ObjectId())
        self.mock_validate_create(
            {
                **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
                "catalogue_category_id": str(CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES["_id"]),
                "manufacturer_id": str(MANUFACTURER_OUT_DATA_A["_id"]),
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            },
            catalogue_category_out_data=CATALOGUE_CATEGORY_OUT_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_out_data=MANUFACTURER_OUT_DATA_A,
            obsolete_replacement_catalogue_item_out_data=None,
        )
        self.call_validate_create()
        self.check_validate_create_success(
            expected_warnings=[],
            expected_errors=[
                ValidationErrorSchema(
                    type="missing_record",
                    loc=["obsolete_replacement_catalogue_item_id"],
                    msg=f"No catalogue item found with ID '{obsolete_replacement_catalogue_item_id}'",
                    input=obsolete_replacement_catalogue_item_id,
                )
            ],
        )


class TestBulkValidateCreate(CatalogueItemServiceDSL):
    """Tests for bulk validating catalogue items data for creation."""

    def test_bulk_validate_create(self):
        """Test bulk validate correctly returns a list of validation results for the individual catalogue items."""
        mock_catalogue_items = [{"name": "1"}, {"name": "2"}, {"name": "3"}]
        mock_results = [
            ValidationResultSchema(index=index, warnings=[], errors=[]) for index in range(0, len(mock_catalogue_items))
        ]
        mock_validate_create = MagicMock(side_effect=mock_results)

        with patch.object(self.catalogue_item_service, "_validate_create", mock_validate_create):
            result = self.catalogue_item_service.bulk_validate_create(mock_catalogue_items)
        assert mock_validate_create.call_args_list == [
            call(index, mock_catalogue_item) for index, mock_catalogue_item in enumerate(mock_catalogue_items)
        ]
        assert result == BulkValidationResultSchema(results=mock_results)
