# pylint: disable=too-many-lines
"""
Unit tests for the `CatalogueCategoryService` service.
"""

from datetime import timedelta
from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    UNIT_IN_DATA_MM,
)
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW, ServiceTestHelpers
from typing import Optional
from unittest.mock import ANY, MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DuplicateCatalogueCategoryPropertyNameError,
    LeafCatalogueCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    CatalogueCategoryPropertyIn,
    CatalogueCategoryPropertyOut,
)
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPatchSchema,
    CatalogueCategoryPostPropertySchema,
    CatalogueCategoryPostSchema,
)
from inventory_management_system_api.services import utils
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService


class CatalogueCategoryServiceDSL:
    """Base class for CatalogueCategoryService unit tests"""

    wrapped_utils: Mock
    mock_catalogue_category_repository: Mock
    mock_unit_repository: Mock
    catalogue_category_service: CatalogueCategoryService
    unit_value_id_dict: dict[str, str] = {}

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

    def mock_add_property_unit_values(self, units_in_data: list[dict]):
        """Mocks database methods appropriately for when the `_add_property_unit_values` repo method will be called

        Also generates unit ids that are stored inside `unit_value_id_dict` for future lookups.

        :param units_in_data: List of dictionaries containing the unit data as would be required for a UnitIn database
                              model
        """

        for unit_in_data in units_in_data:
            unit_in = UnitIn(**unit_in_data)
            unit_id = str(ObjectId())

            self.unit_value_id_dict[unit_in.value] = unit_id

            ServiceTestHelpers.mock_get(self.mock_unit_repository, UnitOut(**unit_in.model_dump(), id=unit_id))

    def check_add_property_unit_values_performed_expected_calls(
        self, expected_properties: list[CatalogueCategoryPostPropertySchema]
    ):
        """Checks that a call to `add_property_unit_values` performed the expected function calls

        :param expected_properties: Expected properties the function would have been called with
        """

        expected_unit_repo_calls = []
        for prop in expected_properties:
            if prop.unit_id:
                expected_unit_repo_calls.append(call(prop.unit_id))

        self.mock_unit_repository.get.assert_has_calls(expected_unit_repo_calls)


class CreateDSL(CatalogueCategoryServiceDSL):
    """Base class for create tests"""

    _catalogue_category_post: CatalogueCategoryPostSchema
    _expected_catalogue_category_in: CatalogueCategoryIn
    _expected_catalogue_category_out: CatalogueCategoryOut
    _created_catalogue_category: CatalogueCategoryOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        catalogue_category_data: dict,
        parent_catalogue_category_in_data: Optional[dict] = None,
        units_in_data: Optional[list[dict]] = None,
    ):
        """Mocks repo methods appropriately to test the 'create' service method

        :param catalogue_category_data: Dictionary containing the basic system data as would be required for a
                                        CatalogueCategoryPostSchema but without any unit_id's in its properties
                                        as they will be added automatically
        :param parent_catalogue_category_in_data: Either None or a dictionary containing the parent catalogue category
                                                  data as would be required for a CatalogueCategoryIn database model
        :param units_in_data: Either None or a list of dictionaries containing the unit data as would be required for
                              a UnitIn database model. These values will be used for any unit look ups required by the
                              given catalogue category properties
        """

        # When a parent_id is given need to mock the get for it too
        if catalogue_category_data["parent_id"]:
            ServiceTestHelpers.mock_get(
                self.mock_catalogue_category_repository,
                CatalogueCategoryOut(
                    **CatalogueCategoryIn(**parent_catalogue_category_in_data).model_dump(by_alias=True),
                    id=str(ObjectId()),
                ),
            )

        # When properties are given need to mock any units and need to ensure the expected data
        # inserts the unit values as well
        property_post_schemas = []
        expected_properties_in = []
        if catalogue_category_data["properties"]:
            self.mock_add_property_unit_values(units_in_data)

            for prop in catalogue_category_data["properties"]:
                unit_id = None
                if "unit" in prop and prop["unit"]:
                    unit_id = self.unit_value_id_dict.get(prop["unit"])

                property_post_schemas.append(CatalogueCategoryPostPropertySchema(**prop, unit_id=unit_id))
                expected_properties_in.append(CatalogueCategoryPropertyIn(**prop, unit_id=unit_id))

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

    def call_create(self):
        """Calls the CatalogueCategoryService `create` method with the appropriate data from a prior call to
        `mock_create`"""

        self._created_catalogue_category = self.catalogue_category_service.create(self._catalogue_category_post)

    def check_create_success(self):
        """Checks that a prior call to `call_create` worked as expected"""

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

        # To assert with property ids we must compare as dicts and use ANY here as otherwise the ObjectIds will always
        # be different
        if self._catalogue_category_post.properties:
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


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category"""

    def test_create_without_properties(self):
        """Test creating a catalogue category without properties"""

        self.mock_create(CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        self.call_create()
        self.check_create_success()

    def test_create_with_properties(self):
        """Test creating a catalogue category with properties"""

        self.mock_create(CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM, units_in_data=[UNIT_IN_DATA_MM])
        self.call_create()
        self.check_create_success()


# UNIT_A = {
#     "value": "mm",
#     "code": "mm",
#     "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
#     "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
# }


# def test_create_with_parent_id(
#     test_helpers,
#     catalogue_category_repository_mock,
#     unit_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test creating a catalogue category with a parent ID.

#     Verify that the `create` method properly handles a catalogue category with a parent ID.
#     """

#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)

#     # pylint: disable=duplicate-code
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=True,
#         parent_id=str(ObjectId()),
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()),
#                 name="Property A",
#                 type="number",
#                 unit_id=unit.id,
#                 unit=unit.value,
#                 mandatory=False,
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the parent catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.parent_id,
#             name="Category A",
#             code="category-a",
#             is_leaf=False,
#             parent_id=None,
#             properties=[],
#             created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#             modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         ),
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)

#     # Mock `create` to return the created catalogue category
#     test_helpers.mock_create(catalogue_category_repository_mock, catalogue_category)

#     created_catalogue_category = catalogue_category_service.create(
#         CatalogueCategoryPostSchema(
#             name=catalogue_category.name,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=[prop.model_dump() for prop in catalogue_category.properties],
#         )
#     )

#     # pylint: disable=duplicate-code
#     # To assert with property ids we must compare as dicts and use ANY here as otherwise the ObjectIds will always
#     # be different
#     catalogue_category_repository_mock.create.assert_called_once()
#     create_catalogue_category_in = catalogue_category_repository_mock.create.call_args_list[0][0][0]
#     assert isinstance(create_catalogue_category_in, CatalogueCategoryIn)
#     assert create_catalogue_category_in.model_dump() == {
#         **(
#             CatalogueCategoryIn(
#                 name=catalogue_category.name,
#                 code=catalogue_category.code,
#                 is_leaf=catalogue_category.is_leaf,
#                 parent_id=catalogue_category.parent_id,
#                 properties=[prop.model_dump() for prop in catalogue_category.properties],
#             ).model_dump()
#         ),
#         "properties": [{**prop.model_dump(), "id": ANY, "unit_id": ANY} for prop in catalogue_category.properties],
#     }
#     # pylint: enable=duplicate-code
#     assert created_catalogue_category == catalogue_category


# def test_create_with_whitespace_name(
#     test_helpers,
#     catalogue_category_repository_mock,
#     unit_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test creating a catalogue category name containing leading/trailing/consecutive whitespaces.

#     Verify that the `create` method trims the whitespace from the category name and handles it correctly.
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)

#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="    Category   A         ",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()), name="Property A", type="number", unit_id=unit.id, unit=unit.value, mandatory=False
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `create` to return the created catalogue category
#     test_helpers.mock_create(catalogue_category_repository_mock, catalogue_category)

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)

#     created_catalogue_category = catalogue_category_service.create(
#         CatalogueCategoryPostSchema(
#             name=catalogue_category.name,
#             is_leaf=catalogue_category.is_leaf,
#             properties=[prop.model_dump() for prop in catalogue_category.properties],
#         )
#     )

#     # pylint: disable=duplicate-code
#     # To assert with property ids we must compare as dicts and use ANY here as otherwise the ObjectIds will always
#     # be different
#     catalogue_category_repository_mock.create.assert_called_once()
#     create_catalogue_category_in = catalogue_category_repository_mock.create.call_args_list[0][0][0]
#     assert isinstance(create_catalogue_category_in, CatalogueCategoryIn)
#     assert create_catalogue_category_in.model_dump() == {
#         **(
#             CatalogueCategoryIn(
#                 name=catalogue_category.name,
#                 code=catalogue_category.code,
#                 is_leaf=catalogue_category.is_leaf,
#                 parent_id=catalogue_category.parent_id,
#                 properties=[prop.model_dump() for prop in catalogue_category.properties],
#             ).model_dump()
#         ),
#         "properties": [{**prop.model_dump(), "id": ANY, "unit_id": ANY} for prop in catalogue_category.properties],
#     }
#     # pylint: enable=duplicate-code
#     assert created_catalogue_category == catalogue_category


# def test_create_with_leaf_parent_catalogue_category(
#     test_helpers, catalogue_category_repository_mock, unit_repository_mock, catalogue_category_service
# ):
#     """
#     Test creating a catalogue category in a leaf parent catalogue category.
#     """
#     # pylint: disable=duplicate-code

#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=False,
#         parent_id=str(ObjectId()),
#         properties=[],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the parent catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.parent_id,
#             name="Category A",
#             code="category-a",
#             is_leaf=True,
#             parent_id=None,
#             properties=[
#                 CatalogueCategoryPropertyOut(
#                     id=str(ObjectId()),
#                     name="Property A",
#                     type="number",
#                     unit_id=unit.id,
#                     unit=unit.value,
#                     mandatory=False,
#                 ),
#                 CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#             ],
#             created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#             modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         ),
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)

#     with pytest.raises(LeafCatalogueCategoryError) as exc:
#         catalogue_category_service.create(
#             CatalogueCategoryPostSchema(
#                 name=catalogue_category.name,
#                 is_leaf=catalogue_category.is_leaf,
#                 parent_id=catalogue_category.parent_id,
#                 properties=catalogue_category.properties,
#             )
#         )
#     catalogue_category_repository_mock.create.assert_not_called()
#     assert str(exc.value) == "Cannot add catalogue category to a leaf parent catalogue category"


# def test_create_with_duplicate_property_names(
#     test_helpers, catalogue_category_repository_mock, unit_repository_mock, catalogue_category_service
# ):
#     """
#     Test trying to create a catalogue category with duplicate property names
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=True,
#         parent_id=None,
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()), name="Property A", type="number", unit_id=unit.id, unit=unit.value, mandatory=False
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property A", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)
#     # pylint: enable=duplicate-code

#     with pytest.raises(DuplicateCatalogueCategoryPropertyNameError) as exc:
#         # pylint: disable=duplicate-code
#         catalogue_category_service.create(
#             CatalogueCategoryPostSchema(
#                 name=catalogue_category.name,
#                 is_leaf=catalogue_category.is_leaf,
#                 properties=[prop.model_dump() for prop in catalogue_category.properties],
#             )
#         )
#         # pylint: enable=duplicate-code
#     catalogue_category_repository_mock.create.assert_not_called()
#     assert str(exc.value) == (f"Duplicate property name: {catalogue_category.properties[0].name}")


# def test_create_properties_with_non_existent_unit_id(
#     test_helpers,
#     catalogue_category_repository_mock,
#     unit_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test creating a catalogue category with a non existent unit ID.
#     """

#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)

#     # pylint: disable=duplicate-code
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=True,
#         parent_id=str(ObjectId()),
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()),
#                 name="Property A",
#                 type="number",
#                 unit_id=unit.id,
#                 unit=unit.value,
#                 mandatory=False,
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the parent catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.parent_id,
#             name="Category A",
#             code="category-a",
#             is_leaf=False,
#             parent_id=None,
#             properties=[],
#             created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#             modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         ),
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, None)

#     # Mock `create` to return the created catalogue category
#     test_helpers.mock_create(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_category_service.create(
#             CatalogueCategoryPostSchema(
#                 name=catalogue_category.name,
#                 is_leaf=catalogue_category.is_leaf,
#                 parent_id=catalogue_category.parent_id,
#                 properties=[prop.model_dump() for prop in catalogue_category.properties],
#             )
#         )
#     catalogue_category_repository_mock.create.assert_not_called()
#     assert str(exc.value) == (f"No unit found with ID: {unit.id}")


# def test_delete(catalogue_category_repository_mock, catalogue_category_service):
#     """
#     Test deleting a catalogue category.

#     Verify that the `delete` method properly handles the deletion of a catalogue category by ID.
#     """
#     catalogue_category_id = str(ObjectId())

#     catalogue_category_service.delete(catalogue_category_id)

#     catalogue_category_repository_mock.delete.assert_called_once_with(catalogue_category_id)


# def test_get(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
#     """
#     Test getting a catalogue category.

#     Verify that the `get` method properly handles the retrieval of a catalogue category by ID.
#     """
#     # pylint: disable=duplicate-code
#     catalogue_category_id = str(ObjectId())
#     catalogue_category = MagicMock()

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, catalogue_category)

#     retrieved_catalogue_category = catalogue_category_service.get(catalogue_category_id)

#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)
#     assert retrieved_catalogue_category == catalogue_category


# def test_get_with_non_existent_id(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
#     """
#     Test getting a catalogue category with a non-existent ID.

#     Verify that the `get` method properly handles the retrieval of a catalogue category with a non-existent ID.
#     """
#     catalogue_category_id = str(ObjectId())

#     # Mock `get` to not return a catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, None)

#     retrieved_catalogue_category = catalogue_category_service.get(catalogue_category_id)

#     assert retrieved_catalogue_category is None
#     catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)


# def test_get_breadcrumbs(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
#     """
#     Test getting breadcrumbs for a catalogue category

#     Verify that the `get_breadcrumbs` method properly handles the retrieval of breadcrumbs for a catalogue category
#     """
#     catalogue_category_id = str(ObjectId())
#     breadcrumbs = MagicMock()

#     # Mock `get` to return breadcrumbs
#     test_helpers.mock_get_breadcrumbs(catalogue_category_repository_mock, breadcrumbs)

#     retrieved_breadcrumbs = catalogue_category_service.get_breadcrumbs(catalogue_category_id)

#     catalogue_category_repository_mock.get_breadcrumbs.assert_called_once_with(catalogue_category_id)
#     assert retrieved_breadcrumbs == breadcrumbs


# def test_list(catalogue_category_repository_mock, catalogue_category_service):
#     """
#     Test listing catalogue categories.

#     Verify that the `list` method properly calls the repository function with any passed filters
#     """

#     parent_id = MagicMock()

#     result = catalogue_category_service.list(parent_id=parent_id)

#     catalogue_category_repository_mock.list.assert_called_once_with(parent_id)
#     assert result == catalogue_category_repository_mock.list.return_value


# def test_update_when_no_child_elements(
#     test_helpers,
#     catalogue_category_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test updating a catalogue category without child elements

#     Verify that the `update` method properly handles the catalogue category to be updated when it doesn't have any
#     child elements.
#     """
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=True,
#         parent_id=None,
#         properties=[],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name="Category A",
#             code="category-a",
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     updated_catalogue_category = catalogue_category_service.update(
#         catalogue_category.id, CatalogueCategoryPatchSchema(name=catalogue_category.name)
#     )

#     # pylint: disable=duplicate-code
#     catalogue_category_repository_mock.update.assert_called_once_with(
#         catalogue_category.id,
#         CatalogueCategoryIn(
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.modified_time,
#         ),
#     )
#     # pylint: enable=duplicate-code
#     assert updated_catalogue_category == catalogue_category


# def test_update_when_has_child_elements(
#     test_helpers,
#     catalogue_category_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test updating a catalogue category when it has child elements

#     Verify that the `update` method properly handles the catalogue category to be updated when it has children.
#     """
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=True,
#         parent_id=None,
#         properties=[],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name="Category A",
#             code="category-a",
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )
#     # Mock so child elements found
#     catalogue_category_repository_mock.has_child_elements.return_value = True
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     updated_catalogue_category = catalogue_category_service.update(
#         catalogue_category.id, CatalogueCategoryPatchSchema(name=catalogue_category.name)
#     )

#     # pylint: disable=duplicate-code
#     catalogue_category_repository_mock.update.assert_called_once_with(
#         catalogue_category.id,
#         CatalogueCategoryIn(
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.modified_time,
#         ),
#     )
#     # pylint: enable=duplicate-code
#     assert updated_catalogue_category == catalogue_category


# def test_update_with_non_existent_id(test_helpers, catalogue_category_repository_mock, catalogue_category_service):
#     """
#     Test updating a catalogue category with a non-existent ID.

#     Verify that the `update` method properly handles the catalogue category to be updated with a non-existent ID.
#     """
#     # Mock `get` to not return a catalogue category
#     test_helpers.mock_get(catalogue_category_repository_mock, None)

#     catalogue_category_id = str(ObjectId())
#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_category_service.update(catalogue_category_id, CatalogueCategoryPatchSchema(properties=[]))
#     catalogue_category_repository_mock.update.assert_not_called()
#     assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"


# def test_update_change_parent_id(
#     test_helpers,
#     catalogue_category_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test moving a catalogue category to another parent catalogue category.
#     """

#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category B",
#         code="category-b",
#         is_leaf=False,
#         parent_id=str(ObjectId()),
#         properties=[],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=None,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     # Mock `get` to return a parent catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=str(ObjectId()),
#             name="Category A",
#             code="category-a",
#             is_leaf=False,
#             parent_id=None,
#             properties=[],
#             created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#             modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         ),
#     )
#     # pylint: enable=duplicate-code
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     updated_catalogue_category = catalogue_category_service.update(
#         catalogue_category.id, CatalogueCategoryPatchSchema(parent_id=catalogue_category.parent_id)
#     )

#     # pylint: disable=duplicate-code
#     catalogue_category_repository_mock.update.assert_called_once_with(
#         catalogue_category.id,
#         CatalogueCategoryIn(
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.modified_time,
#         ),
#     )
#     # pylint: enable=duplicate-code
#     assert updated_catalogue_category == catalogue_category


# def test_update_change_parent_id_leaf_parent_catalogue_category(
#     test_helpers, catalogue_category_repository_mock, unit_repository_mock, catalogue_category_service
# ):
#     """
#     Testing moving a catalogue category to a leaf parent catalogue category.
#     """
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category_b_id = str(ObjectId())
#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_b_id,
#             name="Category B",
#             code="category-b",
#             is_leaf=False,
#             parent_id=None,
#             properties=[],
#             created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#             modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         ),
#     )
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     catalogue_category_a_id = str(ObjectId())
#     # Mock `get` to return a parent catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category_b_id,
#             name="Category A",
#             code="category-a",
#             is_leaf=True,
#             parent_id=None,
#             properties=[
#                 CatalogueCategoryPropertyOut(
#                     id=str(ObjectId()),
#                     name="Property A",
#                     type="number",
#                     unit_id=unit.id,
#                     unit=unit.value,
#                     mandatory=False,
#                 ),
#                 CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#             ],
#             created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#             modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         ),
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)

#     with pytest.raises(LeafCatalogueCategoryError) as exc:
#         catalogue_category_service.update(
#             catalogue_category_b_id, CatalogueCategoryPatchSchema(parent_id=catalogue_category_a_id)
#         )
#     catalogue_category_repository_mock.update.assert_not_called()
#     assert str(exc.value) == "Cannot add catalogue category to a leaf parent catalogue category"


# def test_update_change_from_leaf_to_non_leaf_when_no_child_elements(
#     test_helpers,
#     catalogue_category_repository_mock,
#     unit_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test changing a catalogue category from leaf to non-leaf when the category doesn't have any child elements.
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category A",
#         code="category-a",
#         is_leaf=False,
#         parent_id=None,
#         properties=[],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=True,
#             parent_id=catalogue_category.parent_id,
#             properties=[
#                 CatalogueCategoryPropertyOut(
#                     id=str(ObjectId()),
#                     name="Property A",
#                     type="number",
#                     unit_id=unit.id,
#                     unit=unit.value,
#                     mandatory=False,
#                 ),
#                 CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#             ],
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     updated_catalogue_category = catalogue_category_service.update(
#         catalogue_category.id, CatalogueCategoryPatchSchema(is_leaf=False)
#     )

#     catalogue_category_repository_mock.update.assert_called_once_with(
#         catalogue_category.id,
#         CatalogueCategoryIn(
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=catalogue_category.properties,
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.modified_time,
#         ),
#     )
#     assert updated_catalogue_category == catalogue_category


# def test_update_change_properties_when_no_child_elements(
#     test_helpers,
#     catalogue_category_repository_mock,
#     unit_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test updating a catalogue category's item properties when it has no child elements.

#     Verify that the `update` method properly handles the catalogue category to be updated.
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()), name="Property A", type="number", unit_id=unit.id, unit=unit.value, mandatory=False
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=[catalogue_category.properties[1]],
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     # pylint: enable=duplicate-code
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     updated_catalogue_category = catalogue_category_service.update(
#         catalogue_category.id,
#         CatalogueCategoryPatchSchema(properties=[prop.model_dump() for prop in catalogue_category.properties]),
#     )

#     # To assert with property ids we must compare as dicts and use ANY here as otherwise the ObjectIds will always
#     # be different
#     catalogue_category_repository_mock.update.assert_called_once_with(catalogue_category.id, ANY)
#     update_catalogue_category_in = catalogue_category_repository_mock.update.call_args_list[0][0][1]
#     assert isinstance(update_catalogue_category_in, CatalogueCategoryIn)
#     assert update_catalogue_category_in.model_dump() == {
#         **(
#             CatalogueCategoryIn(
#                 name=catalogue_category.name,
#                 code=catalogue_category.code,
#                 is_leaf=catalogue_category.is_leaf,
#                 parent_id=catalogue_category.parent_id,
#                 properties=[prop.model_dump() for prop in catalogue_category.properties],
#                 created_time=catalogue_category.created_time,
#                 modified_time=catalogue_category.modified_time,
#             ).model_dump()
#         ),
#         "properties": [{**prop.model_dump(), "id": ANY, "unit_id": ANY} for prop in catalogue_category.properties],
#     }
#     assert updated_catalogue_category == catalogue_category


# def test_update_change_from_leaf_to_non_leaf_when_has_child_elements(
#     test_helpers, catalogue_category_repository_mock, unit_repository_mock, catalogue_category_service
# ):
#     """
#     Test changing a catalogue category from leaf to non-leaf when the category has child elements.
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category A",
#         code="category-a",
#         is_leaf=False,
#         parent_id=None,
#         properties=[],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=True,
#             parent_id=catalogue_category.parent_id,
#             properties=[
#                 CatalogueCategoryPropertyOut(
#                     id=str(ObjectId()),
#                     name="Property A",
#                     type="number",
#                     unit_id=unit.id,
#                     unit=unit.value,
#                     mandatory=False,
#                 ),
#                 CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#             ],
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.modified_time,
#         ),
#     )
#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)
#     # Mock so child elements found
#     catalogue_category_repository_mock.has_child_elements.return_value = True
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(ChildElementsExistError) as exc:
#         catalogue_category_service.update(catalogue_category.id, CatalogueCategoryPatchSchema(is_leaf=False))
#     catalogue_category_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value)
#         == f"Catalogue category with ID {str(catalogue_category.id)} has child elements and cannot be updated"
#     )


# def test_update_change_properties_when_has_child_elements(
#     test_helpers, catalogue_category_repository_mock, unit_repository_mock, catalogue_category_service
# ):
#     """
#     Test updating a catalogue category's item properties when it has child elements.

#     Verify that the `update` method properly handles the catalogue category to be updated.
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()), name="Property A", type="number", unit_id=unit.id, unit=unit.value, mandatory=False
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=[catalogue_category.properties[1]],
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )
#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)
#     # Mock so child elements found
#     catalogue_category_repository_mock.has_child_elements.return_value = True
#     # pylint: enable=duplicate-code
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(ChildElementsExistError) as exc:
#         catalogue_category_service.update(
#             catalogue_category.id,
#             CatalogueCategoryPatchSchema(properties=[prop.model_dump() for prop in catalogue_category.properties]),
#         )
#     catalogue_category_repository_mock.update.assert_not_called()
#     assert (
#         str(exc.value)
#         == f"Catalogue category with ID {str(catalogue_category.id)} has child elements and cannot be updated"
#     )


# def test_update_properties_to_have_duplicate_names(
#     test_helpers, catalogue_category_repository_mock, unit_repository_mock, catalogue_category_service
# ):
#     """
#     Test that checks that trying to update properties so that the names are duplicated is not allowed

#     Verify the `update` method properly handles the catalogue category to be updated
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()), name="Duplicate", type="number", unit_id=unit.id, unit=unit.value, mandatory=False
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Duplicate", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=[catalogue_category.properties[1]],
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )
#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, unit)
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     # pylint: enable=duplicate-code
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(DuplicateCatalogueCategoryPropertyNameError) as exc:
#         catalogue_category_service.update(
#             catalogue_category.id,
#             CatalogueCategoryPatchSchema(properties=[prop.model_dump() for prop in catalogue_category.properties]),
#         )
#     catalogue_category_repository_mock.update.assert_not_called()
#     assert str(exc.value) == (f"Duplicate property name: {catalogue_category.properties[0].name}")


# def test_update_change_properties_with_non_existent_unit_id(
#     test_helpers,
#     catalogue_category_repository_mock,
#     unit_repository_mock,
#     model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
#     catalogue_category_service,
# ):
#     """
#     Test updating a catalogue category's properties when it has a non existent unit ID.
#     """
#     # pylint: disable=duplicate-code
#     unit = UnitOut(id=str(ObjectId()), **UNIT_A)
#     catalogue_category = CatalogueCategoryOut(
#         id=str(ObjectId()),
#         name="Category A",
#         code="category-a",
#         is_leaf=True,
#         parent_id=None,
#         properties=[
#             CatalogueCategoryPropertyOut(
#                 id=str(ObjectId()), name="Property A", type="number", unit_id=unit.id, unit=unit.value, mandatory=False
#             ),
#             CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
#         ],
#         created_time=MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
#         modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
#     )
#     # pylint: enable=duplicate-code

#     # Mock `get` to return a catalogue category
#     # pylint: disable=duplicate-code
#     test_helpers.mock_get(
#         catalogue_category_repository_mock,
#         CatalogueCategoryOut(
#             id=catalogue_category.id,
#             name=catalogue_category.name,
#             code=catalogue_category.code,
#             is_leaf=catalogue_category.is_leaf,
#             parent_id=catalogue_category.parent_id,
#             properties=[catalogue_category.properties[1]],
#             created_time=catalogue_category.created_time,
#             modified_time=catalogue_category.created_time,
#         ),
#     )

#     # Mock `get` to return the unit
#     test_helpers.mock_get(unit_repository_mock, None)
#     # Mock so child elements not found
#     catalogue_category_repository_mock.has_child_elements.return_value = False
#     # pylint: enable=duplicate-code
#     # Mock `update` to return the updated catalogue category
#     test_helpers.mock_update(catalogue_category_repository_mock, catalogue_category)

#     with pytest.raises(MissingRecordError) as exc:
#         catalogue_category_service.update(
#             catalogue_category.id,
#             CatalogueCategoryPatchSchema(properties=[prop.model_dump() for prop in catalogue_category.properties]),
#         )
#     catalogue_category_repository_mock.update.assert_not_called()
#     assert str(exc.value) == (f"No unit found with ID: {unit.id}")
