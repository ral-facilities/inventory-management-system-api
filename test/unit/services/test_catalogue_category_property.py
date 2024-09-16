"""
Unit tests for the `CatalogueCategoryPropertyService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code

from test.mock_data import (
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    UNIT_IN_DATA_MM,
)
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW, BaseCatalogueServiceDSL, ServiceTestHelpers
from typing import Optional
from unittest.mock import ANY, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import InvalidActionError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import (
    AllowedValues,
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    CatalogueCategoryPropertyIn,
    CatalogueCategoryPropertyOut,
)
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPropertyPatchSchema,
    CatalogueCategoryPropertyPostSchema,
)
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.catalogue_category_property import CatalogueCategoryPropertyService


class CatalogueCategoryPropertyServiceDSL(BaseCatalogueServiceDSL):
    """Base class for `CatalogueCategoryPropertyService` unit tests."""

    wrapped_utils: Mock
    mock_mongodb_client: Mock
    mock_catalogue_category_repository: Mock
    mock_catalogue_item_repository: Mock
    mock_item_repository: Mock
    mock_unit_repository: Mock
    catalogue_category_property_service: CatalogueCategoryPropertyService

    # pylint:disable=too-many-arguments
    @pytest.fixture(autouse=True)
    def setup(
        self,
        catalogue_category_repository_mock,
        catalogue_item_repository_mock,
        item_repository_mock,
        unit_repository_mock,
        catalogue_category_property_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""

        self.mock_catalogue_category_repository = catalogue_category_repository_mock
        self.mock_catalogue_item_repository = catalogue_item_repository_mock
        self.mock_item_repository = item_repository_mock
        self.mock_unit_repository = unit_repository_mock
        self.catalogue_category_property_service = catalogue_category_property_service

        with patch(
            "inventory_management_system_api.services.catalogue_category_property.mongodb_client"
        ) as mocked_mongo_db_client:
            self.mock_mongodb_client = mocked_mongo_db_client

            with patch(
                "inventory_management_system_api.services.catalogue_category_property.utils", wraps=utils
            ) as wrapped_utils:
                self.wrapped_utils = wrapped_utils
                yield


class CreateDSL(CatalogueCategoryPropertyServiceDSL):
    """Base class for `create` tests."""

    _catalogue_category_id: str
    _catalogue_category_property_post: CatalogueCategoryPropertyPostSchema
    _catalogue_category_out: Optional[CatalogueCategoryOut]
    _expected_catalogue_category_property_in: CatalogueCategoryPropertyIn
    _expected_catalogue_category_property_out: CatalogueCategoryPropertyOut
    _expected_property_in: PropertyIn
    _created_catalogue_category_property: CatalogueCategoryPropertyOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        catalogue_category_property_data: dict,
        catalogue_category_in_data: Optional[dict] = None,
        unit_in_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param catalogue_category_property_data: Dictionary containing the basic catalogue category property data as
                                        would be required for a `CatalogueCategoryPropertyPostSchema` but with any
                                        `unit_id`'s replaced by the `unit` value in its properties as the IDs will be
                                        added automatically.
        :param catalogue_category_in_data: Either `None` or a dictionary containing the catalogue category data as would
                                           be required for a `CatalogueCategoryIn` database model.
        :param unit_in_data: Either `None` or a dictionary containing the unit data as would be required for a `UnitIn`
                             database model. These values will be used for the unit look up if required by the given
                             catalogue category property.
        """

        self._catalogue_category_id = str(ObjectId())

        # Catalogue category
        self._catalogue_category_out = (
            CatalogueCategoryOut(
                **{
                    **CatalogueCategoryIn(**catalogue_category_in_data).model_dump(by_alias=True),
                    "_id": self._catalogue_category_id,
                }
            )
            if catalogue_category_in_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._catalogue_category_out)

        self._expected_catalogue_category_property_in = (
            self.construct_catalogue_category_properties_in_and_post_with_ids([catalogue_category_property_data])[0][0]
        )

        # Unit
        unit = None
        unit_id = None
        if "unit" in catalogue_category_property_data and catalogue_category_property_data["unit"] is not None:
            unit_in = UnitIn(**unit_in_data) if unit_in_data else None
            unit = catalogue_category_property_data["unit"]
            unit_id = self.unit_value_id_dict[unit]

            ServiceTestHelpers.mock_get(
                self.mock_unit_repository, UnitOut(**unit_in.model_dump(), id=unit_id) if unit_in else None
            )

        self._catalogue_category_property_post = CatalogueCategoryPropertyPostSchema(
            **{**catalogue_category_property_data, "unit_id": unit_id}
        )

        self._expected_catalogue_category_property_out = CatalogueCategoryPropertyOut(
            **self._expected_catalogue_category_property_in.model_dump(),
        )

        self._expected_property_in = PropertyIn(
            id=str(self._expected_catalogue_category_property_in.id),
            name=self._expected_catalogue_category_property_in.name,
            value=self._catalogue_category_property_post.default_value,
            unit=unit,
            unit_id=unit_id,
        )

        self.mock_catalogue_category_repository.create_property.return_value = (
            self._expected_catalogue_category_property_out
        )

    def call_create(self) -> None:
        """Calls the `CatalogueCategoryPropertyService` `create` method with the appropriate data from a prior call to
        `mock_create`."""

        self._created_catalogue_category_property = self.catalogue_category_property_service.create(
            self._catalogue_category_id, self._catalogue_category_property_post
        )

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryPropertyService` `create` method with the appropriate data from a prior call to
        `mock_create` while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_property_service.create(
                self._catalogue_category_id, self._catalogue_category_property_post
            )
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        # This is the get for the catalogue category
        self.mock_catalogue_category_repository.get.assert_called_once_with(self._catalogue_category_id)

        # This is the properties duplicate check
        self.wrapped_utils.check_duplicate_property_names.assert_called_with(
            self._catalogue_category_out.properties + [self._catalogue_category_property_post]
        )

        # Session/Transaction
        expected_session = self.mock_mongodb_client.start_session.return_value.__enter__.return_value
        expected_session.start_transaction.assert_called_once()

        # Catalogue category

        # To assert with property IDs we must compare as dicts and use ANY here as otherwise the object ids will always
        # be different
        self.mock_catalogue_category_repository.create_property.assert_called_with(
            self._catalogue_category_id, ANY, session=expected_session
        )
        actual_catalogue_category_property_in = self.mock_catalogue_category_repository.create_property.call_args_list[
            0
        ][0][1]
        assert isinstance(actual_catalogue_category_property_in, CatalogueCategoryPropertyIn)
        assert actual_catalogue_category_property_in.model_dump() == {
            **self._expected_catalogue_category_property_in.model_dump(),
            "id": ANY,
        }

        # Catalogue items
        self._expected_property_in.id = actual_catalogue_category_property_in.id
        self.mock_catalogue_item_repository.insert_property_to_all_matching.assert_called_once_with(
            self._catalogue_category_id, self._expected_property_in, session=expected_session
        )

        # Items
        self.mock_catalogue_item_repository.list_ids.assert_called_once_with(
            self._catalogue_category_id, session=expected_session
        )
        self.mock_item_repository.insert_property_to_all_in.assert_called_once_with(
            self.mock_catalogue_item_repository.list_ids.return_value,
            self._expected_property_in,
            session=expected_session,
        )

        assert self._created_catalogue_category_property == self._expected_catalogue_category_property_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_category_repository.create_property.assert_not_called()
        self.mock_catalogue_item_repository.insert_property_to_all_matching.assert_not_called()
        self.mock_item_repository.insert_property_to_all_in.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category property."""

    def test_create_non_mandatory_without_default_value(self):
        """Test creating a non-mandatory property without a default value provided."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_create()
        self.check_create_success()

    def test_create_non_mandatory_with_default_value(self):
        """Test creating a non-mandatory property with a default value provided."""

        self.mock_create(
            {**CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY, "default_value": 20},
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_create()
        self.check_create_success()

    def test_create_mandatory_without_default_value(self):
        """Test creating a mandatory property without a default value provided."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_create_expecting_error(InvalidActionError)
        self.check_create_failed_with_exception("Cannot add a mandatory property without a default value")

    def test_create_mandatory_with_default_value(self):
        """Test creating a mandatory property without a default value provided."""

        self.mock_create(
            {**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY, "default_value": True},
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_unit(self):
        """Test creating a property with a unit provided."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            unit_in_data=UNIT_IN_DATA_MM,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_unit_id(self):
        """Test creating a property with a non-existent unit ID."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            unit_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No unit found with ID: {self.unit_value_id_dict['mm']}")

    def test_create_with_non_existent_catalogue_category_id(self):
        """Test creating a property with a non-existent catalogue category ID."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
            catalogue_category_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No catalogue category found with ID: {self._catalogue_category_id}")

    def test_create_with_non_leaf_catalogue_category(self):
        """Test creating a property with a non-leaf catalogue category."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_create_expecting_error(InvalidActionError)
        self.check_create_failed_with_exception("Cannot add a property to a non-leaf catalogue category")


# pylint:disable=too-many-locals
# pylint:disable=too-many-arguments

# UNIT_A = {
#     "value": "mm",
#     "code": "mm",
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }


# @patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
# def test_update(
#     mongodb_client_mock,
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method properly handles the property to be created and propagates the changes
#     downwards through catalogue items (This test supplies both name and allowed_values)
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
#     )
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100]),
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category to one without a property with the same name
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

#     # Start of transaction
#     session = mongodb_client_mock.start_session.return_value.__enter__.return_value
#     catalogue_category_repository_mock.update_property.assert_called_once_with(
#         catalogue_category_id,
#         property_id,
#         CatalogueCategoryPropertyIn(**{**stored_property.model_dump(), **property_patch.model_dump()}),
#         session=session,
#     )

#     # Catalogue items update
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_called_once_with(
#         property_id, property_patch.name, session=session
#     )

#     # Items update
#     item_repository_mock.update_names_of_all_properties_with_id.assert_called_once_with(
#         property_id, property_patch.name, session=session
#     )

#     # Final output
#     assert updated_property == catalogue_category_repository_mock.update_property.return_value


# @patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
# def test_update_category_only(
#     mongodb_client_mock,
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method properly handles an update that doesn't require any propagation through
#     catalogue items and items (in this case only modifying the allowed_values)
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
#     )
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100]),
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category to one without a property with the same name
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

#     # Start of transaction
#     session = mongodb_client_mock.start_session.return_value.__enter__.return_value
#     catalogue_category_repository_mock.update_property.assert_called_once_with(
#         catalogue_category_id,
#         property_id,
#         CatalogueCategoryPropertyIn(
#             **{**stored_property.model_dump(), **property_patch.model_dump(exclude_unset=True)}
#         ),
#         session=session,
#     )

#     # Ensure changes aren't propagated
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()

#     # Final output
#     assert updated_property == catalogue_category_repository_mock.update_property.return_value


# @patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
# def test_update_with_no_changes_allowed_values_none(
#     mongodb_client_mock,
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method properly handles the property to be created and propagates the changes
#     downwards through catalogue items (in this case passing allowed_values as None when the database
#     model also uses None)
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(allowed_values=None)
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=None,
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category to one without a property with the same name
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

#     # Start of transaction
#     session = mongodb_client_mock.start_session.return_value.__enter__.return_value
#     catalogue_category_repository_mock.update_property.assert_called_once_with(
#         catalogue_category_id,
#         property_id,
#         CatalogueCategoryPropertyIn(
#             **{**stored_property.model_dump(), **property_patch.model_dump(exclude_unset=True)}
#         ),
#         session=session,
#     )

#     # Ensure changes aren't propagated
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()

#     # Final output
#     assert updated_property == catalogue_category_repository_mock.update_property.return_value


# def test_update_with_missing_catalogue_category(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method raises a MissingRecordError when the catalogue category with the given
#     catalogue_category_id doesn't exist
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
#     )
#     stored_catalogue_category = None

#     # Mock the stored catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
#     assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"

#     # Ensure no updates actually called
#     catalogue_category_repository_mock.update_property.assert_not_called()
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


# def test_update_with_missing_property(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method raises a MissingRecordError when the property with the given
#     property_id doesn't exist
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
#     )
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=str(ObjectId()),
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100]),
#     )
#     # pylint: enable=duplicate-code
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
#     assert str(exc.value) == f"No property found with ID: {property_id}"

#     # Ensure no updates actually called
#     catalogue_category_repository_mock.update_property.assert_not_called()
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


# def test_update_allowed_values_from_none_to_value(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
#     from None to a value
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
#     )
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=None,
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     with pytest.raises(InvalidActionError) as exc:
#         catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
#     assert str(exc.value) == "Cannot add allowed_values to an existing property"

#     # Ensure no updates actually called
#     catalogue_category_repository_mock.update_property.assert_not_called()
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


# def test_update_allowed_values_from_value_to_none(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
#     from a value to None
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(name="Property Name", allowed_values=None)
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100]),
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     with pytest.raises(InvalidActionError) as exc:
#         catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
#     assert str(exc.value) == "Cannot remove allowed_values from an existing property"

#     # Ensure no updates actually called
#     catalogue_category_repository_mock.update_property.assert_not_called()
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


# def test_update_allowed_values_removing_element(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
#     to have one fewer element
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000]}
#     )
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100, 500, 1000, 2000]),
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     with pytest.raises(InvalidActionError) as exc:
#         catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
#     assert (
#         str(exc.value)
#         == "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
#     )

#     # Ensure no updates actually called
#     catalogue_category_repository_mock.update_property.assert_not_called()
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


# def test_update_allowed_values_modifying_element(
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method raises a InvalidActionError when attempting to change a properties' allowed_values
#     by changing one element
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         name="Property Name", allowed_values={"type": "list", "values": [100, 500, 1000, 2000]}
#     )
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100, 500, 1200, 2000]),
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     with pytest.raises(InvalidActionError) as exc:
#         catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)
#     assert (
#         str(exc.value)
#         == "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
#     )

#     # Ensure no updates actually called
#     catalogue_category_repository_mock.update_property.assert_not_called()
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()


# @patch("inventory_management_system_api.services.catalogue_category_property.mongodb_client")
# def test_update_adding_allowed_values(
#     mongodb_client_mock,
#     test_helpers,
#     catalogue_category_repository_mock,
#     catalogue_item_repository_mock,
#     item_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_property_service,
# ):
#     """
#     Test updating a property at the catalogue category level

#     Verify that the `update` method allows an allowed_values list to be extended
#     """
#     catalogue_category_id = str(ObjectId())
#     property_id = str(ObjectId())
#     property_patch = CatalogueCategoryPropertyPatchSchema(
#         allowed_values={"type": "list", "values": [100, 500, 1000, 2000, 3000, 4000]}
#     )
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     stored_property = CatalogueCategoryPropertyOut(
#         id=property_id,
#         name="Property A",
#         type="number",
#         unit_id=unit.id,
#         unit=unit.value,
#         mandatory=True,
#         allowed_values=AllowedValues(type="list", values=[100]),
#     )
#     stored_catalogue_category = CatalogueCategoryOut(
#         id=catalogue_category_id,
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[stored_property],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock the stored catalogue category to one without a property with the same name
#     test_helpers.mock_get(catalogue_category_repository_mock, stored_catalogue_category)

#     updated_property = catalogue_category_property_service.update(catalogue_category_id, property_id, property_patch)

#     # Start of transaction
#     session = mongodb_client_mock.start_session.return_value.__enter__.return_value
#     catalogue_category_repository_mock.update_property.assert_called_once_with(
#         catalogue_category_id,
#         property_id,
#         CatalogueCategoryPropertyIn(
#             **{**stored_property.model_dump(), **property_patch.model_dump(exclude_unset=True)}
#         ),
#         session=session,
#     )

#     # Ensure changes aren't propagated
#     catalogue_item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()
#     item_repository_mock.update_names_of_all_properties_with_id.assert_not_called()

#     # Final output
#     assert updated_property == catalogue_category_repository_mock.update_property.return_value
