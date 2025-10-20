"""
Unit tests for the `CatalogueCategoryService` service.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=too-many-lines
# pylint: disable=duplicate-code

from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    UNIT_IN_DATA_MM,
)
from test.unit.services.conftest import BaseCatalogueServiceDSL, ServiceTestHelpers
from typing import Optional
from unittest.mock import ANY, MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    LeafCatalogueCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.schemas.catalogue_category import (
    CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS,
    CatalogueCategoryPatchSchema,
    CatalogueCategoryPostPropertySchema,
    CatalogueCategoryPostSchema,
)
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService


class CatalogueCategoryServiceDSL(BaseCatalogueServiceDSL):
    """Base class for `CatalogueCategoryService` unit tests."""

    wrapped_utils: Mock
    mock_catalogue_category_repository: Mock
    mock_unit_repository: Mock
    catalogue_category_service: CatalogueCategoryService

    @pytest.fixture(autouse=True)
    def setup(
        self,
        catalogue_category_repository_mock,
        unit_repository_mock,
        catalogue_category_service,
        # Ensures all created and modified times are mocked throughout
        # pylint: disable=unused-argument
        model_mixins_datetime_now_mock,
    ):
        """Setup fixtures"""

        self.mock_catalogue_category_repository = catalogue_category_repository_mock
        self.mock_unit_repository = unit_repository_mock
        self.catalogue_category_service = catalogue_category_service

        with patch("inventory_management_system_api.services.catalogue_category.utils", wraps=utils) as wrapped_utils:
            self.wrapped_utils = wrapped_utils
            yield

    def mock_add_property_unit_values(
        self, units_in_data: list[Optional[dict]], unit_value_id_dict: dict[str, str]
    ) -> None:
        """
        Mocks database methods appropriately for when the `_add_property_unit_values` repo method will be called.

        Also generates unit IDs that are stored inside `unit_value_id_dict` for future lookups.

        :param units_in_data: List of dictionaries (or `None`) containing the unit data as would be required for a
                              `UnitIn` database model. These values will be used for any unit look ups required by
                              the given catalogue category properties.
        :param unit_value_id_dict: List of unit value and id pairs for lookups.
        """

        for unit_in_data in units_in_data:
            unit_in = UnitIn(**unit_in_data) if unit_in_data else None
            unit_id = unit_value_id_dict[unit_in.value] if unit_in_data else None

            ServiceTestHelpers.mock_get(
                self.mock_unit_repository, UnitOut(**unit_in.model_dump(), id=unit_id) if unit_in else None
            )

    def check_add_property_unit_values_performed_expected_calls(
        self, expected_properties: list[CatalogueCategoryPostPropertySchema]
    ) -> None:
        """Checks that a call to `add_property_unit_values` performed the expected function calls.

        :param expected_properties: Expected properties the function would have been called with.
        """

        expected_unit_repo_calls = []
        for prop in expected_properties:
            if prop.unit_id:
                expected_unit_repo_calls.append(call(prop.unit_id))

        self.mock_unit_repository.get.assert_has_calls(expected_unit_repo_calls)


class CreateDSL(CatalogueCategoryServiceDSL):
    """Base class for `create` tests."""

    _catalogue_category_post: CatalogueCategoryPostSchema
    _expected_catalogue_category_in: CatalogueCategoryIn
    _expected_catalogue_category_out: CatalogueCategoryOut
    _created_catalogue_category: CatalogueCategoryOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        catalogue_category_data: dict,
        parent_catalogue_category_in_data: Optional[dict] = None,
        units_in_data: Optional[list[Optional[dict]]] = None,
    ) -> None:
        """
        Mocks repo methods appropriately to test the `create` service method.

        :param catalogue_category_data: Dictionary containing the basic catalogue category data as would be required
                                        for a `CatalogueCategoryPostSchema` but with any `unit_id`'s replaced by the
                                        `unit` value in its properties as the IDs will be added automatically.
        :param parent_catalogue_category_in_data: Either `None` or a dictionary containing the parent catalogue category
                                                  data as would be required for a `CatalogueCategoryIn` database model.
        :param units_in_data: Either `None` or a list of dictionaries (or `None`) containing the unit data as would be
                              required for a `UnitIn` database model. These values will be used for any unit look ups
                              required by the given catalogue category properties.
        """

        # When a parent_id is given need to mock the get for it too
        if catalogue_category_data["parent_id"]:
            ServiceTestHelpers.mock_get(
                self.mock_catalogue_category_repository,
                CatalogueCategoryOut(
                    **{
                        **CatalogueCategoryIn(**parent_catalogue_category_in_data).model_dump(by_alias=True),
                        "_id": catalogue_category_data["parent_id"],
                    },
                ),
            )

        # When properties are given need to mock any units and ensure the expected data inserts the unit IDs as well
        property_post_schemas = []
        expected_properties_in = []
        if "properties" in catalogue_category_data and catalogue_category_data["properties"]:
            expected_properties_in, property_post_schemas = (
                self.construct_catalogue_category_properties_in_and_post_with_ids(catalogue_category_data["properties"])
            )

            self.mock_add_property_unit_values(units_in_data or [], self.unit_value_id_dict)

        self._catalogue_category_post = CatalogueCategoryPostSchema(
            **{**catalogue_category_data, "properties": property_post_schemas}
        )

        self._expected_catalogue_category_in = CatalogueCategoryIn(
            **{**catalogue_category_data, "properties": expected_properties_in},
            code=utils.generate_code(catalogue_category_data["name"], "catalogue category"),
        )
        self._expected_catalogue_category_out = CatalogueCategoryOut(
            **self._expected_catalogue_category_in.model_dump(), id=ObjectId()
        )

        ServiceTestHelpers.mock_create(self.mock_catalogue_category_repository, self._expected_catalogue_category_out)

    def call_create(self) -> None:
        """Calls the `CatalogueCategoryService` `create` method with the appropriate data from a prior call to
        `mock_create`."""

        self._created_catalogue_category = self.catalogue_category_service.create(self._catalogue_category_post)

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryService` `create` method with the appropriate data from a prior call to
        `mock_create` while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_service.create(self._catalogue_category_post)
        self._create_exception = exc

    def check_create_success(self) -> None:
        """Checks that a prior call to `call_create` worked as expected."""

        # This is the get for the parent
        if self._catalogue_category_post.parent_id:
            self.mock_catalogue_category_repository.get.assert_called_once_with(self._catalogue_category_post.parent_id)

        # This is the properties duplicate check
        if self._catalogue_category_post.properties:
            self.wrapped_utils.check_duplicate_property_names.assert_called_with(
                self._catalogue_category_post.properties
            )

        # This is for getting the units
        if self._catalogue_category_post.properties:
            self.check_add_property_unit_values_performed_expected_calls(self._catalogue_category_post.properties)

        self.wrapped_utils.generate_code.assert_called_once_with(
            self._expected_catalogue_category_out.name, "catalogue category"
        )

        if self._catalogue_category_post.properties:
            # To assert with property IDs we must compare as dicts and use ANY here as otherwise the ObjectIds will
            # always be different
            self.mock_catalogue_category_repository.create.assert_called_once()
            actual_catalogue_category_in = self.mock_catalogue_category_repository.create.call_args_list[0][0][0]
            assert isinstance(actual_catalogue_category_in, CatalogueCategoryIn)
            assert actual_catalogue_category_in.model_dump() == {
                **self._expected_catalogue_category_in.model_dump(),
                "properties": [
                    {**prop.model_dump(), "id": ANY} for prop in self._expected_catalogue_category_in.properties
                ],
            }
        else:
            self.mock_catalogue_category_repository.create.assert_called_once_with(self._expected_catalogue_category_in)

        assert self._created_catalogue_category == self._expected_catalogue_category_out

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_category_repository.create.assert_not_called()
        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category."""

    def test_create_without_properties(self):
        """Test creating a catalogue category without properties."""

        self.mock_create(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        self.call_create()
        self.check_create_success()

    def test_create_with_properties(self):
        """Test creating a catalogue category with properties."""

        self.mock_create(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM, units_in_data=[UNIT_IN_DATA_MM])
        self.call_create()
        self.check_create_success()

    def test_create_with_properties_with_non_existent_unit_id(self):
        """Test creating a catalogue category with properties with a non-existent unit ID."""

        self.mock_create(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM, units_in_data=[None])
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No unit found with ID '{self.unit_value_id_dict['mm']}'")

    def test_create_with_non_leaf_parent(self):
        """Test creating a catalogue category with a non-leaf parent catalogue category."""

        self.mock_create(
            CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            parent_catalogue_category_in_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_leaf_parent(self):
        """Test creating a catalogue category with a leaf parent catalogue category."""

        self.mock_create(
            {**CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": str(ObjectId())},
            parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_create_expecting_error(LeafCatalogueCategoryError)
        self.check_create_failed_with_exception("Cannot add catalogue category to a leaf parent catalogue category")


class GetDSL(CatalogueCategoryServiceDSL):
    """Base class for `get` tests."""

    _obtained_catalogue_category_id: str
    _expected_catalogue_category: MagicMock
    _obtained_catalogue_category: MagicMock

    def mock_get(self) -> None:
        """Mocks repo methods appropriately to test the `get` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_catalogue_category = MagicMock()
        ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._expected_catalogue_category)

    def call_get(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryService` `get` method.

        :param catalogue_category_id: ID of the catalogue category to be obtained.
        """

        self._obtained_catalogue_category_id = catalogue_category_id
        self._obtained_catalogue_category = self.catalogue_category_service.get(catalogue_category_id)

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.mock_catalogue_category_repository.get.assert_called_once_with(self._obtained_catalogue_category_id)
        assert self._obtained_catalogue_category == self._expected_catalogue_category


class TestGet(GetDSL):
    """Tests for getting a catalogue category."""

    def test_get(self):
        """Test getting a catalogue category."""

        self.mock_get()
        self.call_get(str(ObjectId()))
        self.check_get_success()


class GetBreadcrumbsDSL(CatalogueCategoryServiceDSL):
    """Base class for `get_breadcrumbs` tests"""

    _expected_breadcrumbs: MagicMock
    _obtained_breadcrumbs: MagicMock
    _obtained_catalogue_category_id: str

    def mock_get_breadcrumbs(self) -> None:
        """Mocks repo methods appropriately to test the `get_breadcrumbs` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_breadcrumbs = MagicMock()
        ServiceTestHelpers.mock_get_breadcrumbs(self.mock_catalogue_category_repository, self._expected_breadcrumbs)

    def call_get_breadcrumbs(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryService` `get_breadcrumbs` method.

        :param catalogue_category_id: ID of the catalogue category to obtain the breadcrumbs of.
        """

        self._obtained_catalogue_category_id = catalogue_category_id
        self._obtained_breadcrumbs = self.catalogue_category_service.get_breadcrumbs(catalogue_category_id)

    def check_get_breadcrumbs_success(self) -> None:
        """Checks that a prior call to `call_get_breadcrumbs` worked as expected."""

        self.mock_catalogue_category_repository.get_breadcrumbs.assert_called_once_with(
            self._obtained_catalogue_category_id
        )
        assert self._obtained_breadcrumbs == self._expected_breadcrumbs


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting the breadcrumbs of a catalogue category."""

    def test_get_breadcrumbs(self):
        """Test getting a catalogue category's breadcrumbs."""

        self.mock_get_breadcrumbs()
        self.call_get_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_success()


class ListDSL(CatalogueCategoryServiceDSL):
    """Base class for `list` tests"""

    _parent_id_filter: Optional[str]
    _expected_catalogue_categories: MagicMock
    _obtained_catalogue_categories: MagicMock

    def mock_list(self) -> None:
        """Mocks repo methods appropriately to test the `list` service method."""

        # Simply a return currently, so no need to use actual data
        self._expected_catalogue_categories = MagicMock()
        ServiceTestHelpers.mock_list(self.mock_catalogue_category_repository, self._expected_catalogue_categories)

    def call_list(self, parent_id: Optional[str]) -> None:
        """
        Calls the `CatalogueCategoryService` `list` method.

        :param parent_id: ID of the parent catalogue category to query by, or `None`.
        """

        self._parent_id_filter = parent_id
        self._obtained_catalogue_categories = self.catalogue_category_service.list(parent_id)

    def check_list_success(self) -> None:
        """Checks that a prior call to `call_list` worked as expected."""

        self.mock_catalogue_category_repository.list.assert_called_once_with(self._parent_id_filter)

        assert self._obtained_catalogue_categories == self._expected_catalogue_categories


class TestList(ListDSL):
    """Tests for listing catalogue categories."""

    def test_list(self):
        """Test listing catalogue categories."""

        self.mock_list()
        self.call_list(str(ObjectId()))
        self.check_list_success()


# pylint:disable=too-many-instance-attributes
class UpdateDSL(CatalogueCategoryServiceDSL):
    """Base class for `update` tests."""

    _stored_catalogue_category: Optional[CatalogueCategoryOut]
    _catalogue_category_patch: CatalogueCategoryPatchSchema
    _expected_catalogue_category_in: CatalogueCategoryIn
    _expected_catalogue_category_out: MagicMock
    _updated_catalogue_category_id: str
    _updated_catalogue_category: MagicMock
    _update_exception: pytest.ExceptionInfo

    _expect_child_check: bool
    _moving_catalogue_category: bool
    unit_value_id_dict: dict[str, str]

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def mock_update(
        self,
        catalogue_category_id: str,
        catalogue_category_update_data: dict,
        stored_catalogue_category_post_data: Optional[dict],
        has_child_elements: bool = False,
        new_parent_catalogue_category_in_data: Optional[dict] = None,
        units_in_data: Optional[list[Optional[dict]]] = None,
    ) -> None:
        """
        Mocks repository methods appropriately to test the `update` service method.

        :param catalogue_category_id: ID of the catalogue category that will be obtained.
        :param catalogue_category_update_data: Dictionary containing the basic patch data as would be required for a
                                               `CatalogueCategoryPatchSchema` but with any `unit_id`'s replaced by the
                                               `unit` value in its properties as the IDs will be added automatically.
        :param stored_catalogue_category_post_data: Dictionary containing the catalogue category data for the existing
                                               stored catalogue category as would be required for a
                                               `CatalogueCategoryPostSchema` (i.e. no ID, code or created and modified
                                               times required).
        :param has_child_elements: Boolean of whether the catalogue category being updated has child elements or not
        :param new_parent_catalogue_category_in_data: Either `None` or a dictionary containing the new parent catalogue
                                               category data as would be required for a `CatalogueCategoryIn` database
                                               model.
        :param units_in_data: Either `None` or a list of dictionaries (or `None`) containing the unit data as would be
                              required for a `UnitIn` database model. These values will be used for any unit look ups
                              required by the given catalogue category properties in the patch data.
        """

        # Stored catalogue category
        self._stored_catalogue_category = (
            CatalogueCategoryOut(
                **CatalogueCategoryIn(
                    **stored_catalogue_category_post_data,
                    code=utils.generate_code(stored_catalogue_category_post_data["name"], "catalogue category"),
                ).model_dump(by_alias=True),
                id=CustomObjectId(catalogue_category_id),
            )
            if stored_catalogue_category_post_data
            else None
        )
        ServiceTestHelpers.mock_get(self.mock_catalogue_category_repository, self._stored_catalogue_category)

        # Need to mock has_child_elements only if the check is required
        self._expect_child_check = any(
            key in catalogue_category_update_data for key in CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS
        )
        if self._expect_child_check:
            self.mock_catalogue_category_repository.has_child_elements.return_value = has_child_elements

        # When moving i.e. changing the parent id, the data for the new parent needs to be mocked
        self._moving_catalogue_category = (
            "parent_id" in catalogue_category_update_data and stored_catalogue_category_post_data is not None
        )

        if self._moving_catalogue_category and catalogue_category_update_data["parent_id"]:
            ServiceTestHelpers.mock_get(
                self.mock_catalogue_category_repository,
                (
                    CatalogueCategoryOut(
                        **{
                            **CatalogueCategoryIn(**new_parent_catalogue_category_in_data).model_dump(by_alias=True),
                            "_id": catalogue_category_update_data["parent_id"],
                        }
                    )
                    if new_parent_catalogue_category_in_data
                    else None
                ),
            )

        # When properties are given need to mock any units and ensure the expected data inserts the unit IDs as well
        expected_properties_in = []
        if "properties" in catalogue_category_update_data and catalogue_category_update_data["properties"]:
            expected_properties_in, property_post_schemas = (
                self.construct_catalogue_category_properties_in_and_post_with_ids(
                    catalogue_category_update_data["properties"]
                )
            )
            catalogue_category_update_data["properties"] = property_post_schemas

            self.mock_add_property_unit_values(units_in_data or [], self.unit_value_id_dict)

        # Updated catalogue category
        self._expected_catalogue_category_out = MagicMock()
        ServiceTestHelpers.mock_update(self.mock_catalogue_category_repository, self._expected_catalogue_category_out)

        # Patch schema
        self._catalogue_category_patch = CatalogueCategoryPatchSchema(**catalogue_category_update_data)

        # Construct the expected input for the repository
        merged_catalogue_category_data = {
            **(stored_catalogue_category_post_data or {}),
            **catalogue_category_update_data,
        }
        self._expected_catalogue_category_in = CatalogueCategoryIn(
            **{**merged_catalogue_category_data, "properties": expected_properties_in},
            code=utils.generate_code(merged_catalogue_category_data["name"], "catalogue category"),
        )

    def call_update(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryService` `update` method with the appropriate data from a prior call to
        `mock_update`.

        :param catalogue_category_id: ID of the catalogue category to be updated.
        """

        self._updated_catalogue_category_id = catalogue_category_id
        self._updated_catalogue_category = self.catalogue_category_service.update(
            catalogue_category_id, self._catalogue_category_patch
        )

    def call_update_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryService` `update` method with the appropriate data from a prior call to
        `mock_update` while expecting an error to be raised.

        :param catalogue_category_id: ID of the catalogue category to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_service.update(catalogue_category_id, self._catalogue_category_patch)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        # Obtain a list of expected catalogue category get calls
        expected_catalogue_category_get_calls = []

        # Ensure obtained old catalogue category
        expected_catalogue_category_get_calls.append(call(self._updated_catalogue_category_id))

        # Ensure checking children if needed
        if self._expect_child_check:
            self.mock_catalogue_category_repository.has_child_elements.assert_called_once_with(
                self._updated_catalogue_category_id
            )

        # Ensure new code was obtained if patching name
        if self._catalogue_category_patch.name:
            self.wrapped_utils.generate_code.assert_called_once_with(
                self._catalogue_category_patch.name, "catalogue category"
            )
        else:
            self.wrapped_utils.generate_code.assert_not_called()

        # Ensure obtained new parent if moving
        if self._moving_catalogue_category and self._catalogue_category_patch.parent_id:
            expected_catalogue_category_get_calls.append(call(self._catalogue_category_patch.parent_id))

        self.mock_catalogue_category_repository.get.assert_has_calls(expected_catalogue_category_get_calls)

        # Ensure updated with expected data
        if self._catalogue_category_patch.properties:
            self.wrapped_utils.check_duplicate_property_names.assert_called_with(
                self._catalogue_category_patch.properties
            )

            # To assert with property IDs we must compare as dicts and use ANY here as otherwise the ObjectIds will
            # always be different
            self.mock_catalogue_category_repository.update.assert_called_once()
            update_call_args = self.mock_catalogue_category_repository.update.call_args_list[0][0]
            assert update_call_args[0] == self._updated_catalogue_category_id
            actual_catalogue_category_in = update_call_args[1]
            assert isinstance(actual_catalogue_category_in, CatalogueCategoryIn)
            assert actual_catalogue_category_in.model_dump() == {
                **self._expected_catalogue_category_in.model_dump(),
                "properties": [
                    {**prop.model_dump(), "id": ANY} for prop in self._expected_catalogue_category_in.properties
                ],
            }
        else:
            self.mock_catalogue_category_repository.update.assert_called_once_with(
                self._updated_catalogue_category_id, self._expected_catalogue_category_in
            )

        assert self._updated_catalogue_category == self._expected_catalogue_category_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.mock_catalogue_category_repository.update.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue category."""

    def test_update_non_leaf_all_fields_except_parent_id_no_children(self):
        """Test updating all fields of a non-leaf catalogue category except its `parent_id` when it has no children."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_all_fields_except_parent_id_with_children(self):
        """Test updating all allowable fields of a catalogue category except its `parent_id` when it has children
        (leaf/non-leaf doesn't matter as properties can't be updated with children anyway)."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={"name": "New name"},
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            has_child_elements=True,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_is_leaf_without_children(self):
        """Test updating a catalogue categories is_leaf field only when it doesn't have any children
        (code should not need regenerating as name doesn't change)."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={"is_leaf": True},
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_is_leaf_with_children(self):
        """Test updating a catalogue categories is_leaf field only when it has children
        (code should not need regenerating as name doesn't change)."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={"is_leaf": True},
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            has_child_elements=True,
        )
        self.call_update_expecting_error(catalogue_category_id, ChildElementsExistError)
        self.check_update_failed_with_exception(
            f"Catalogue category with ID '{catalogue_category_id}' has child elements and cannot be updated"
        )

    def test_update_leaf_all_fields_except_parent_id_with_no_children(self):
        """Test updating all fields of a leaf catalogue category except its `parent_id` when it has no children."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data=CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            units_in_data=[UNIT_IN_DATA_MM],
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_leaf_properties_with_children(self):
        """Test updating the properties of a leaf catalogue category when it has children."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT]
            },
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            units_in_data=[UNIT_IN_DATA_MM],
            has_child_elements=True,
        )
        self.call_update_expecting_error(catalogue_category_id, ChildElementsExistError)
        self.check_update_failed_with_exception(
            f"Catalogue category with ID '{catalogue_category_id}' has child elements and cannot be updated"
        )

    def test_update_leaf_properties_with_non_existent_unit_id(self):
        """Test updating the properties of a leaf catalogue category when given a property with an non-existent unit
        ID."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={
                "properties": [CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT]
            },
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
            units_in_data=[None],
        )
        self.call_update_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No unit found with ID '{self.unit_value_id_dict['mm']}'")

    def test_update_parent_id(self):
        """Test updating a catalogue category's `parent_id` to move it."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={"parent_id": str(ObjectId())},
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_parent_id_to_leaf(self):
        """Test updating a catalogue category's `parent_id` to move it to a leaf catalogue category."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data={"parent_id": str(ObjectId())},
            stored_catalogue_category_post_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
        )
        self.call_update_expecting_error(catalogue_category_id, LeafCatalogueCategoryError)
        self.check_update_failed_with_exception("Cannot add catalogue category to a leaf parent catalogue category")

    def test_update_with_non_existent_id(self):
        """Test updating a catalogue category with a non-existent ID."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            catalogue_category_update_data=CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            stored_catalogue_category_post_data=None,
        )
        self.call_update_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No catalogue category found with ID '{catalogue_category_id}'")


class DeleteDSL(CatalogueCategoryServiceDSL):
    """Base class for `delete` tests."""

    _delete_catalogue_category_id: str

    def call_delete(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryService` `delete` method.

        :param catalogue_category_id: ID of the catalogue category to be deleted.
        """

        self._delete_catalogue_category_id = catalogue_category_id
        self.catalogue_category_service.delete(catalogue_category_id)

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.mock_catalogue_category_repository.delete.assert_called_once_with(self._delete_catalogue_category_id)


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue category."""

    def test_delete(self):
        """Test deleting a catalogue category."""

        self.call_delete(str(ObjectId()))
        self.check_delete_success()
