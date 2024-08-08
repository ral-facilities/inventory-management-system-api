# pylint: disable=too-many-lines
"""
Unit tests for the `ItemService` service.
"""

from datetime import datetime, timedelta, timezone
from test.conftest import add_ids_to_properties
from test.mock_data import (
    BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
    BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    ITEM_DATA_REQUIRED_VALUES_ONLY,
    ITEM_DATA_WITH_ALL_PROPERTIES,
    USAGE_STATUS_IN_DATA_IN_USE,
)
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW, ServiceTestHelpers
from typing import List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidActionError,
    InvalidObjectIdError,
    InvalidPropertyTypeError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    CatalogueCategoryPropertyIn,
)
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut, PropertyIn
from inventory_management_system_api.models.item import ItemIn, ItemOut
from inventory_management_system_api.models.system import SystemOut
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.schemas.catalogue_item import PropertyPostSchema
from inventory_management_system_api.schemas.item import ItemPatchSchema, ItemPostSchema
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.item import ItemService


class ItemServiceDSL:
    """Base class for `ItemService` unit tests."""

    wrapped_utils: Mock
    mock_item_repository: Mock
    mock_catalogue_item_repository: Mock
    mock_catalogue_category_repository: Mock
    mock_system_repository: Mock
    mock_usage_status_repository: Mock
    item_service: ItemService

    property_name_id_dict: dict[str, str]

    # pylint:disable=too-many-arguments
    @pytest.fixture(autouse=True)
    def setup(
        self,
        item_repository_mock,
        catalogue_item_repository_mock,
        catalogue_category_repository_mock,
        system_repository_mock,
        usage_status_repository_mock,
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
        self.item_service = item_service

        with patch("inventory_management_system_api.services.item.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield

    # TODO: Is this needed? Could this be reused - copied from test_catalogue_items
    def construct_properties_in_and_post_with_ids(
        self,
        catalogue_category_properties_in: list[CatalogueCategoryPropertyIn],
        properties_data: list[dict],
    ) -> tuple[list[PropertyIn], list[PropertyPostSchema]]:
        """
        Returns a list of property post schemas and expected property in models by adding
        in unit IDs. It also assigns `unit_value_id_dict` for looking up these IDs.

        :param catalogue_category_properties_in: List of `CatalogueCategoryPropertyIn`'s as would be found in the
                                                 catalogue category.
        :param properties_data: List of dictionaries containing the data for each property as would be required for a
                                `PropertyPostSchema` but without any `id`'s.
        :returns: Tuple of lists. The first contains the expected `PropertyIn` models and the second the
                  `PropertyPostSchema` schema's that should be posted in order to obtain them.
        """

        property_post_schemas = []
        expected_properties_in = []

        self.property_name_id_dict = {}

        for prop in properties_data:
            prop_id = None
            prop_without_name = prop.copy()

            # Find the corresponding catalogue category property with the same name
            for found_prop in catalogue_category_properties_in:
                if found_prop.name == prop["name"]:
                    prop_id = str(found_prop.id)
                    self.property_name_id_dict["name"] = prop_id
                    del prop_without_name["name"]
                    break

            expected_properties_in.append(PropertyIn(**prop, id=prop_id))
            property_post_schemas.append(PropertyPostSchema(**prop_without_name, id=prop_id))

        return expected_properties_in, property_post_schemas


class CreateDSL(ItemServiceDSL):
    """Base class for `create` tests."""

    _catalogue_item_out: Optional[CatalogueItemOut]
    _catalogue_category_out: Optional[CatalogueCategoryOut]
    _usage_status_out: Optional[UsageStatusOut]
    _item_post: ItemPostSchema
    _expected_item_in: ItemIn
    _expected_item_out: ItemOut
    _created_item: CatalogueItemOut
    _create_exception: pytest.ExceptionInfo

    # TODO: Update comment below - particularly part about missing any mandatory ids - may need to say have value
    # instead
    # pylint:disable=too-many-arguments
    def mock_create(
        self,
        item_data: dict,
        catalogue_item_data: Optional[dict] = None,
        catalogue_category_in_data: Optional[dict] = None,
        usage_status_in_data: Optional[dict] = None,
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
        """

        # Generate mandatory IDs to be inserted where needed
        catalogue_item_id = str(ObjectId())
        system_id = str(ObjectId())
        usage_status_id = str(ObjectId())

        ids_to_insert = {
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
            "usage_status_id": usage_status_id,
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
        catalogue_item_property_post_schemas = []
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
                }
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
            UsageStatusOut(**{**usage_status_in.model_dump(), "_id": usage_status_id}) if usage_status_in else None
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
        supplied_properties = self._item_post.properties if self._item_post.properties else []

        supplied_properties_dict = {
            supplied_property.id: supplied_property for supplied_property in supplied_properties
        }
        expected_merged_properties: List[PropertyPostSchema] = []

        if self._catalogue_item_out and self._catalogue_category_out:
            for prop in self._catalogue_item_out.properties:
                supplied_property = supplied_properties_dict.get(prop.id)
                expected_merged_properties.append(
                    supplied_property if supplied_property else PropertyPostSchema(**prop.model_dump())
                )

            expected_properties_in = utils.process_properties(
                self._catalogue_category_out.properties, expected_merged_properties
            )

        self._expected_item_in = ItemIn(**{**item_data, **ids_to_insert, "properties": expected_properties_in})
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

        self.mock_item_repository.create.assert_called_once_with(self._expected_item_in)

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
    """Tests for creating a item."""

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

    def test_create_with_no_properties_defined(self):
        """Test creating an item when none of the properties present in the catalogue item are defined in the item."""

        self.mock_create(
            ITEM_DATA_REQUIRED_VALUES_ONLY,
            catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_all_properties(self):
        """Test creating an item when all properties present in the catalogue item are defined in the item."""

        self.mock_create(
            ITEM_DATA_WITH_ALL_PROPERTIES,
            catalogue_item_data=BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES,
            catalogue_category_in_data=BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM,
            usage_status_in_data=USAGE_STATUS_IN_DATA_IN_USE,
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


# # pylint: disable=duplicate-code
# FULL_CATALOGUE_CATEGORY_A_INFO = {
#     "name": "Category A",
#     "code": "category-a",
#     "is_leaf": True,
#     "parent_id": None,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
#         {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
#         {"name": "Property D", "type": "string", "unit": None, "mandatory": False},
#     ],
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }

# FULL_CATALOGUE_ITEM_A_INFO = {
#     "name": "Catalogue Item A",
#     "description": "This is Catalogue Item A",
#     "cost_gbp": 129.99,
#     "cost_to_rework_gbp": None,
#     "days_to_replace": 2.0,
#     "days_to_rework": None,
#     "drawing_link": "https://drawing-link.com/",
#     "drawing_number": None,
#     "item_model_number": "abc123",
#     "is_obsolete": False,
#     "obsolete_reason": None,
#     "obsolete_replacement_catalogue_item_id": None,
#     "notes": None,
#     "properties": [
#         {"name": "Property A", "value": 20, "unit": "mm"},
#         {"name": "Property B", "value": False, "unit": None},
#         {"name": "Property C", "value": "20x15x10", "unit": "cm"},
#     ],
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }

# ITEM_INFO = {
#     "is_defective": False,
#     "warranty_end_date": datetime(2015, 11, 15, 23, 59, 59, 0, tzinfo=timezone.utc),
#     "serial_number": "xyz123",
#     "delivered_date": datetime(2012, 12, 5, 12, 0, 0, 0, tzinfo=timezone.utc),
#     "notes": "Test notes",
#     "properties": [{"name": "Property A", "value": 21}],
# }

# FULL_ITEM_INFO = {
#     **ITEM_INFO,
#     "purchase_order_number": None,
#     "asset_number": None,
#     "properties": [
#         {"name": "Property A", "value": 21, "unit": "mm"},
#         {"name": "Property B", "value": False, "unit": None},
#         {"name": "Property C", "value": "20x15x10", "unit": "cm"},
#         {"name": "Property D", "value": None, "unit": None},
#     ],
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }

# FULL_SYSTEM_INFO = {
#     "name": "Test name a",
#     "code": "test-name-a",
#     "location": "Test location",
#     "owner": "Test owner",
#     "importance": "low",
#     "description": "Test description",
#     "parent_id": None,
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }
# USAGE_STATUS_A = {
#     "value": "New",
#     "code": "new",
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }
# USAGE_STATUS_B = {
#     "value": "Used",
#     "code": "used",
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }


# # pylint: enable=duplicate-code


# def test_delete(item_repository_mock, item_service):
#     """
#     Test deleting item.

#     Verify that the `delete` method properly handles the deletion of item by ID.
#     """
#     item_id = str(ObjectId())

#     item_service.delete(item_id)

#     item_repository_mock.delete.assert_called_once_with(item_id)


# def test_get(test_helpers, item_repository_mock, item_service):
#     """
#     Test getting an item.

#     Verify that the `get` method properly handles the retrieval of the item by ID.
#     """
#     item_id = str(ObjectId())
#     item = MagicMock()

#     # Mock `get` to return an item
#     test_helpers.mock_get(item_repository_mock, item)

#     retrieved_item = item_service.get(item_id)

#     item_repository_mock.get.assert_called_once_with(item_id)
#     assert retrieved_item == item


# def test_get_with_non_existent_id(test_helpers, item_repository_mock, item_service):
#     """
#     Test getting an item with a non-existent ID.

#     Verify the `get` method properly handles the retrieval of an item with a non-existent ID.
#     """
#     item_id = str(ObjectId())

#     # Mock get to not return an item
#     test_helpers.mock_get(item_repository_mock, None)

#     retrieved_item = item_service.get(item_id)

#     assert retrieved_item is None
#     item_repository_mock.get.assert_called_once_with(item_id)


# def test_list(item_repository_mock, item_service):
#     """
#     Test listing items.

#     Verify that the `list` method properly calls the repository function
#     """
#     result = item_service.list(None, None)

#     item_repository_mock.list.assert_called_once_with(None, None)
#     assert result == item_repository_mock.list.return_value


# def test_update(
#     test_helpers,
#     item_repository_mock,
#     usage_status_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     item_service,
# ):
#     """
#     Test updating an item,

#     Verify that the `update` method properly handles the item to be updated.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="Used",
#         **{
#             **FULL_ITEM_INFO,
#             "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "is_defective": True,
#                 "usage_status": item.usage_status,
#                 "usage_status_id": item.usage_status_id,
#                 "modified_time": item.created_time,
#                 "properties": item_properties,
#             }
#         ),
#     )
#     # Mock `update` to return the updated item
#     test_helpers.mock_update(item_repository_mock, item)
#     # Mock `get` to return the usage status
#     test_helpers.mock_get(
#         usage_status_repository_mock,
#         UsageStatusOut(id=item.usage_status_id, **USAGE_STATUS_B),
#     )
#     updated_item = item_service.update(
#         item.id,
#         ItemPatchSchema(is_defective=item.is_defective, usage_status_id=item.usage_status_id),
#     )

#     item_repository_mock.update.assert_called_once_with(
#         item.id,
#         ItemIn(
#             catalogue_item_id=item.catalogue_item_id,
#             system_id=item.system_id,
#             usage_status_id=item.usage_status_id,
#             usage_status=item.usage_status,
#             **{
#                 **FULL_ITEM_INFO,
#                 "created_time": item.created_time,
#                 "properties": item_properties,
#             },
#         ),
#     )
#     assert updated_item == item


# def test_update_with_non_existent_id(test_helpers, item_repository_mock, item_service):
#     """
#     Test updating an item with a non-existent ID.

#     Verify that the `update` method properly handles the item to be updated with a non-existent ID.
#     """
#     # Mock `get` to return an item
#     test_helpers.mock_get(item_repository_mock, None)

#     item_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         item_service.update(item_id, ItemPatchSchema(properties=[]))
#     item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No item found with ID: {item_id}"


# def test_update_change_catalogue_item_id(test_helpers, item_repository_mock, item_service):
#     """
#     Test updating an item with a catalogue item ID.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "catalogue_item_id": str(ObjectId()),
#                 "properties": item_properties,
#             }
#         ),
#     )

#     catalogue_item_id = str(ObjectId())
#     with pytest.raises(InvalidActionError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(catalogue_item_id=catalogue_item_id),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == "Cannot change the catalogue item the item belongs to"


# def test_update_change_system_id(
#     test_helpers,
#     item_repository_mock,
#     system_repository_mock,
#     usage_status_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     item_service,
#     # pylint: disable=too-many-arguments
# ):
#     """
#     Test updating system id to an existing id
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "system_id": str(ObjectId()),
#                 "modified_time": item.created_time,
#                 "properties": item_properties,
#             }
#         ),
#     )

#     # Mock `get` to return a system
#     test_helpers.mock_get(
#         system_repository_mock,
#         SystemOut(
#             id=item.system_id,
#             **FULL_SYSTEM_INFO,
#         ),
#     )

#     # Mock `get` to return the usage status
#     test_helpers.mock_get(
#         usage_status_repository_mock,
#         UsageStatusOut(id=item.usage_status_id, **USAGE_STATUS_A),
#     )

#     # Mock `update` to return the updated item
#     test_helpers.mock_update(item_repository_mock, item)

#     updated_item = item_service.update(
#         item.id,
#         ItemPatchSchema(system_id=item.system_id),
#     )

#     item_repository_mock.update.assert_called_once_with(
#         item.id,
#         ItemIn(
#             catalogue_item_id=item.catalogue_item_id,
#             system_id=item.system_id,
#             usage_status=item.usage_status,
#             usage_status_id=item.usage_status_id,
#             **{
#                 **FULL_ITEM_INFO,
#                 "created_time": item.created_time,
#                 "properties": item_properties,
#             },
#         ),
#     )
#     assert updated_item == item


# def test_update_with_non_existent_system_id(test_helpers, system_repository_mock, item_repository_mock, item_service):
#     """
#     Test updating an item with a non-existent system ID.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "system_id": str(ObjectId()),
#                 "properties": item_properties,
#             }
#         ),
#     )

#     # Mock `get` to not return a catalogue item
#     test_helpers.mock_get(system_repository_mock, None)

#     system_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(system_id=system_id),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No system found with ID: {system_id}"


# def test_update_with_non_existent_usage_status(
#     test_helpers, usage_status_repository_mock, item_repository_mock, item_service
# ):
#     """
#     Test updating an item with a non-existent usage status ID.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "usage_status_id": str(ObjectId()),
#                 "properties": item_properties,
#             }
#         ),
#     )

#     # Mock `get` to not return a catalogue item
#     test_helpers.mock_get(usage_status_repository_mock, None)

#     usage_status_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(usage_status_id=usage_status_id),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"


# def test_update_with_invalid_usage_status(
#     test_helpers, usage_status_repository_mock, item_repository_mock, item_service
# ):
#     """
#     Test updating an item with a invalid usage status ID.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "usage_status_id": str(ObjectId()),
#                 "properties": item_properties,
#             }
#         ),
#     )

#     # Mock `get` to not return a catalogue item
#     test_helpers.mock_get(usage_status_repository_mock, None)

#     usage_status_id = "invalid"
#     with pytest.raises(MissingRecordError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(usage_status_id=usage_status_id),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"


# def test_update_change_property_value(
#     test_helpers,
#     catalogue_item_repository_mock,
#     catalogue_category_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     item_service,
# ):  # pylint: disable=too-many-arguments
#     """
#     Test updating a value of a property
#     """
#     item_properties = add_ids_to_properties(
#         None,
#         [
#             {"name": "Property A", "value": 1, "unit": "mm"},
#             *FULL_ITEM_INFO["properties"][-3:],
#         ],
#     )
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
#             "properties": item_properties,
#         },
#     )

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "properties": item_properties,
#                 "modified_time": item.created_time,
#             }
#         ),
#     )

#     catalogue_category_id = str(ObjectId())
#     manufacturer_id = str(ObjectId())

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=item.catalogue_item_id,
#             catalogue_category_id=catalogue_category_id,
#             manufacturer_id=manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     item_properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # pylint: enable=duplicate-code

#     # Mock `update` to return the updated item
#     test_helpers.mock_update(item_repository_mock, item)

#     updated_item = item_service.update(
#         item.id,
#         ItemPatchSchema(properties=[{"id": prop.id, "value": prop.value} for prop in item.properties]),
#     )

#     item_repository_mock.update.assert_called_once_with(
#         item.id,
#         ItemIn(
#             catalogue_item_id=item.catalogue_item_id,
#             system_id=item.system_id,
#             usage_status_id=item.usage_status_id,
#             usage_status=item.usage_status,
#             **{
#                 **FULL_ITEM_INFO,
#                 "created_time": item.created_time,
#                 "properties": item_properties,
#             },
#         ),
#     )
#     assert updated_item == item


# def test_update_with_missing_existing_properties(
#     test_helpers,
#     catalogue_item_repository_mock,
#     catalogue_category_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     item_service,
# ):  # pylint: disable=too-many-arguments
#     """
#     Test updating properties with missing properties
#     """
#     item_properties = add_ids_to_properties(
#         None,
#         [
#             FULL_CATALOGUE_ITEM_A_INFO["properties"][0],
#             *FULL_ITEM_INFO["properties"][-3:],
#         ],
#     )
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
#             "properties": item_properties,
#         },
#     )

#     # Mock `get` to return an item
#     test_helpers.mock_get(
#         item_repository_mock,
#         ItemOut(
#             **{
#                 **item.model_dump(),
#                 "properties": add_ids_to_properties(None, FULL_ITEM_INFO["properties"]),
#                 "modified_time": item.created_time,
#             }
#         ),
#     )

#     catalogue_category_id = str(ObjectId())
#     manufacturer_id = str(ObjectId())

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=item.catalogue_item_id,
#             catalogue_category_id=catalogue_category_id,
#             manufacturer_id=manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     item_properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # pylint: enable=duplicate-code

#     # Mock `update` to return the updated item
#     test_helpers.mock_update(item_repository_mock, item)

#     updated_item = item_service.update(
#         item.id,
#         ItemPatchSchema(properties=[{"id": prop.id, "value": prop.value} for prop in item.properties[-2:]]),
#     )

#     item_repository_mock.update.assert_called_once_with(
#         item.id,
#         ItemIn(
#             catalogue_item_id=item.catalogue_item_id,
#             system_id=item.system_id,
#             usage_status_id=item.usage_status_id,
#             usage_status=item.usage_status,
#             **{
#                 **FULL_ITEM_INFO,
#                 "created_time": item.created_time,
#                 "properties": item_properties,
#             },
#         ),
#     )
#     assert updated_item == item


# def test_update_change_value_for_string_property_invalid_type(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     item_service,
# ):
#     """
#     Test changing the value of a string property to an invalid type.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(item_repository_mock, item)

#     catalogue_category_id = str(ObjectId())
#     manufacturer_id = str(ObjectId())

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=item.catalogue_item_id,
#             catalogue_category_id=catalogue_category_id,
#             manufacturer_id=manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     item_properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     properties = [{"id": prop.id, "value": prop.value} for prop in item.properties]
#     properties[2]["value"] = True
#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(properties=properties),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == f"Invalid value type for property with ID '{item.properties[2].id}'. Expected type: string."
#     )


# def test_update_change_value_for_number_property_invalid_type(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     item_service,
# ):
#     """
#     Test changing the value of a number property to an invalid type.
#     """
#     # pylint: disable=duplicate-code
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return an item
#     test_helpers.mock_get(item_repository_mock, item)

#     catalogue_category_id = str(ObjectId())
#     manufacturer_id = str(ObjectId())

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=item.catalogue_item_id,
#             catalogue_category_id=catalogue_category_id,
#             manufacturer_id=manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     item_properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     properties = [{"id": prop.id, "value": prop.value} for prop in item.properties]
#     properties[0]["value"] = "20"
#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(properties=properties),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == f"Invalid value type for property with ID '{item.properties[0].id}'. Expected type: number."
#     )


# def test_update_change_value_for_boolean_property_invalid_type(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     item_service,
# ):
#     """
#     Test changing the value of a boolean property to an invalid type.
#     """
#     item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
#     item = ItemOut(
#         id=str(ObjectId()),
#         catalogue_item_id=str(ObjectId()),
#         system_id=str(ObjectId()),
#         usage_status_id=str(ObjectId()),
#         usage_status="New",
#         **{
#             **FULL_ITEM_INFO,
#             "properties": item_properties,
#         },
#     )

#     # Mock `get` to return an item
#     test_helpers.mock_get(item_repository_mock, item)

#     catalogue_category_id = str(ObjectId())
#     manufacturer_id = str(ObjectId())

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=item.catalogue_item_id,
#             catalogue_category_id=catalogue_category_id,
#             manufacturer_id=manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     item_properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     properties = [{"id": prop.id, "value": prop.value} for prop in item.properties]
#     properties[1]["value"] = "False"
#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         item_service.update(
#             item.id,
#             ItemPatchSchema(properties=properties),
#         )
#     item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == f"Invalid value type for property with ID '{item.properties[1].id}'. Expected type: boolean."
#     )
