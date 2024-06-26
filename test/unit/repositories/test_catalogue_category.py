# pylint: disable=too-many-lines
"""
Unit tests for the `CatalogueCategoryRepo` repository.
"""

from test.mock_data import (
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
    CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT,
)
from test.unit.repositories.conftest import RepositoryTestHelpers
from test.unit.repositories.test_utils import (
    MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH,
    MOCK_MOVE_QUERY_RESULT_INVALID,
    MOCK_MOVE_QUERY_RESULT_VALID,
)
from test.unit.services.test_catalogue_item import CATALOGUE_ITEM_A_INFO
from typing import Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DuplicateRecordError,
    InvalidActionError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    CatalogueCategoryPropertyIn,
    CatalogueCategoryPropertyOut,
)
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo


class CatalogueCategoryRepoDSL:
    """Base class for CatalogueCategoryRepo unit tests"""

    # pylint:disable=too-many-instance-attributes
    test_helpers: RepositoryTestHelpers
    mock_database: Mock
    mock_utils: Mock
    catalogue_category_repository: CatalogueCategoryRepo
    catalogue_categories_collection: Mock
    catalogue_items_collection: Mock

    mock_session = MagicMock()

    # Internal data for utility functions
    _mock_child_catalogue_category_data: Optional[dict]
    _mock_child_catalogue_item_data: Optional[dict]

    @pytest.fixture(autouse=True)
    def setup(self, test_helpers, database_mock):
        """Setup fixtures"""

        self.test_helpers = test_helpers
        self.mock_database = database_mock
        self.catalogue_category_repository = CatalogueCategoryRepo(database_mock)
        self.catalogue_categories_collection = database_mock.catalogue_categories
        self.catalogue_items_collection = database_mock.catalogue_items

        self.mock_session = MagicMock()

        # Here we only wrap the utils so they keep their original functionality - this is done here
        # to avoid having to mock the code generation function as the output will be passed to
        # CatalogueCategoryOut with pydantic validation and so will error otherwise
        with patch("inventory_management_system_api.repositories.catalogue_category.utils") as mock_utils:
            self.mock_utils = mock_utils
            yield

    def mock_has_child_elements(
        self, child_catalogue_category_data: Optional[dict] = None, child_catalogue_item_data: Optional[dict] = None
    ):
        """Mocks database methods appropriately for when the 'has_child_elements' repo method will be called

        :param child_catalogue_category_data: Dictionary containing a child catalogue categories's data (or None)
        :param child_catalogue_item_data: Dictionary containing a child catalogue item's data (or None)
        """

        self._mock_child_catalogue_category_data = child_catalogue_category_data
        self._mock_child_catalogue_item_data = child_catalogue_item_data

        self.test_helpers.mock_find_one(self.catalogue_categories_collection, child_catalogue_category_data)
        self.test_helpers.mock_find_one(self.catalogue_items_collection, child_catalogue_item_data)

    def check_has_child_elements_performed_expected_calls(self, expected_catalogue_category_id: str):
        """Checks that a call to `has_child_elements` performed the expected function calls

        :param expected_catalogue_category_id: Expected catalogue category id used in the database calls
        """

        self.catalogue_categories_collection.find_one.assert_called_once_with(
            {"parent_id": CustomObjectId(expected_catalogue_category_id)}, session=self.mock_session
        )
        # Will only call the second one if the first doesn't return anything
        if not self._mock_child_catalogue_category_data:
            self.catalogue_items_collection.find_one.assert_called_once_with(
                {"catalogue_category_id": CustomObjectId(expected_catalogue_category_id)}, session=self.mock_session
            )


class CreateDSL(CatalogueCategoryRepoDSL):
    """Base class for create tests"""

    _catalogue_category_in: CatalogueCategoryIn
    _expected_catalogue_category_out: CatalogueCategoryOut
    _created_catalogue_category: CatalogueCategoryOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        catalogue_category_in_data: dict,
        parent_catalogue_category_in_data: Optional[dict] = None,
        duplicate_catalogue_category_in_data: Optional[dict] = None,
    ):
        """Mocks database methods appropriately to test the 'create' repo method

        :param catalogue_category_in_data: Dictionary containing the catalogue category data as would be required for
                                           a CatalogueCategoryIn database model (i.e. no id or created and modified
                                           times required)
        :param parent_catalogue_category_in_data: Either None or a dictionary containing the parent catalogue category
                                                  data as would be required for a CatalogueCategoryIn database model
        :param duplicate_catalogue_category_in_data: Either None or a dictionary containing catalogue category data
                                                     for a duplicate catalogue category
        """
        inserted_catalogue_category_id = CustomObjectId(str(ObjectId()))

        # Pass through CatalogueCategoryIn first as need creation and modified times
        self._catalogue_category_in = CatalogueCategoryIn(**catalogue_category_in_data)

        self._expected_catalogue_category_out = CatalogueCategoryOut(
            **self._catalogue_category_in.model_dump(by_alias=True), id=inserted_catalogue_category_id
        )

        # When a parent_id is given, need to mock the find_one for it too
        if catalogue_category_in_data["parent_id"]:
            # If parent_catalogue_category_data is given as None, then it is intentionally supposed to be, otherwise
            # pass through CatalogueCategoryIn first to ensure it has creation and modified times
            self.test_helpers.mock_find_one(
                self.catalogue_categories_collection,
                (
                    {
                        **CatalogueCategoryIn(**parent_catalogue_category_in_data).model_dump(),
                        "_id": catalogue_category_in_data["parent_id"],
                    }
                    if parent_catalogue_category_in_data
                    else None
                ),
            )
        self.test_helpers.mock_find_one(
            self.catalogue_categories_collection,
            (
                {**CatalogueCategoryIn(**duplicate_catalogue_category_in_data).model_dump(), "_id": ObjectId()}
                if duplicate_catalogue_category_in_data
                else None
            ),
        )
        self.test_helpers.mock_insert_one(self.catalogue_categories_collection, inserted_catalogue_category_id)
        self.test_helpers.mock_find_one(
            self.catalogue_categories_collection,
            {**self._catalogue_category_in.model_dump(by_alias=True), "_id": inserted_catalogue_category_id},
        )

    def call_create(self):
        """Calls the CatalogueCategoryRepo `create` method with the appropriate data from a prior call to
        `mock_create`"""

        self._created_catalogue_category = self.catalogue_category_repository.create(
            self._catalogue_category_in, session=self.mock_session
        )

    def call_create_expecting_error(self, error_type: type[BaseException]):
        """Calls the CatalogueCategoryRepo `create` method with the appropriate data from a prior call to `mock_create`
        while expecting an error to be raised"""

        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.create(self._catalogue_category_in)
        self._create_exception = exc

    def check_create_success(self):
        """Checks that a prior call to `call_create` worked as expected"""

        catalogue_category_in_data = self._catalogue_category_in.model_dump(by_alias=True)

        # Obtain a list of expected find_one calls
        expected_find_one_calls = []
        # This is the check for parent existence
        if self._catalogue_category_in.parent_id:
            expected_find_one_calls.append(
                call({"_id": self._catalogue_category_in.parent_id}, session=self.mock_session)
            )
        # Also need checks for duplicate and the final newly inserted catalogue category get
        expected_find_one_calls.append(
            call(
                {
                    "parent_id": self._catalogue_category_in.parent_id,
                    "code": self._catalogue_category_in.code,
                    "_id": {"$ne": None},
                },
                session=self.mock_session,
            )
        )
        expected_find_one_calls.append(
            call(
                {"_id": CustomObjectId(self._expected_catalogue_category_out.id)},
                session=self.mock_session,
            )
        )
        self.catalogue_categories_collection.find_one.assert_has_calls(expected_find_one_calls)

        self.catalogue_categories_collection.insert_one.assert_called_once_with(
            catalogue_category_in_data, session=self.mock_session
        )
        assert self._created_catalogue_category == self._expected_catalogue_category_out

    def check_create_failed_with_exception(self, message: str):
        """Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message"""

        self.catalogue_categories_collection.insert_one.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a Catalogue Category"""

    def test_create_non_leaf_without_parent(self):
        """Test creating a non-leaf Catalogue Category without a parent"""

        self.mock_create(CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A)
        self.call_create()
        self.check_create_success()

    def test_create_leaf_without_properties(self):
        """Test creating a leaf Catalogue Category without properties"""

        self.mock_create(CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.call_create()
        self.check_create_success()

    def test_create_leaf_with_properties(self):
        """Test creating a leaf Catalogue Category with properties"""

        self.mock_create(CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES)
        self.call_create()
        self.check_create_success()

    def test_create_with_parent(self):
        """Test creating a Catalogue Category with a parent"""

        self.mock_create(
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, "parent_id": str(ObjectId())},
            parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_parent_id(self):
        """Test creating a Catalogue Category with a non existent parent_id"""

        parent_id = str(ObjectId())

        self.mock_create(
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, "parent_id": parent_id},
            parent_catalogue_category_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No parent catalogue category found with ID: {parent_id}")

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a Catalogue Category with a duplicate Catalogue Category being found in the same parent
        Catalogue Category"""

        self.mock_create(
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, "parent_id": str(ObjectId())},
            parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
            duplicate_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
        )
        self.call_create_expecting_error(DuplicateRecordError)
        self.check_create_failed_with_exception(
            "Duplicate catalogue category found within the parent catalogue category"
        )


class GetDSL(CatalogueCategoryRepoDSL):
    """Base class for get tests"""

    _obtained_catalogue_category_id: str
    _expected_catalogue_category_out: Optional[CatalogueCategoryOut]
    _obtained_catalogue_category: Optional[CatalogueCategoryOut]
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, catalogue_category_id: str, catalogue_category_in_data: Optional[dict]):
        """Mocks database methods appropriately to test the 'get' repo method

        :param catalogue_category_id: ID of the Catalogue Category that will be obtained
        :param catalogue_category_in_data: Either None or a Dictionary containing the catalogue category data as would
                                           be required for a CatalogueCategoryIn database model (i.e. No id or created
                                           and modified times required)
        """

        self._expected_catalogue_category_out = (
            CatalogueCategoryOut(
                **CatalogueCategoryIn(**catalogue_category_in_data).model_dump(by_alias=True),
                id=CustomObjectId(catalogue_category_id),
            )
            if catalogue_category_in_data
            else None
        )

        self.test_helpers.mock_find_one(
            self.catalogue_categories_collection,
            self._expected_catalogue_category_out.model_dump() if self._expected_catalogue_category_out else None,
        )

    def call_get(self, catalogue_category_id: str):
        """Calls the CatalogueCategoryRepo `get` method with the appropriate data from a prior call to `mock_get`"""

        self._obtained_catalogue_category_id = catalogue_category_id
        self._obtained_catalogue_category = self.catalogue_category_repository.get(
            catalogue_category_id, session=self.mock_session
        )

    def call_get_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]):
        """Calls the CatalogueCategoryRepo `get` method with the appropriate data from a prior call to `mock_get`
        while expecting an error to be raised"""

        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.get(catalogue_category_id)
        self._get_exception = exc

    def check_get_success(self):
        """Checks that a prior call to `call_get` worked as expected"""

        self.catalogue_categories_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_catalogue_category_id)}, session=self.mock_session
        )
        assert self._obtained_catalogue_category == self._expected_catalogue_category_out

    def check_get_failed_with_exception(self, message: str):
        """Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception
        with the correct message"""

        self.catalogue_categories_collection.find_one.assert_not_called()

        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a Catalogue Category"""

    def test_get(self):
        """Test getting a Catalogue Category"""

        catalogue_category_id = str(ObjectId())

        self.mock_get(catalogue_category_id, CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A)
        self.call_get(catalogue_category_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Test getting a Catalogue Category with a non-existent ID"""

        catalogue_category_id = str(ObjectId())

        self.mock_get(catalogue_category_id, None)
        self.call_get(catalogue_category_id)
        self.check_get_success()

    def test_get_with_invalid_id(self):
        """Test getting a Catalogue Category with an invalid ID"""

        catalogue_category_id = "invalid-id"

        self.call_get_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_get_failed_with_exception("Invalid ObjectId value 'invalid-id'")


# pylint: disable=duplicate-code
class GetBreadcrumbsDSL(CatalogueCategoryRepoDSL):
    """Base class for breadcrumbs tests"""

    _breadcrumbs_query_result: list[dict]
    _mock_aggregation_pipeline = MagicMock()
    _expected_breadcrumbs: MagicMock
    _obtained_catalogue_category_id: str
    _obtained_breadcrumbs: MagicMock
    # pylint: enable=duplicate-code

    def mock_breadcrumbs(self, breadcrumbs_query_result: list[dict]):
        """Mocks database methods appropriately to test the 'get_breadcrumbs' repo method

        :param breadcrumbs_query_result: List of dictionaries containing the breadcrumbs query result from the
                                         aggregation pipeline
        """

        self._breadcrumbs_query_result = breadcrumbs_query_result
        self._mock_aggregation_pipeline = MagicMock()
        self._expected_breadcrumbs = MagicMock()

        self.mock_utils.create_breadcrumbs_aggregation_pipeline.return_value = self._mock_aggregation_pipeline
        self.catalogue_categories_collection.aggregate.return_value = breadcrumbs_query_result
        self.mock_utils.compute_breadcrumbs.return_value = self._expected_breadcrumbs

    def call_get_breadcrumbs(self, catalogue_category_id: str):
        """Calls the CatalogueCategoryRepo `get_breadcrumbs` method"""

        self._obtained_catalogue_category_id = catalogue_category_id
        self._obtained_breadcrumbs = self.catalogue_category_repository.get_breadcrumbs(
            catalogue_category_id, session=self.mock_session
        )

    def check_get_breadcrumbs_success(self):
        """Checks that a prior call to `call_get_breadcrumbs` worked as expected"""

        self.mock_utils.create_breadcrumbs_aggregation_pipeline.assert_called_once_with(
            entity_id=self._obtained_catalogue_category_id, collection_name="catalogue_categories"
        )
        self.catalogue_categories_collection.aggregate.assert_called_once_with(
            self._mock_aggregation_pipeline, session=self.mock_session
        )
        self.mock_utils.compute_breadcrumbs.assert_called_once_with(
            list(self._breadcrumbs_query_result),
            entity_id=self._obtained_catalogue_category_id,
            collection_name="catalogue_categories",
        )

        assert self._obtained_breadcrumbs == self._expected_breadcrumbs


# pylint: disable=duplicate-code
class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting the breadcrumbs of a Catalogue Category"""

    def test_get_breadcrumbs(self):
        """Test getting a Catalogue Categories's breadcrumbs"""

        self.mock_breadcrumbs(MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH)
        self.call_get_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_success()


# pylint: enable=duplicate-code


class ListDSL(CatalogueCategoryRepoDSL):
    """Base class for list tests"""

    _expected_catalogue_categories_out: list[CatalogueCategoryOut]
    _parent_id_filter: Optional[str]
    _obtained_catalogue_categories_out: list[CatalogueCategoryOut]

    def mock_list(self, catalogue_categories_in_data: list[dict]):
        """Mocks database methods appropriately to test the 'list' repo method

        :param catalogue_categories_in_data: List of dictionaries containing the catalogue category data as would be
                                             required for a CatalogueCategoryIn database model (i.e. no id or created
                                             and modified times required)
        """

        self._expected_catalogue_categories_out = [
            CatalogueCategoryOut(
                **CatalogueCategoryIn(**catalogue_category_in_data).model_dump(by_alias=True), id=ObjectId()
            )
            for catalogue_category_in_data in catalogue_categories_in_data
        ]

        self.test_helpers.mock_find(
            self.catalogue_categories_collection,
            [catalogue_category_out.model_dump() for catalogue_category_out in self._expected_catalogue_categories_out],
        )

    def call_list(self, parent_id: Optional[str]):
        """Calls the CatalogueCategoryRepo `list` method"""

        self._parent_id_filter = parent_id

        self._obtained_catalogue_categories_out = self.catalogue_category_repository.list(
            parent_id=parent_id, session=self.mock_session
        )

    def check_list_success(self):
        """Checks that a prior call to 'call_list` worked as expected"""

        self.mock_utils.list_query.assert_called_once_with(self._parent_id_filter, "catalogue categories")
        self.catalogue_categories_collection.find.assert_called_once_with(
            self.mock_utils.list_query.return_value, session=self.mock_session
        )

        assert self._obtained_catalogue_categories_out == self._expected_catalogue_categories_out


class TestList(ListDSL):
    """Tests for listing Catalogue Categorie's"""

    def test_list(self):
        """Test listing all Catalogue Categories"""

        self.mock_list(
            [CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B]
        )
        self.call_list(parent_id=None)
        self.check_list_success()

    def test_list_with_parent_id_filter(self):
        """Test listing all Catalogue Categories with a given parent_id"""

        self.mock_list(
            [CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B]
        )
        self.call_list(parent_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_null_parent_id_filter(self):
        """Test listing all Catalogue Categories with a 'null' parent_id"""

        self.mock_list(
            [CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B]
        )
        self.call_list(parent_id="null")
        self.check_list_success()

    # pylint: disable=duplicate-code
    def test_list_with_parent_id_with_no_results(self):
        """Test listing all Catalogue Categories with a parent_id filter returning no results"""

        self.mock_list([])
        self.call_list(parent_id=str(ObjectId()))
        self.check_list_success()

    # pylint: enable=duplicate-code


class UpdateDSL(CatalogueCategoryRepoDSL):
    """Base class for update tests"""

    # pylint:disable=too-many-instance-attributes
    _catalogue_category_in: CatalogueCategoryIn
    _stored_catalogue_category_out: Optional[CatalogueCategoryOut]
    _expected_catalogue_category_out: CatalogueCategoryOut
    _updated_catalogue_category_id: str
    _updated_catalogue_category: CatalogueCategoryOut
    _moving_catalogue_category: bool
    _update_exception: pytest.ExceptionInfo

    def set_update_data(self, new_catalogue_category_in_data: dict):
        """Assigns the update data to use during a call to `call_update`

        :param new_catalogue_category_in_data: New catalogue category data as would be required for a
                                               CatalogueCategoryIn database model to supply to the SystemRepo
                                               `update` method
        """
        self._catalogue_category_in = CatalogueCategoryIn(**new_catalogue_category_in_data)

    # pylint:disable=too-many-arguments
    def mock_update(
        self,
        catalogue_category_id: str,
        new_catalogue_category_in_data: dict,
        stored_catalogue_category_in_data: Optional[dict],
        new_parent_catalogue_category_in_data: Optional[dict] = None,
        duplicate_catalogue_category_in_data: Optional[dict] = None,
        valid_move_result: bool = True,
    ):
        """Mocks database methods appropriately to test the 'update' repo method

        :param catalogue_category_id: ID of the Catalogue Category that will be obtained
        :param new_catalogue_category_in_data: Dictionary containing the new catalogue category data as would be
                                               required for a CatalogueCategoryIn database model (i.e. no id or
                                               created and modified times required)
        :param stored_catalogue_category_in_data: Dictionary containing the catalogue category data for the existing
                                                  stored catalogue category as would be required for a SystemIn
                                                  database model
        :param new_parent_catalogue_category_in_data: Either None or a dictionary containing the new parent system data
                                                      as would be required for a SystemIn database model
        :param duplicate_catalogue_category_in_data: Either None or a dictionary containing the data for a duplicate
                                                     system as would be required for a SystemIn database model
        :param valid_move_result: Whether to mock in a valid or invalid move result i.e. when True will simulating
                                  moving the system one of its own children
        """
        self.set_update_data(new_catalogue_category_in_data)

        # When a parent_id is given, need to mock the find_one for it too
        if new_catalogue_category_in_data["parent_id"]:
            # If new_parent_catalogue_category_data is given as none, then it is intentionally supposed to be, otherwise
            # pass through CatalogueCategoryIn first to ensure it has creation and modified times
            self.test_helpers.mock_find_one(
                self.catalogue_categories_collection,
                (
                    {
                        **CatalogueCategoryIn(**new_parent_catalogue_category_in_data).model_dump(by_alias=True),
                        "_id": new_catalogue_category_in_data["parent_id"],
                    }
                    if new_parent_catalogue_category_in_data
                    else None
                ),
            )

        # Stored catalogue category
        self._stored_catalogue_category_out = (
            CatalogueCategoryOut(
                **CatalogueCategoryIn(**stored_catalogue_category_in_data).model_dump(by_alias=True),
                id=CustomObjectId(catalogue_category_id),
            )
            if stored_catalogue_category_in_data
            else None
        )
        self.test_helpers.mock_find_one(
            self.catalogue_categories_collection,
            self._stored_catalogue_category_out.model_dump() if self._stored_catalogue_category_out else None,
        )

        # Duplicate check
        self._moving_catalogue_category = stored_catalogue_category_in_data is not None and (
            new_catalogue_category_in_data["parent_id"] != stored_catalogue_category_in_data["parent_id"]
        )
        if (
            self._stored_catalogue_category_out
            and (self._catalogue_category_in.name != self._stored_catalogue_category_out.name)
        ) or self._moving_catalogue_category:
            self.test_helpers.mock_find_one(
                self.catalogue_categories_collection,
                (
                    {
                        **CatalogueCategoryIn(**duplicate_catalogue_category_in_data).model_dump(by_alias=True),
                        "_id": ObjectId(),
                    }
                    if duplicate_catalogue_category_in_data
                    else None
                ),
            )

        # Final catalogue category after update
        self._expected_catalogue_category_out = CatalogueCategoryOut(
            **self._catalogue_category_in.model_dump(), id=CustomObjectId(catalogue_category_id)
        )
        self.test_helpers.mock_find_one(
            self.catalogue_categories_collection, self._expected_catalogue_category_out.model_dump()
        )

        if self._moving_catalogue_category:
            mock_aggregation_pipeline = MagicMock()
            self.mock_utils.create_move_check_aggregation_pipeline.return_value = mock_aggregation_pipeline
            if valid_move_result:
                self.mock_utils.is_valid_move_result.return_value = True
                self.catalogue_categories_collection.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_VALID
            else:
                self.mock_utils.is_valid_move_result.return_value = False
                self.catalogue_categories_collection.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_INVALID

    def call_update(self, system_id: str):
        """Calls the CatalogueCategoryRepo `update` method with the appropriate data from a prior call to `mock_update`
        (or`set_update_data`)"""

        self._updated_catalogue_category_id = system_id
        self._updated_catalogue_category = self.catalogue_category_repository.update(
            system_id, self._catalogue_category_in, session=self.mock_session
        )

    def call_update_expecting_error(self, system_id: str, error_type: type[BaseException]):
        """Calls the CatalogueCategoryRepo `update` method with the appropriate data from a prior call to `mock_update`
        (or `set_update_data`) while expecting an error to be raised"""

        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.update(system_id, self._catalogue_category_in)
        self._update_exception = exc

    def check_update_success(self):
        """Checks that a prior call to `call_update` worked as expected"""

        # Obtain a list of expected find_one calls
        expected_find_one_calls = []

        # Parent existence check
        if self._catalogue_category_in.parent_id:
            expected_find_one_calls.append(
                call({"_id": self._catalogue_category_in.parent_id}, session=self.mock_session)
            )

        # Stored system
        expected_find_one_calls.append(
            call(
                {"_id": CustomObjectId(self._expected_catalogue_category_out.id)},
                session=self.mock_session,
            )
        )

        # Duplicate check (which only runs if moving or changing the name)
        if (
            self._stored_catalogue_category_out
            and (self._catalogue_category_in.name != self._stored_catalogue_category_out.name)
        ) or self._moving_catalogue_category:
            expected_find_one_calls.append(
                call(
                    {
                        "parent_id": self._catalogue_category_in.parent_id,
                        "code": self._catalogue_category_in.code,
                        "_id": {"$ne": CustomObjectId(self._updated_catalogue_category_id)},
                    },
                    session=self.mock_session,
                )
            )
        self.catalogue_categories_collection.find_one.assert_has_calls(expected_find_one_calls)

        if self._moving_catalogue_category:
            self.mock_utils.create_move_check_aggregation_pipeline.assert_called_once_with(
                entity_id=self._updated_catalogue_category_id,
                destination_id=str(self._catalogue_category_in.parent_id),
                collection_name="catalogue_categories",
            )
            self.catalogue_categories_collection.aggregate.assert_called_once_with(
                self.mock_utils.create_move_check_aggregation_pipeline.return_value, session=self.mock_session
            )

        self.catalogue_categories_collection.update_one.assert_called_once_with(
            {
                "_id": CustomObjectId(self._updated_catalogue_category_id),
            },
            {
                "$set": {
                    **self._catalogue_category_in.model_dump(),
                },
            },
            session=self.mock_session,
        )

        assert self._updated_catalogue_category == self._expected_catalogue_category_out

    def check_update_failed_with_exception(self, message: str):
        """Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message"""

        self.catalogue_categories_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a Catalogue Category"""

    def test_update(self):
        """Test updating a Catalogue Category"""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_no_changes(self):
        """Test updating a Catalogue Category to have exactly the same contents"""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_parent_id(self):
        """Test updating a Catalogue Category's parent_id to move it"""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id=catalogue_category_id,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
                "parent_id": str(ObjectId()),
            },
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
            duplicate_catalogue_category_in_data=None,
            valid_move_result=True,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_parent_id_to_child_of_self(self):
        """Test updating a Catalogue Category's parent_id to a child of it self (should prevent this)"""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id=catalogue_category_id,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
                "parent_id": str(ObjectId()),
            },
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
            duplicate_catalogue_category_in_data=None,
            valid_move_result=False,
        )
        self.call_update_expecting_error(catalogue_category_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot move a catalogue category to one of its own children")

    def test_update_with_non_existent_parent_id(self):
        """Test updating a Catalogue Category's parent_id to a non-existent Catalogue Category"""

        catalogue_category_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, "parent_id": new_parent_id},
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            new_parent_catalogue_category_in_data=None,
        )
        self.call_update_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No parent catalogue category found with ID: {new_parent_id}")

    def test_update_name_to_duplicate_within_parent(self):
        """Test updating a Catalogue Category's name to one that is a duplicate within the same parent Catalogue
        Category"""

        catalogue_category_id = str(ObjectId())
        new_name = "New Duplicate Name"

        self.mock_update(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, "name": new_name},
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            duplicate_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
        )
        self.call_update_expecting_error(catalogue_category_id, DuplicateRecordError)
        self.check_update_failed_with_exception(
            "Duplicate catalogue category found within the parent catalogue category"
        )

    def test_update_parent_id_with_duplicate_within_parent(self):
        """Test updating a Catalogue Category's parent-id to one contains a Catalogue Category with a duplicate name
        within the same parent Catalogue Category"""

        catalogue_category_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A, "parent_id": new_parent_id},
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B,
            duplicate_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
        )
        self.call_update_expecting_error(catalogue_category_id, DuplicateRecordError)
        self.check_update_failed_with_exception(
            "Duplicate catalogue category found within the parent catalogue category"
        )

    def test_update_with_invalid_id(self):
        """Test updating a System with an invalid id"""

        catalogue_category_id = "invalid-id"

        self.set_update_data(CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A)
        self.call_update_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_update_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class HasChildElementsDSL(CatalogueCategoryRepoDSL):
    """Base class for has_child_elements tests"""

    _has_child_elements_catalogue_category_id: str
    _has_child_elements_result: bool

    def call_has_child_elements(self, catalogue_category_id: str):
        """Calls the CatalogueCategoryRepo `has_child_elements` method"""

        self._has_child_elements_catalogue_category_id = catalogue_category_id
        self._has_child_elements_result = self.catalogue_category_repository.has_child_elements(
            CustomObjectId(catalogue_category_id), session=self.mock_session
        )

    def check_has_child_elements_success(self, expected_result: bool):
        """Checks that a prior call to `call_has_child_elements` worked as expected

        :param expected_result: The expected result returned by `has_child_elements`
        """

        self.check_has_child_elements_performed_expected_calls(self._has_child_elements_catalogue_category_id)

        assert self._has_child_elements_result == expected_result


class TestHasChildElements(HasChildElementsDSL):
    """Tests for `has_child_elements`"""

    def test_has_child_elements_with_no_children(self):
        """Test `has_child_elements` when there are no child catalogue categories or catalogue items"""

        self.mock_has_child_elements(child_catalogue_category_data=None, child_catalogue_item_data=None)
        self.call_has_child_elements(catalogue_category_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=False)

    def test_has_child_elements_with_child_catalogue_category(self):
        """Test `has_child_elements` when there is a child catalogue category but no child catalogue items"""

        self.mock_has_child_elements(
            child_catalogue_category_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A,
            child_catalogue_item_data=None,
        )
        self.call_has_child_elements(catalogue_category_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=True)

    def test_has_child_elements_with_child_catalogue_catalogue_item(self):
        """Test `has_child_elements` when there are no child catalogue categories but there is a child catalogue item"""

        # pylint:disable=fixme
        # TODO: Replace CATALOGUE_ITEM_A_INFO once item tests have been refactored
        self.mock_has_child_elements(
            child_catalogue_category_data=None,
            child_catalogue_item_data=CATALOGUE_ITEM_A_INFO,
        )
        self.call_has_child_elements(catalogue_category_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=True)


class DeleteDSL(CatalogueCategoryRepoDSL):
    """Base class for delete tests"""

    _delete_catalogue_category_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self,
        deleted_count: int,
        child_catalogue_category_data: Optional[dict] = None,
        child_catalogue_item_data: Optional[dict] = None,
    ):
        """Mocks database methods appropriately to test the 'delete' repo method

        :param deleted_count: Number of documents deleted successfully
        :param child_system_data: Dictionary containing a child catalogue categories's data (or None)
        :param child_item_data: Dictionary containing a child catalogue item's data (or None)
        """

        self.mock_has_child_elements(child_catalogue_category_data, child_catalogue_item_data)
        self.test_helpers.mock_delete_one(self.catalogue_categories_collection, deleted_count)

    def call_delete(self, system_id: str):
        """Calls the CatalogueCategoryRepo `delete` method"""

        self._delete_catalogue_category_id = system_id
        self.catalogue_category_repository.delete(system_id, session=self.mock_session)

    def call_delete_expecting_error(self, system_id: str, error_type: type[BaseException]):
        """Calls the CatalogueCategoryRepo `delete` method while expecting an error to be raised"""

        self._delete_catalogue_category_id = system_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.delete(system_id)
        self._delete_exception = exc

    def check_delete_success(self):
        """Checks that a prior call to `call_delete` worked as expected"""

        self.check_has_child_elements_performed_expected_calls(self._delete_catalogue_category_id)
        self.catalogue_categories_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_catalogue_category_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False):
        """Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception
        with the correct message"""

        if not expecting_delete_one_called:
            self.catalogue_categories_collection.delete_one.assert_not_called()
        else:
            self.catalogue_categories_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_catalogue_category_id)}, session=None
            )

        assert str(self._delete_exception.value) == message


# pylint: disable=duplicate-code
class TestDelete(DeleteDSL):
    """Tests for deleting a Catalogue Category"""

    def test_delete(self):
        """Test deleting a Catalogue Category"""

        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    # pylint: enable=duplicate-code

    def test_delete_with_child_catalogue_category(self):
        """Test deleting a Catalogue Category when it has a child Catalogue Category"""

        catalogue_category_id = str(ObjectId())

        self.mock_delete(deleted_count=1, child_catalogue_category_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A)
        self.call_delete_expecting_error(catalogue_category_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(
            f"Catalogue category with ID {catalogue_category_id} has child elements and cannot be deleted"
        )

    def test_delete_with_child_catalogue_item(self):
        """Test deleting a Catalogue Category when it has a child Catalogue Item"""

        catalogue_category_id = str(ObjectId())

        # pylint:disable=fixme
        # TODO: Replace CATALOGUE_ITEM_A_INFO once item tests have been refactored
        self.mock_delete(deleted_count=1, child_catalogue_item_data=CATALOGUE_ITEM_A_INFO)
        self.call_delete_expecting_error(catalogue_category_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(
            f"Catalogue category with ID {catalogue_category_id} has child elements and cannot be deleted"
        )

    def test_delete_non_existent_id(self):
        """Test deleting a Catalogue Category with a non-existent id"""

        catalogue_category_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_delete_failed_with_exception(
            f"No catalogue category found with ID: {catalogue_category_id}", expecting_delete_one_called=True
        )

    def test_delete_invalid_id(self):
        """Test deleting a Catalogue Category with an invalid id"""

        catalogue_category_id = "invalid-id"

        self.call_delete_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class CreatePropertyDSL(CatalogueCategoryRepoDSL):
    """Base class for create property tests"""

    _mock_datetime: Mock
    _property_in: CatalogueCategoryPropertyIn
    _expected_property_out: CatalogueCategoryPropertyOut
    _created_property: CatalogueCategoryOut
    _catalogue_category_id: str
    _create_exception: pytest.ExceptionInfo

    @pytest.fixture(autouse=True)
    def setup_create_property_dsl(self):
        """Setup fixtures"""

        with patch("inventory_management_system_api.repositories.catalogue_category.datetime") as mock_datetime:
            self._mock_datetime = mock_datetime
            yield

    def mock_create_property(self, property_in_data: dict):
        """Mocks database methods appropriately to test the 'create_property' repo method

        :param property_in_data: Dictionary containing the catalogue category property data as would be required for a
                                 CatalogueCategoryPropertyIn database model
        """

        self._property_in = CatalogueCategoryPropertyIn(**property_in_data)
        self._expected_property_out = CatalogueCategoryPropertyOut(**self._property_in.model_dump(by_alias=True))

        self.test_helpers.mock_update_one(self.catalogue_categories_collection)

    def call_create_property(self, catalogue_category_id: str):
        """Calls the CatalogueCategoryRepo `create_property` method with the appropriate data from a prior call to
        `mock_create_property`
        """

        self._catalogue_category_id = catalogue_category_id
        self._created_property = self.catalogue_category_repository.create_property(
            catalogue_category_id, self._property_in, session=self.mock_session
        )

    def call_create_property_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]):
        """Calls the CatalogueCategoryRepo `create_property` method with the appropriate data from a prior call to
        `mock_create_property`
        """

        self._catalogue_category_id = catalogue_category_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.create_property(
                catalogue_category_id, self._property_in, session=self.mock_session
            )
        self._create_exception = exc

    def check_create_property_success(self):
        """Checks that a prior call to `call_create_property` worked as expected"""

        self.catalogue_categories_collection.update_one.assert_called_once_with(
            {"_id": CustomObjectId(self._catalogue_category_id)},
            {
                "$push": {"properties": self._property_in.model_dump(by_alias=True)},
                "$set": {"modified_time": self._mock_datetime.now.return_value},
            },
            session=self.mock_session,
        )
        assert self._created_property == self._expected_property_out

    def check_create_property_failed_with_exception(self, message: str):
        """Checks that a prior call to `call_create_property_expecting_error` worked as expected, raising an exception
        with the correct message"""

        self.catalogue_categories_collection.update_one.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreateProperty(CreatePropertyDSL):
    """Tests for creating a property"""

    def test_create_property(self):
        """Test creating a property in an existing Catalogue Category"""

        self.mock_create_property(CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT)
        self.call_create_property(str(ObjectId()))
        self.check_create_property_success()

    def test_create_property_with_invalid_id(self):
        """Test creating a property in a Catalogue Category with an invalid id"""

        self.mock_create_property(CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT)
        self.call_create_property_expecting_error("invalid-id", InvalidObjectIdError)
        self.check_create_property_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class UpdatePropertyDSL(CreatePropertyDSL):
    """Base class for update property tests"""

    _updated_property: CatalogueCategoryOut
    _property_id: str
    _update_exception: pytest.ExceptionInfo

    def mock_update_property(self, property_in_data: dict):
        """Mocks database methods appropriately to test the 'update_property' repo method

        :param property_in_data: Dictionary containing the catalogue category property data as would be required for a
                                 CatalogueCategoryPropertyIn database model
        """

        self._property_in = CatalogueCategoryPropertyIn(**property_in_data)
        self._expected_property_out = CatalogueCategoryPropertyOut(**self._property_in.model_dump(by_alias=True))

        self.test_helpers.mock_update_one(self.catalogue_categories_collection)

    def call_update_property(self, catalogue_category_id: str, property_id: str):
        """Calls the CatalogueCategoryRepo `update_property` method with the appropriate data from a prior call to
        `mock_update_property`
        """

        self._catalogue_category_id = catalogue_category_id
        self._property_id = property_id
        self._updated_property = self.catalogue_category_repository.update_property(
            catalogue_category_id, property_id, self._property_in, session=self.mock_session
        )

    def call_update_property_expecting_error(
        self, catalogue_category_id: str, property_id: str, error_type: type[BaseException]
    ):
        """Calls the CatalogueCategoryRepo `update_property` method with the appropriate data from a prior call to
        `mock_update_property`
        """

        self._catalogue_category_id = catalogue_category_id
        self._property_id = property_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.update_property(
                catalogue_category_id, property_id, self._property_in, session=self.mock_session
            )
        self._update_exception = exc

    def check_update_property_success(self):
        """Checks that a prior call to `call_update_property` worked as expected"""

        self.catalogue_categories_collection.update_one.assert_called_once_with(
            {
                "_id": CustomObjectId(self._catalogue_category_id),
                "properties._id": CustomObjectId(self._property_id),
            },
            {
                "$set": {
                    "properties.$[elem]": self._property_in.model_dump(by_alias=True),
                    "modified_time": self._mock_datetime.now.return_value,
                },
            },
            array_filters=[{"elem._id": CustomObjectId(self._property_id)}],
            session=self.mock_session,
        )
        assert self._updated_property == self._expected_property_out

    def check_update_property_failed_with_exception(self, message: str):
        """Checks that a prior call to `call_update_property_expecting_error` worked as expected, raising an exception
        with the correct message"""

        self.catalogue_categories_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdateProperty(UpdatePropertyDSL):
    """Tests for updating a property"""

    def test_update_property(self):
        """Test updating a property in an existing Catalogue Category"""

        self.mock_update_property(CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT)
        self.call_update_property(catalogue_category_id=str(ObjectId()), property_id=str(ObjectId()))
        self.check_update_property_success()

    def test_update_property_with_invalid_catalogue_category_id(self):
        """Test updating a property in a Catalogue Category with an invalid id"""

        self.mock_update_property(CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT)
        self.call_update_property_expecting_error(
            catalogue_category_id="invalid-id", property_id=str(ObjectId()), error_type=InvalidObjectIdError
        )
        self.check_update_property_failed_with_exception("Invalid ObjectId value 'invalid-id'")

    def test_update_property_with_invalid_property_id(self):
        """Test updating a property with an invalid id in a Catalogue Category"""

        self.mock_update_property(CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT)
        self.call_update_property_expecting_error(
            catalogue_category_id=str(ObjectId()), property_id="invalid-id", error_type=InvalidObjectIdError
        )
        self.check_update_property_failed_with_exception("Invalid ObjectId value 'invalid-id'")
