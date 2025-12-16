"""
Unit tests for the `CatalogueCategoryPropertyService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code

from test.mock_data import (
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY,
    UNIT_IN_DATA_MM,
)
from test.unit.services.conftest import BaseCatalogueServiceDSL, ServiceTestHelpers
from typing import Optional
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import InvalidActionError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import (
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
    mock_start_session_transaction: Mock
    mock_catalogue_category_repository: Mock
    mock_catalogue_item_repository: Mock
    mock_item_repository: Mock
    mock_unit_repository: Mock
    catalogue_category_property_service: CatalogueCategoryPropertyService

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
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
            "inventory_management_system_api.services.catalogue_category_property.start_session_transaction"
        ) as mocked_start_session_transaction:
            self.mock_start_session_transaction = mocked_start_session_transaction

            with patch(
                "inventory_management_system_api.services.catalogue_category_property.utils", wraps=utils
            ) as wrapped_utils:
                self.wrapped_utils = wrapped_utils
                yield


# pylint:disable=too-many-instance-attributes
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
        self.mock_start_session_transaction.assert_called_once_with("adding property")
        expected_session = self.mock_start_session_transaction.return_value.__enter__.return_value

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
        self.check_create_failed_with_exception(f"No unit found with ID '{self.unit_value_id_dict['mm']}'")

    def test_create_with_non_existent_catalogue_category_id(self):
        """Test creating a property with a non-existent catalogue category ID."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
            catalogue_category_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No catalogue category found with ID '{self._catalogue_category_id}'")

    def test_create_with_non_leaf_catalogue_category(self):
        """Test creating a property with a non-leaf catalogue category."""

        self.mock_create(
            CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
            catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_create_expecting_error(InvalidActionError)
        self.check_create_failed_with_exception("Cannot add a property to a non-leaf catalogue category")


# pylint:disable=too-many-instance-attributes
class UpdateDSL(CatalogueCategoryPropertyServiceDSL):
    """Base class for `update` tests."""

    _catalogue_category_id: str
    _stored_catalogue_category_in: Optional[CatalogueCategoryIn]
    _stored_catalogue_category_out: Optional[CatalogueCategoryOut]
    _stored_catalogue_category_property_out: Optional[CatalogueCategoryPropertyOut]
    _catalogue_category_property_patch: CatalogueCategoryPropertyPatchSchema
    _expected_catalogue_category_property_in: CatalogueCategoryPropertyIn
    _expected_catalogue_category_property_out: MagicMock
    _updated_catalogue_category_property_id: str
    _updated_catalogue_category_property: MagicMock
    _update_exception: pytest.ExceptionInfo
    _user_authorised: bool

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def mock_update(
        self,
        catalogue_category_property_id: str,
        catalogue_category_property_update_data: dict,
        stored_catalogue_category_property_in_data: Optional[dict],
        catalogue_category_exists: bool = True,
        user_is_authorised=False,
        unit_in_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `update` service method.

        :param catalogue_category_property_id: ID of the catalogue category property that will be obtained.
        :param catalogue_category_property_update_data: Dictionary containing the basic patch data as would be required
                                           for a `CatalogueCategoryPropertyPatchSchema` but with any unit_id's replaced
                                           by the unit value in its properties as the IDs will be added automatically.

        :param stored_catalogue_category_property_in_data: Either `None` or a dictionary containing the catalogue
                                                category property data for the existing stored catalogue category
                                                property as would be required for a `CatalogueCategoryPropertyIn`
                                                database model.
        :param catalogue_category_exists: Boolean of whether the catalogue category being updated should exist or not.
        :param user_is_authorised: Whether the request is authorised to edit a property's unit.
        :param unit_in_data: Either `None` or a dictionary containing the unit data as would be required for a `UnitIn`
                             database model. These values will be used for the unit look up if required by the given
                             catalogue category property update data.
        """

        self._catalogue_category_id = str(ObjectId())

        self._user_authorised = user_is_authorised

        # Use a predefined catalogue category when it should exist with a single property to be overridden
        self._stored_catalogue_category_in = (
            CatalogueCategoryIn(
                **CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            )
            if catalogue_category_exists
            else None
        )

        self._stored_catalogue_category_property_out = (
            CatalogueCategoryPropertyOut(
                **{
                    **CatalogueCategoryPropertyIn(**stored_catalogue_category_property_in_data).model_dump(),
                    "id": catalogue_category_property_id,
                }
            )
            if stored_catalogue_category_property_in_data
            else None
        )
        self._stored_catalogue_category_out = (
            CatalogueCategoryOut(
                **{
                    **self._stored_catalogue_category_in.model_dump(by_alias=True),
                    "properties": (
                        [self._stored_catalogue_category_property_out]
                        if stored_catalogue_category_property_in_data
                        else []
                    ),
                },
                id=self._catalogue_category_id,
            )
            if catalogue_category_exists
            else None
        )

        ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._stored_catalogue_category_out)

        # Updated catalogue item
        self._expected_catalogue_category_property_out = MagicMock()
        self.mock_catalogue_category_repository.update_property.return_value = (
            self._expected_catalogue_category_property_out
        )

        # Unit
        unit_id = None
        if "unit" in catalogue_category_property_update_data:
            if catalogue_category_property_update_data["unit"] is not None:
                unit_in = UnitIn(**unit_in_data) if unit_in_data else None
                unit_id = str(ObjectId())

                ServiceTestHelpers.mock_get(
                    self.mock_unit_repository, UnitOut(**unit_in.model_dump(), id=unit_id) if unit_in else None
                )

            catalogue_category_property_update_data = {**catalogue_category_property_update_data, "unit_id": unit_id}

        # Patch schema
        self._catalogue_category_property_patch = CatalogueCategoryPropertyPatchSchema(
            **catalogue_category_property_update_data,
        )

        # Expected input for the repository
        if self._stored_catalogue_category_property_out:
            self._expected_catalogue_category_property_in = CatalogueCategoryPropertyIn(
                **{
                    **self._stored_catalogue_category_property_out.model_dump(),
                    **catalogue_category_property_update_data,
                }
            )

    def call_update(self, catalogue_category_property_id: str) -> None:
        """
        Calls the `CatalogueCategoryPropertyService` `update` method with the appropriate data from a prior call to
        `mock_update`.

        :param catalogue_category_property_id: ID of the catalogue category property to be updated.
        """

        self._updated_catalogue_category_property_id = catalogue_category_property_id
        self._updated_catalogue_category_property = self.catalogue_category_property_service.update(
            self._catalogue_category_id,
            catalogue_category_property_id,
            self._catalogue_category_property_patch,
            self._user_authorised,
        )

    def call_update_expecting_error(self, catalogue_category_property_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryPropertyService` `update` method with the appropriate data from a prior call to
        `mock_update` while expecting an error to be raised.

        :param catalogue_category_property_id: D of the catalogue category property to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_property_service.update(
                self._catalogue_category_id,
                catalogue_category_property_id,
                self._catalogue_category_property_patch,
                self._user_authorised,
            )
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        self.mock_catalogue_category_repository.get.assert_called_once_with(self._catalogue_category_id)

        updating_name = (
            self._catalogue_category_property_patch.name is not None
            and self._stored_catalogue_category_out.name != self._catalogue_category_property_patch.name
        )

        if updating_name:
            modified_catalogue_category_out = CatalogueCategoryPropertyOut(
                **self._stored_catalogue_category_property_out.model_dump()
            )
            modified_catalogue_category_out.name = self._catalogue_category_property_patch.name
            self.wrapped_utils.check_duplicate_property_names.assert_called_once_with([modified_catalogue_category_out])

        updating_unit = (
            self._stored_catalogue_category_property_out.unit_id != self._catalogue_category_property_patch.unit_id
        )

        if updating_unit and self._stored_catalogue_category_property_out.unit_id is not None:
            self.mock_unit_repository.get.assert_called_once_with(self._stored_catalogue_category_property_out.unit_id)

        # Session/Transaction
        self.mock_start_session_transaction.assert_called_once_with("updating property")
        expected_session = self.mock_start_session_transaction.return_value.__enter__.return_value

        # Catalogue category
        self.mock_catalogue_category_repository.update_property.assert_called_once_with(
            self._catalogue_category_id,
            self._updated_catalogue_category_property_id,
            self._expected_catalogue_category_property_in,
            session=expected_session,
        )

        if updating_name or updating_unit:
            unit_data = (
                {
                    "unit_id": self._catalogue_category_property_patch.unit_id,
                    "unit": self._expected_catalogue_category_property_in.unit,
                }
                if updating_unit
                else None
            )

            # Catalogue items
            # pylint:disable=line-too-long
            self.mock_catalogue_item_repository.update_names_and_units_of_all_properties_with_id.assert_called_once_with(
                self._updated_catalogue_category_property_id,
                self._catalogue_category_property_patch.name,
                unit_data,
                session=expected_session,
            )

            # Items
            self.mock_item_repository.update_names_and_units_of_all_properties_with_id.assert_called_once_with(
                self._updated_catalogue_category_property_id,
                self._catalogue_category_property_patch.name,
                unit_data,
                session=expected_session,
            )
        else:
            self.mock_catalogue_item_repository.update_names_and_units_of_all_properties_with_id.assert_not_called()
            self.mock_item_repository.update_names_and_units_of_all_properties_with_id.assert_not_called()

        assert self._updated_catalogue_category_property == self._expected_catalogue_category_property_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_category_repository.update_property.assert_not_called()
        self.mock_catalogue_item_repository.update_names_and_units_of_all_properties_with_id.assert_not_called()
        self.mock_item_repository.update_names_and_units_of_all_properties_with_id.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue category property."""

    def test_update_all_fields(self):
        """Test updating all allowable fields of a catalogue category property."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={
                "name": "New name",
                "unit": UNIT_IN_DATA_MM["value"],
                "allowed_values": {
                    "type": "list",
                    "values": [
                        *CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST[
                            "allowed_values"
                        ]["values"],
                        4,
                    ],
                },
            },
            stored_catalogue_category_property_in_data=(
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
            ),
            user_is_authorised=True,
            unit_in_data=UNIT_IN_DATA_MM,
        )
        self.call_update(catalogue_category_property_id)
        self.check_update_success()

    def test_update_name_only(self):
        """Test updating only the name of catalogue category property."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"name": "New name"},
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
        )
        self.call_update(catalogue_category_property_id)
        self.check_update_success()

    def test_update_unit_only(self):
        """Test updating only the `unit_id` of a catalogue category property."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"unit": UNIT_IN_DATA_MM["value"]},
            # pylint:disable=line-too-long
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
            user_is_authorised=True,
            unit_in_data=UNIT_IN_DATA_MM,
        )

        self.call_update(catalogue_category_property_id)
        self.check_update_success()

    def test_update_unit_to_none(self):
        """Test updating only the `unit_id` of a property to `None`"""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"unit": None},
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_MANDATORY,
            user_is_authorised=True,
            unit_in_data=None,
        )

        self.call_update(catalogue_category_property_id)
        self.check_update_success()

    def test_update_unit_when_not_authorised(self):
        """Test updating the `unit_id` of a property when the user is not authorised"""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"unit": UNIT_IN_DATA_MM["value"]},
            # pylint:disable=line-too-long
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
            user_is_authorised=False,
        )

        self.call_update_expecting_error(catalogue_category_property_id, InvalidActionError)
        self.check_update_failed_with_exception("You are not able to change the unit of a property")

    def test_update_allowed_values_to_none_no_changes(self):
        """Test updating the `allowed_values` of a property to `None` when it already is."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"allowed_values": None},
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
        )
        self.call_update(catalogue_category_property_id)
        self.check_update_success()

    def test_update_allowed_values_from_none_to_value(self):
        """Test updating the `allowed_values` of a property to a value when it's currently `None`."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={
                "allowed_values": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST[
                    "allowed_values"
                ]
            },
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY,
        )
        self.call_update_expecting_error(catalogue_category_property_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot add allowed_values to an existing property")

    def test_update_allowed_values_to_none(self):
        """Test updating the `allowed_values` of a property to `None` when it currently has a value."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"allowed_values": None},
            stored_catalogue_category_property_in_data=(
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
            ),
        )
        self.call_update_expecting_error(catalogue_category_property_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot remove allowed_values from an existing property")

    def test_update_allowed_values_list_adding_element(self):
        """Test updating the `allowed_values` list of a property to have one more element than it already has."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={
                "allowed_values": {
                    "type": "list",
                    "values": [
                        *CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST[
                            "allowed_values"
                        ]["values"],
                        42,
                    ],
                },
            },
            stored_catalogue_category_property_in_data=(
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
            ),
        )
        self.call_update(catalogue_category_property_id)
        self.check_update_success()

    def test_update_allowed_values_list_modifying_element(self):
        """Test updating the `allowed_values` list of a property modify one element within it."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={
                "allowed_values": {
                    "type": "list",
                    "values": [
                        *CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST[
                            "allowed_values"
                        ]["values"][:-1],
                        42,
                    ],
                },
            },
            stored_catalogue_category_property_in_data=(
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
            ),
        )
        self.call_update_expecting_error(catalogue_category_property_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
        )

    def test_update_allowed_values_list_removing_element(self):
        """Test updating the `allowed_values` list of a property to have one less element than it already has."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={
                "allowed_values": {
                    "type": "list",
                    "values": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST[
                        "allowed_values"
                    ]["values"][:-1],
                },
            },
            stored_catalogue_category_property_in_data=(
                CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST
            ),
        )
        self.call_update_expecting_error(catalogue_category_property_id, InvalidActionError)
        self.check_update_failed_with_exception(
            "Cannot modify existing values inside allowed_values of type 'list', you may only add more values"
        )

    def test_update_with_non_existent_catalogue_category_id(self):
        """Test updating the a catalogue category property when given a non-existent catalogue category ID."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"name": "New name"},
            stored_catalogue_category_property_in_data=CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
            catalogue_category_exists=False,
        )
        self.call_update_expecting_error(catalogue_category_property_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No catalogue category found with ID '{self._catalogue_category_id}'")

    def test_update_with_non_existent_catalogue_category_property_id(self):
        """Test updating the a catalogue category property when given a non-existent catalogue category property ID."""

        catalogue_category_property_id = str(ObjectId())

        self.mock_update(
            catalogue_category_property_id,
            catalogue_category_property_update_data={"name": "New name"},
            stored_catalogue_category_property_in_data=None,
        )
        self.call_update_expecting_error(catalogue_category_property_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No property found with ID '{catalogue_category_property_id}'")
