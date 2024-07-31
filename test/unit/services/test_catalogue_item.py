# pylint: disable=too-many-lines
"""
Unit tests for the `CatalogueCategoryService` service.
"""
from datetime import timedelta
from test.conftest import add_ids_to_properties
from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_ITEM_POST_DATA_REQUIRED_VALUES_ONLY,
    MANUFACTURER_IN_DATA_A,
)
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW, ServiceTestHelpers
from typing import Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidActionError,
    InvalidPropertyTypeError,
    MissingMandatoryProperty,
    MissingRecordError,
    NonLeafCatalogueCategoryError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut, PropertyIn
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.schemas.catalogue_item import (
    CatalogueItemPatchSchema,
    CatalogueItemPostSchema,
    PropertyPostSchema,
)
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.catalogue_item import CatalogueItemService


class CatalogueItemServiceDSL:
    """Base class for `CatalogueItemService` unit tests."""

    wrapped_utils: Mock
    mock_catalogue_item_repository: Mock
    mock_catalogue_category_repository: Mock
    mock_manufacturer_repository: Mock
    mock_unit_repository: Mock
    catalogue_item_service: CatalogueItemService

    property_name_id_dict: dict[str, str]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        catalogue_item_repository_mock,
        catalogue_category_repository_mock,
        manufacturer_repository_mock,
        unit_repository_mock,
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
        self.catalogue_item_service = catalogue_item_service

        with patch("inventory_management_system_api.services.catalogue_item.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield

    def check_add_property_unit_values_performed_expected_calls(
        self, expected_properties: list[PropertyPostSchema]
    ) -> None:
        """Checks that a call to `add_property_unit_values` performed the expected function calls.

        :param expected_properties: Expected properties the function would have been called with.
        """

        expected_unit_repo_calls = []
        for prop in expected_properties:
            if prop.unit_id:
                expected_unit_repo_calls.append(call(prop.unit_id))

        self.mock_unit_repository.get.assert_has_calls(expected_unit_repo_calls)


class CreateDSL(CatalogueItemServiceDSL):
    """Base class for `create` tests."""

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
    ) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param catalogue_item_data: Dictionary containing the basic catalogue item data as would be required for a
                                    `CatalogueItemPostSchema` but with any `unit_id`'s replaced by the 'unit' value in
                                    its properties as the IDs will be added automatically.
        :param catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data as would
                                           be required for a `CatalogueCategoryIn` database model.
        :param manufacturer_in_data: Either `None` or a dictionary containing the manufacturer data as would be required
                                     for a `ManufacturerIn` database model.
        :param obsolete_replacement_catalogue_item_data: Dictionary containing the basic catalogue item data for the
                                     obsolete replacement as would be required for a `CatalogueItemPostSchema` but with
                                     any `unit_id`'s replaced by the 'unit' value in its properties as the IDs will be
                                     added automatically.
        """

        # TODO: Cleanup?

        catalogue_category_in_dump = {}
        if catalogue_category_in_data:
            catalogue_category_in = CatalogueCategoryIn(**catalogue_category_in_data)
            self.property_name_id_dict = {prop.name: prop.id for prop in catalogue_category_in.properties}

            catalogue_category_in_dump = catalogue_category_in.model_dump(by_alias=True)

        ServiceTestHelpers.mock_get(
            self.mock_catalogue_category_repository,
            (
                CatalogueCategoryOut(
                    **{
                        **catalogue_category_in_dump,
                        "_id": catalogue_item_data["catalogue_category_id"],
                    },
                )
                if catalogue_category_in_data
                else None
            ),
        )

        ServiceTestHelpers.mock_get(
            self.mock_manufacturer_repository,
            (
                ManufacturerOut(
                    **{
                        **ManufacturerIn(**manufacturer_in_data).model_dump(),
                        "_id": catalogue_item_data["manufacturer_id"],
                    },
                )
                if manufacturer_in_data
                else None
            ),
        )

        ServiceTestHelpers.mock_get(
            self.mock_catalogue_item_repository,
            (
                CatalogueItemOut(
                    **{
                        **CatalogueItemIn(**obsolete_replacement_catalogue_item_data).model_dump(),
                        "_id": catalogue_item_data["obsolete_replacement_catalogue_item_id"],
                    },
                )
                if obsolete_replacement_catalogue_item_data
                else None
            ),
        )

        # TODO: Go over catalogue categories and check if should use this method instead of current
        expected_properties_in = []
        if "properties" in catalogue_item_data:
            expected_properties_in = add_ids_to_properties(
                catalogue_category_in_dump["properties"], catalogue_item_data["properties"]
            )

        self._catalogue_item_post = CatalogueItemPostSchema(
            **{**catalogue_item_data, "properties": expected_properties_in}
        )

        self._expected_catalogue_item_in = CatalogueItemIn(
            **{
                **catalogue_item_data,
                "properties": expected_properties_in,
            }
        )
        self._expected_catalogue_item_out = CatalogueItemOut(
            **self._expected_catalogue_item_in.model_dump(), id=ObjectId()
        )

        ServiceTestHelpers.mock_create(self.mock_catalogue_item_repository, self._expected_catalogue_item_out)

    def call_create(self) -> None:
        """Calls the `CatalogueItemService` `create` method with the appropriate data from a prior call to
        `mock_create`."""

        self._created_catalogue_item = self.catalogue_item_service.create(self._catalogue_item_post)

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

        # TODO: Process properties

        if self._catalogue_item_post.properties:
            pass
            # TODO: Implement properties check
            # # To assert with property IDs we must compare as dicts and use ANY here as otherwise the ObjectIds will
            # # always be different
            # actual_catalogue_category_in = self.mock_catalogue_category_repository.create.call_args_list[0][0][0]
            # assert isinstance(actual_catalogue_category_in, CatalogueCategoryIn)
            # assert actual_catalogue_category_in.model_dump() == {
            #     **self._expected_catalogue_category_in.model_dump(),
            #     "properties": [
            #         {**prop.model_dump(), "id": ANY} for prop in self._expected_catalogue_category_in.properties
            #     ],
            # }
        else:
            self.mock_catalogue_item_repository.create.assert_called_once_with(self._expected_catalogue_item_in)

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
            CATALOGUE_ITEM_POST_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_catalogue_category_id(self):
        """Test creating a catalogue item with a non-existent catalogue category ID."""

        self.mock_create(
            CATALOGUE_ITEM_POST_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=None,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No catalogue category found with ID: {self._catalogue_item_post.catalogue_category_id}"
        )

    def test_create_with_non_leaf_catalogue_category(self):
        """Test creating a catalogue item with a non-leaf catalogue category."""

        self.mock_create(
            CATALOGUE_ITEM_POST_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
        )
        self.call_create_expecting_error(NonLeafCatalogueCategoryError)
        self.check_create_failed_with_exception("Cannot add catalogue item to a non-leaf catalogue category")

    def test_create_with_non_existent_manufacturer_id(self):
        """Test creating a catalogue item with a non-existent manufacturer ID."""

        self.mock_create(
            CATALOGUE_ITEM_POST_DATA_REQUIRED_VALUES_ONLY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No manufacturer found with ID: {self._catalogue_item_post.manufacturer_id}"
        )

    def test_create_with_non_existent_obsolete_replacement_catalogue_item_id(self):
        """Test creating a catalogue item with a non-existent obsolete replacement catalogue item ID."""

        obsolete_replacement_catalogue_item_id = str(ObjectId())
        self.mock_create(
            {
                **CATALOGUE_ITEM_POST_DATA_REQUIRED_VALUES_ONLY,
                "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
            },
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            manufacturer_in_data=MANUFACTURER_IN_DATA_A,
            obsolete_replacement_catalogue_item_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(
            f"No catalogue item found with ID: {obsolete_replacement_catalogue_item_id}"
        )


# FULL_CATALOGUE_CATEGORY_A_INFO = {
#     "name": "Category A",
#     "code": "category-a",
#     "is_leaf": True,
#     "parent_id": None,
#     "properties": [
#         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
#         {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
#         {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
#     ],
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }

# FULL_CATALOGUE_CATEGORY_B_INFO = {
#     "name": "Category B",
#     "code": "category-b",
#     "is_leaf": False,
#     "parent_id": None,
#     "properties": [],
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }

# FULL_CATALOGUE_CATEGORY_C_INFO = {
#     "name": "Category C",
#     "code": "category-c",
#     "is_leaf": True,
#     "parent_id": None,
#     "properties": [],
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }

# # pylint: disable=duplicate-code
# CATALOGUE_ITEM_A_INFO = {
#     "name": "Catalogue Item A",
#     "description": "This is Catalogue Item A",
#     "cost_gbp": 129.99,
#     "days_to_replace": 2.0,
#     "drawing_link": "https://drawing-link.com/",
#     "item_model_number": "abc123",
#     "is_obsolete": False,
#     "properties": [
#         {"name": "Property A", "value": 20},
#         {"name": "Property B", "value": False},
#         {"name": "Property C", "value": "20x15x10"},
#     ],
# }

# FULL_CATALOGUE_ITEM_A_INFO = {
#     **CATALOGUE_ITEM_A_INFO,
#     "cost_to_rework_gbp": None,
#     "days_to_rework": None,
#     "drawing_number": None,
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
# # pylint: enable=duplicate-code

# # pylint: disable=duplicate-code
# FULL_MANUFACTURER_INFO = {
#     "name": "Manufacturer A",
#     "code": "manufacturer-a",
#     "url": "http://example.com/",
#     "address": {
#         "address_line": "1 Example Street",
#         "town": "Oxford",
#         "county": "Oxfordshire",
#         "country": "United Kingdom",
#         "postcode": "OX1 2AB",
#     },
#     "telephone": "0932348348",
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }
# # pylint: enable=duplicate-code


# def test_create(
#     test_helpers,
#     catalogue_item_repository_mock,
#     catalogue_category_repository_mock,
#     manufacturer_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):  # pylint: disable=too-many-arguments
#     """
#     Test creating a catalogue item.

#     Verify that the `create` method properly handles the catalogue item to be created, checks that the catalogue
#     category exists and that it is a leaf category, checks for missing mandatory , filters the
#     matching , adds the units to the supplied properties, and validates the property values.
#     """
#     # pylint: disable=duplicate-code
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(properties, FULL_CATALOGUE_CATEGORY_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `get` to return a manufacturer
#     test_helpers.mock_get(
#         manufacturer_repository_mock,
#         ManufacturerOut(id=catalogue_item.manufacturer_id, **FULL_MANUFACTURER_INFO),
#     )
#     # Mock `create` to return the created catalogue item
#     test_helpers.mock_create(catalogue_item_repository_mock, catalogue_item)

#     created_catalogue_item = catalogue_item_service.create(
#         CatalogueItemPostSchema(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **CATALOGUE_ITEM_A_INFO,
#                 "properties": [{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties],
#             },
#         )
#     )

#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_item.catalogue_category_id)
#     catalogue_item_repository_mock.create.assert_called_once_with(
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": properties,
#             },
#         )
#     )
#     assert created_catalogue_item == catalogue_ite


# def test_create_with_obsolete_replacement_catalogue_item_id(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test creating a catalogue item with an obsolete replacement catalogue item ID.
#     """
#     obsolete_replacement_catalogue_item_id = str(ObjectId())
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "is_obsolete": True,
#             "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `get` to return a replacement catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=obsolete_replacement_catalogue_item_id,
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "name": "Catalogue Item B",
#                 "description": "This is Catalogue Item B",
#                 "properties": properties,
#             },
#         ),
#     )
#     # Mock `create` to return the created catalogue item
#     test_helpers.mock_create(catalogue_item_repository_mock, catalogue_item)

#     created_catalogue_item = catalogue_item_service.create(
#         CatalogueItemPostSchema(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **CATALOGUE_ITEM_A_INFO,
#                 "is_obsolete": True,
#                 "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
#                 "properties": [{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties],
#             },
#         )
#     )

#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_item.catalogue_category_id)
#     catalogue_item_repository_mock.get.assert_called_once_with(obsolete_replacement_catalogue_item_id)
#     catalogue_item_repository_mock.create.assert_called_once_with(
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "is_obsolete": True,
#                 "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
#                 "properties": properties,
#             },
#         )
#     )
#     assert created_catalogue_item == catalogue_item


# def test_create_without_properties(
#     test_helpers,
#     catalogue_item_repository_mock,
#     catalogue_category_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test creating a catalogue item without properties.

#     Verify that the `create` method properly handles the catalogue item to be created without properties.
#     """
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{**FULL_CATALOGUE_ITEM_A_INFO, "properties": []},
#     )

#     # Mock `get` to return the catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{**FULL_CATALOGUE_CATEGORY_A_INFO, "properties": []},
#         ),
#     )
#     # Mock `create` to return the created catalogue item
#     test_helpers.mock_create(catalogue_item_repository_mock, catalogue_item)

#     created_catalogue_item = catalogue_item_service.create(
#         CatalogueItemPostSchema(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{**CATALOGUE_ITEM_A_INFO, "properties": []},
#         )
#     )

#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_item.catalogue_category_id)
#     catalogue_item_repository_mock.create.assert_called_once_with(
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{**FULL_CATALOGUE_ITEM_A_INFO, "properties": []},
#         )
#     )
#     assert created_catalogue_item == catalogue_item


# def test_create_with_missing_mandatory_properties(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test creating a catalogue item with missing mandatory properties.

#     Verify that the `create` method properly handles a catalogue item with missing mandatory properties, checks that
#     the catalogue category exists and that it is a leaf category, finds that there are missing mandatory catalogue item
#     properties, and does not create the catalogue item.
#     """
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_CATEGORY_A_INFO,
#             "properties": add_ids_to_properties(
#                 None,
#                 FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#             ),
#         },
#     )

#     # Mock `get` to return the catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(MissingMandatoryProperty) as exc:
#         catalogue_item_service.create(
#             CatalogueItemPostSchema(
#                 catalogue_category_id=catalogue_category.id,
#                 manufacturer_id=str(ObjectId()),
#                 **{
#                     **CATALOGUE_ITEM_A_INFO,
#                     "properties": [
#                         {
#                             "id": catalogue_category.properties[2].id,
#                             "value": "20x15x10",
#                         },
#                     ],
#                 },
#             ),
#         )
#     assert str(exc.value) == f"Missing mandatory property with ID: '{catalogue_category.properties[1].id}'"
#     catalogue_item_repository_mock.create.assert_not_called()
#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


# def test_create_with_with_invalid_value_type_for_string_property(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test creating a catalogue item with invalid value type for a string property.

#     Verify that the `create` method properly handles a catalogue item with invalid value type for a string property,
#     checks that the catalogue category exists and that it is a leaf category, checks that there are no missing mandatory
#     properties, finds invalid value type for a string property, and does not create the catalogue item.
#     """
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_CATEGORY_A_INFO,
#             "properties": add_ids_to_properties(
#                 None,
#                 FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#             ),
#         },
#     )

#     # Mock `get` to return the catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         catalogue_item_service.create(
#             CatalogueItemPostSchema(
#                 catalogue_category_id=catalogue_category.id,
#                 manufacturer_id=str(ObjectId()),
#                 **{
#                     **CATALOGUE_ITEM_A_INFO,
#                     "properties": [
#                         {"id": catalogue_category.properties[0].id, "value": 20},
#                         {"id": catalogue_category.properties[1].id, "value": False},
#                         {"id": catalogue_category.properties[2].id, "value": True},
#                     ],
#                 },
#             ),
#         )
#     catalogue_item_repository_mock.create.assert_not_called()
#     assert (
#         str(exc.value) == "Invalid value type for property with ID "
#         f"'{catalogue_category.properties[2].id}'. Expected type: string."
#     )
#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


# def test_create_with_invalid_value_type_for_number_property(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test creating a catalogue item with invalid value type for a number property.

#     Verify that the `create` method properly handles a catalogue item with invalid value type for a number catalogue
#     property, checks that the catalogue category exists and that it is a leaf category, checks that there are no missing
#     mandatory properties, finds invalid value type for a number property, and does not create the catalogue item.
#     """
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_CATEGORY_A_INFO,
#             "properties": add_ids_to_properties(
#                 None,
#                 FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#             ),
#         },
#     )

#     # Mock `get` to return the catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         catalogue_item_service.create(
#             CatalogueItemPostSchema(
#                 catalogue_category_id=catalogue_category.id,
#                 manufacturer_id=str(ObjectId()),
#                 **{
#                     **CATALOGUE_ITEM_A_INFO,
#                     "properties": [
#                         {"id": catalogue_category.properties[0].id, "value": "20"},
#                         {"id": catalogue_category.properties[1].id, "value": False},
#                         {"id": catalogue_category.properties[2].id, "value": "20x15x10"},
#                     ],
#                 },
#             )
#         )
#     catalogue_item_repository_mock.create.assert_not_called()
#     assert (
#         str(exc.value) == "Invalid value type for property with ID "
#         f"'{catalogue_category.properties[0].id}'. Expected type: number."
#     )
#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


# def test_create_with_with_invalid_value_type_for_boolean_property(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test creating a catalogue item with invalid value type for a boolean property.

#     Verify that the `create` method properly handles a catalogue item with invalid value type for a boolean property,
#     checks that the catalogue category exists and that it is a leaf category, checks that there are no missing
#     mandatory properties, finds invalid value type for a boolean property, and does not create the catalogue item.
#     """
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_CATEGORY_A_INFO,
#             "properties": add_ids_to_properties(
#                 None,
#                 FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#             ),
#         },
#     )

#     # Mock `get` to return the catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         catalogue_item_service.create(
#             CatalogueItemPostSchema(
#                 catalogue_category_id=catalogue_category.id,
#                 manufacturer_id=str(ObjectId()),
#                 **{
#                     **CATALOGUE_ITEM_A_INFO,
#                     "properties": [
#                         {"id": catalogue_category.properties[0].id, "value": 20},
#                         {"id": catalogue_category.properties[1].id, "value": "False"},
#                         {"id": catalogue_category.properties[2].id, "value": "20x15x10"},
#                     ],
#                 },
#             )
#         )
#     catalogue_item_repository_mock.create.assert_not_called()
#     assert (
#         str(exc.value) == "Invalid value type for property with ID "
#         f"'{catalogue_category.properties[1].id}'. Expected type: boolean."
#     )

#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category.id)


# def test_delete(catalogue_item_repository_mock, catalogue_item_service):
#     """
#     Test deleting a catalogue item.

#     Verify that the `delete` method properly handles the deletion of a catalogue item by ID.
#     """
#     catalogue_item_id = str(ObjectId())

#     catalogue_item_service.delete(catalogue_item_id)

#     catalogue_item_repository_mock.delete.assert_called_once_with(catalogue_item_id)


# def test_get(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
#     """
#     Test getting a catalogue item.

#     Verify that the `get` method properly handles the retrieval of a catalogue item by ID.
#     """
#     catalogue_item_id = str(ObjectId())
#     catalogue_item = MagicMock()

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, catalogue_item)

#     retrieved_catalogue_item = catalogue_item_service.get(catalogue_item_id)

#     catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)
#     assert retrieved_catalogue_item == catalogue_item


# def test_get_with_non_existent_id(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
#     """
#     Test getting a catalogue item with a non-existent ID.

#     Verify that the `get` method properly handles the retrieval of a catalogue item with a non-existent ID.
#     """
#     catalogue_item_id = str(ObjectId())

#     # Mock `get` to not return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, None)

#     retrieved_catalogue_item = catalogue_item_service.get(catalogue_item_id)

#     assert retrieved_catalogue_item is None
#     catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)


# def test_list(catalogue_item_repository_mock, catalogue_item_service):
#     """
#     Test listing catalogue items

#     Verify that the `list` method properly calls the repository function with any passed filters
#     """

#     catalogue_category_id = str(ObjectId())

#     result = catalogue_item_service.list(catalogue_category_id=catalogue_category_id)

#     catalogue_item_repository_mock.list.assert_called_once_with(catalogue_category_id)
#     assert result == catalogue_item_repository_mock.list.return_value


# def test_update_when_no_child_elements(
#     test_helpers,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test updating a catalogue item with child elements.

#     Verify that the `update` method properly handles the catalogue item to be updated when it doesn't have any
#     children.
#     """
#     # pylint: disable=duplicate-code
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "name": "Catalogue Item B",
#                 "description": "This is Catalogue Item B",
#                 "modified_time": catalogue_item.created_time,
#             },
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(name=catalogue_item.name, description=catalogue_item.description),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_when_has_child_elements(
#     test_helpers,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test updating a catalogue item with child elements.

#     Verify that the `update` method properly handles the catalogue item to be updated when it has children.
#     """
#     # pylint: disable=duplicate-code
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "name": "Catalogue Item B",
#                 "description": "This is Catalogue Item B",
#                 "modified_time": catalogue_item.created_time,
#             },
#         ),
#     )
#     # Mock so child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = True
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(name=catalogue_item.name, description=catalogue_item.description),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_with_non_existent_id(test_helpers, catalogue_item_repository_mock, catalogue_item_service):
#     """
#     Test updating a catalogue item with a non-existent ID.

#     Verify that the `update` method properly handles the catalogue category to be updated with a non-existent ID.
#     """
#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, None)

#     catalogue_item_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_item_service.update(catalogue_item_id, CatalogueItemPatchSchema(properties=[]))
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No catalogue item found with ID: {catalogue_item_id}"


# def test_update_change_catalogue_category_id_same_defined_properties_without_supplied_properties(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test moving a catalogue item to another catalogue category that has the same defined  when
#     no properties are supplied.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     current_catalogue_category_id = str(ObjectId())
#     current_properties = add_ids_to_properties(None, properties)
#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "catalogue_category_id": current_catalogue_category_id,
#                 "modified_time": catalogue_item.created_time,
#                 "properties": current_properties,
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return the new catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `get` to return the current catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=current_catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_C_INFO,
#                 "properties": add_ids_to_properties(current_properties, FULL_CATALOGUE_CATEGORY_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id, CatalogueItemPatchSchema(catalogue_category_id=catalogue_item.catalogue_category_id)
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_change_catalogue_category_id_same_defined_properties_with_supplied_properties(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test moving a catalogue item to another catalogue category that has the same defined properties when
#     properties are supplied.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     current_catalogue_category_id = str(ObjectId())
#     current_properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "catalogue_category_id": current_catalogue_category_id,
#                 "modified_time": catalogue_item.created_time,
#                 "properties": current_properties,
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return the new catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `get` to return the current catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=current_catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_C_INFO,
#                 "properties": add_ids_to_properties(current_properties, FULL_CATALOGUE_CATEGORY_A_INFO["properties"]),
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             properties=[{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties],
#         ),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_change_catalogue_category_id_different_defined_properties_without_supplied_properties(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test moving a catalogue item to another catalogue category that has different defined properties when
#     no properties are supplied.
#     """
#     catalogue_item_id = str(ObjectId())
#     catalogue_category_id = str(ObjectId())

#     current_catalogue_category_id = str(ObjectId())
#     current_properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=catalogue_item_id,
#             catalogue_category_id=current_catalogue_category_id,
#             manufacturer_id=str(ObjectId()),
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": current_properties,
#             },
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return the new catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     None,
#                     [
#                         {"name": "Property A", "type": "number", "unit": "m", "mandatory": False},
#                         *FULL_CATALOGUE_CATEGORY_A_INFO["properties"][1:],
#                     ],
#                 ),
#             },
#         ),
#     )
#     # pylint: enable=duplicate-code
#     # Mock `get` to return the current catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=current_catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_C_INFO,
#                 "properties": add_ids_to_properties(current_properties, FULL_CATALOGUE_CATEGORY_A_INFO["properties"]),
#             },
#         ),
#     )

#     with pytest.raises(InvalidActionError) as exc:
#         catalogue_item_service.update(
#             catalogue_item_id,
#             CatalogueItemPatchSchema(catalogue_category_id=catalogue_category_id),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == "Cannot move catalogue item to a category with different properties without "
#         "specifying the new properties"
#     )


# def test_update_change_catalogue_category_id_different_defined_properties_order_without_supplied_properties(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test moving a catalogue item to another catalogue category that has different defined
#     order when no properties are supplied.
#     """
#     catalogue_item_id = str(ObjectId())
#     catalogue_category_id = str(ObjectId())

#     current_catalogue_category_id = str(ObjectId())
#     current_properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=catalogue_item_id,
#             catalogue_category_id=current_catalogue_category_id,
#             manufacturer_id=str(ObjectId()),
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "properties": current_properties,
#             },
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return the new catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     None,
#                     [
#                         *FULL_CATALOGUE_CATEGORY_A_INFO["properties"][::-1],
#                     ],
#                 ),
#             },
#         ),
#     )
#     # pylint: enable=duplicate-code
#     # Mock `get` to return the current catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=current_catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_C_INFO,
#                 "properties": add_ids_to_properties(current_properties, FULL_CATALOGUE_CATEGORY_A_INFO["properties"]),
#             },
#         ),
#     )

#     with pytest.raises(InvalidActionError) as exc:
#         catalogue_item_service.update(
#             catalogue_item_id,
#             CatalogueItemPatchSchema(catalogue_category_id=catalogue_category_id),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == "Cannot move catalogue item to a category with different properties without "
#         "specifying the new properties"
#     )


# def test_update_change_catalogue_category_id_different_defined_properties_with_supplied_properties(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test moving a catalogue item to another catalogue category that has different defined properties when
#     properties are supplied.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     current_catalogue_category_id = str(ObjectId())
#     current_properties = add_ids_to_properties(None, [{"name": "Property A", "value": True, "unit": None}])
#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "catalogue_category_id": current_catalogue_category_id,
#                 "modified_time": catalogue_item.created_time,
#                 "properties": current_properties,
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return the new catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `get` to return the current catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=current_catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_C_INFO,
#                 "properties": add_ids_to_properties(
#                     current_properties,
#                     [{"name": "Property A", "type": "boolean", "unit": None, "mandatory": True}],
#                 ),
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             properties=[{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties],
#         ),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_with_non_existent_catalogue_category_id(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test updating a catalogue item with a non-existent catalogue category ID.
#     """
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, catalogue_item)
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to not return a catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, None)

#     catalogue_category_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(catalogue_category_id=catalogue_category_id),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"


# def test_update_with_existent_manufacturer_id_when_has_no_child_elements(
#     test_helpers,
#     catalogue_item_repository_mock,
#     manufacturer_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test updating manufacturer id to an existing id when the catalogue item has no child elements
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "manufacturer_id": str(ObjectId()),
#                 "modified_time": catalogue_item.created_time,
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a manufacturer
#     test_helpers.mock_get(
#         manufacturer_repository_mock,
#         ManufacturerOut(id=catalogue_item.manufacturer_id, **FULL_MANUFACTURER_INFO),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(manufacturer_id=catalogue_item.manufacturer_id),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_with_existent_manufacturer_id_when_has_child_elements(
#     test_helpers,
#     catalogue_item_repository_mock,
#     manufacturer_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test updating manufacturer id to an existing id when the catalogue item has child elements
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "manufacturer_id": str(ObjectId()),
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = True
#     # Mock `get` to return a manufacturer
#     test_helpers.mock_get(
#         manufacturer_repository_mock,
#         ManufacturerOut(id=catalogue_item.manufacturer_id, **FULL_MANUFACTURER_INFO),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     with pytest.raises(ChildElementsExistError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(manufacturer_id=catalogue_item.manufacturer_id),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"Catalogue item with ID {catalogue_item.id} has child elements and cannot be updated"


# def test_update_with_non_existent_manufacturer_id(
#     test_helpers,
#     manufacturer_repository_mock,
#     catalogue_item_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test updating a catalogue item with a non-existent manufacturer id
#     """
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, catalogue_item)
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to not return a manufacturer
#     test_helpers.mock_get(manufacturer_repository_mock, None)

#     manufacturer_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(manufacturer_id=manufacturer_id),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No manufacturer found with ID: {manufacturer_id}"


# def test_update_change_catalogue_category_id_non_leaf_catalogue_category(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test moving a catalogue item to a non-leaf catalogue category.
#     """
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, catalogue_item)
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     catalogue_category_id = str(ObjectId())
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(id=catalogue_category_id, **FULL_CATALOGUE_CATEGORY_B_INFO),
#     )

#     with pytest.raises(NonLeafCatalogueCategoryError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(catalogue_category_id=catalogue_category_id),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == "Cannot add catalogue item to a non-leaf catalogue category"


# def test_update_with_obsolete_replacement_catalogue_item_id(
#     test_helpers,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test updating a catalogue item with an obsolete replacement catalogue item ID.
#     """
#     obsolete_replacement_catalogue_item_id = str(ObjectId())
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "is_obsolete": True,
#             "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=catalogue_item.id,
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "modified_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a replacement catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             id=obsolete_replacement_catalogue_item_id,
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "name": "Catalogue Item B",
#                 "description": "This is Catalogue Item B",
#                 "properties": properties,
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(
#             is_obsolete=True, obsolete_replacement_catalogue_item_id=obsolete_replacement_catalogue_item_id
#         ),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "is_obsolete": True,
#                 "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_with_non_existent_obsolete_replacement_catalogue_item_id(
#     test_helpers, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test updating a catalogue item with a non-existent obsolete replacement catalogue item ID.
#     """
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, catalogue_item)
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to not return a replacement catalogue item
#     test_helpers.mock_get(catalogue_item_repository_mock, None)

#     obsolete_replacement_catalogue_item_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(
#                 is_obsolete=True, obsolete_replacement_catalogue_item_id=obsolete_replacement_catalogue_item_id
#             ),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No catalogue item found with ID: {obsolete_replacement_catalogue_item_id}"
#     catalogue_item_repository_mock.get.assert_has_calls(
#         [call(catalogue_item.id), call(obsolete_replacement_catalogue_item_id)]
#     )


# def test_update_add_non_mandatory_property(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test adding a non-mandatory property and a value.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "modified_time": catalogue_item.created_time,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_ITEM_A_INFO["properties"][-2:],
#                 ),
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(
#             properties=[{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties]
#         ),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_remove_non_mandatory_property(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test removing a non-mandatory property and its value.
#     """
#     properties = add_ids_to_properties(
#         None, [{"name": "Property A", "value": None, "unit": "mm"}, *FULL_CATALOGUE_ITEM_A_INFO["properties"][-2:]]
#     )
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "modified_time": catalogue_item.created_time,
#                 "properties": add_ids_to_properties(properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(
#             properties=[{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties[-2:]]
#         ),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_remove_mandatory_property(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     catalogue_item_service,
# ):
#     """
#     Test removing a mandatory property and its value.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         catalogue_item,
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     with pytest.raises(MissingMandatoryProperty) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(
#                 properties=[{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties[:2]]
#             ),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"Missing mandatory property with ID: '{catalogue_item.properties[2].id}'"


# def test_update_change_property_value(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_item_service,
# ):
#     """
#     Test updating a value of a property.
#     """
#     properties = add_ids_to_properties(
#         None, [{"name": "Property A", "value": 1, "unit": "mm"}, *FULL_CATALOGUE_ITEM_A_INFO["properties"][-2:]]
#     )
#     # pylint: disable=duplicate-code
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "created_time": FULL_CATALOGUE_ITEM_A_INFO["created_time"] - timedelta(days=5),
#             "properties": properties,
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         CatalogueItemOut(
#             **{
#                 **catalogue_item.model_dump(),
#                 "modified_time": catalogue_item.created_time,
#                 "properties": add_ids_to_properties(properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#             }
#         ),
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     updated_catalogue_item = catalogue_item_service.update(
#         catalogue_item.id,
#         CatalogueItemPatchSchema(
#             properties=[{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties]
#         ),
#     )

#     catalogue_item_repository_mock.update.assert_called_once_with(
#         catalogue_item.id,
#         CatalogueItemIn(
#             catalogue_category_id=catalogue_item.catalogue_category_id,
#             manufacturer_id=catalogue_item.manufacturer_id,
#             **{
#                 **FULL_CATALOGUE_ITEM_A_INFO,
#                 "created_time": catalogue_item.created_time,
#                 "properties": properties,
#             },
#         ),
#     )
#     assert updated_catalogue_item == catalogue_item


# def test_update_change_value_for_string_property_invalid_type(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test changing the value of a string property to an invalid type.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         catalogue_item,
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     properties = [{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties]
#     properties[2]["value"] = True
#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(properties=properties),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == f"Invalid value type for property with ID '{catalogue_item.properties[2].id}'. "
#         "Expected type: string."
#     )


# def test_update_change_value_for_number_property_invalid_type(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test changing the value of a number property to an invalid type.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         catalogue_item,
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     properties = [{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties]
#     properties[0]["value"] = "20"
#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(properties=properties),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == f"Invalid value type for property with ID '{catalogue_item.properties[0].id}'. "
#         "Expected type: number."
#     )


# def test_update_change_value_for_boolean_property_invalid_type(
#     test_helpers, catalogue_category_repository_mock, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test changing the value of a boolean property to an invalid type.
#     """
#     properties = add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"])
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": properties,
#         },
#     )

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         catalogue_item,
#     )
#     # Mock so no child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_item.catalogue_category_id,
#             **{
#                 **FULL_CATALOGUE_CATEGORY_A_INFO,
#                 "properties": add_ids_to_properties(
#                     properties,
#                     FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
#                 ),
#             },
#         ),
#     )

#     properties = [{"id": prop.id, "value": prop.value} for prop in catalogue_item.properties]
#     properties[1]["value"] = "False"
#     with pytest.raises(InvalidPropertyTypeError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(properties=properties),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value) == f"Invalid value type for property with ID '{catalogue_item.properties[1].id}'. "
#         "Expected type: boolean."
#     )


# def test_update_properties_when_has_child_elements(
#     test_helpers, catalogue_item_repository_mock, catalogue_item_service
# ):
#     """
#     Test updating a catalogue item's properties when it has child elements.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_item = CatalogueItemOut(
#         id=str(ObjectId()),
#         catalogue_category_id=str(ObjectId()),
#         manufacturer_id=str(ObjectId()),
#         **{
#             **FULL_CATALOGUE_ITEM_A_INFO,
#             "properties": add_ids_to_properties(None, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
#         },
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue item
#     test_helpers.mock_get(
#         catalogue_item_repository_mock,
#         catalogue_item.model_dump(),
#     )
#     # Mock so child elements found
#     catalogue_item_repository_mock.has_child_elements.return_value = True
#     # Mock `update` to return the updated catalogue item
#     test_helpers.mock_update(catalogue_item_repository_mock, catalogue_item)

#     with pytest.raises(ChildElementsExistError) as exc:
#         catalogue_item_service.update(
#             catalogue_item.id,
#             CatalogueItemPatchSchema(properties=[]),
#         )
#     catalogue_item_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"Catalogue item with ID {catalogue_item.id} has child elements and cannot be updated"
