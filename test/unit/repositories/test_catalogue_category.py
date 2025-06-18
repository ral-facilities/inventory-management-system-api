"""
Unit tests for the `CatalogueCategoryRepo` repository.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code
# pylint: disable=too-many-lines

from test.mock_data import (
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
)
from test.unit.repositories.conftest import RepositoryTestHelpers
from test.unit.repositories.test_utils import (
    MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH,
    MOCK_MOVE_QUERY_RESULT_INVALID,
    MOCK_MOVE_QUERY_RESULT_VALID,
)
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
    """Base class for `CatalogueCategoryRepo` unit tests."""

    # pylint:disable=too-many-instance-attributes
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
    def setup(self, database_mock):
        """Setup fixtures"""

        self.mock_database = database_mock
        self.catalogue_category_repository = CatalogueCategoryRepo(database_mock)
        self.catalogue_categories_collection = database_mock.catalogue_categories
        self.catalogue_items_collection = database_mock.catalogue_items

        self.mock_session = MagicMock()

        with patch("inventory_management_system_api.repositories.catalogue_category.utils") as mock_utils:
            self.mock_utils = mock_utils
            yield

    def mock_has_child_elements(
        self, child_catalogue_category_data: Optional[dict] = None, child_catalogue_item_data: Optional[dict] = None
    ) -> None:
        """
        Mocks database methods appropriately for when the `has_child_elements` repo method will be called.

        :param child_catalogue_category_data: Dictionary containing a child catalogue category's data (or `None`)
        :param child_catalogue_item_data: Dictionary containing a child catalogue item's data (or `None`)
        """

        self._mock_child_catalogue_category_data = child_catalogue_category_data
        self._mock_child_catalogue_item_data = child_catalogue_item_data

        RepositoryTestHelpers.mock_find_one(self.catalogue_categories_collection, child_catalogue_category_data)
        RepositoryTestHelpers.mock_find_one(self.catalogue_items_collection, child_catalogue_item_data)

    def check_has_child_elements_performed_expected_calls(self, expected_catalogue_category_id: str) -> None:
        """
        Checks that a call to `has_child_elements` performed the expected function calls.

        :param expected_catalogue_category_id: Expected `catalogue_category_id` used in the database calls.
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
    """Base class for `create` tests."""

    _catalogue_category_in: CatalogueCategoryIn
    _expected_catalogue_category_out: CatalogueCategoryOut
    _created_catalogue_category: CatalogueCategoryOut
    _create_exception: pytest.ExceptionInfo

    def mock_create(
        self,
        catalogue_category_in_data: dict,
        parent_catalogue_category_in_data: Optional[dict] = None,
        duplicate_catalogue_category_in_data: Optional[dict] = None,
    ) -> None:
        """Mocks database methods appropriately to test the `create` repo method.

        :param catalogue_category_in_data: Dictionary containing the catalogue category data as would be required for
                                           a `CatalogueCategoryIn` database model (i.e. no ID or created and modified
                                           times required).
        :param parent_catalogue_category_in_data: Either `None` or a dictionary containing the parent catalogue category
                                                  data as would be required for a `CatalogueCategoryIn` database model.
        :param duplicate_catalogue_category_in_data: Either `None` or a dictionary containing catalogue category data
                                                     for a duplicate catalogue category.
        """

        inserted_catalogue_category_id = CustomObjectId(str(ObjectId()))

        # Pass through `CatalogueCategoryIn` first as need creation and modified times
        self._catalogue_category_in = CatalogueCategoryIn(**catalogue_category_in_data)

        self._expected_catalogue_category_out = CatalogueCategoryOut(
            **self._catalogue_category_in.model_dump(by_alias=True), id=inserted_catalogue_category_id
        )

        # When a parent_id is given, need to mock the find_one for it too
        if self._catalogue_category_in.parent_id:
            # If parent_catalogue_category_data is given as None, then it is intentionally supposed to be, otherwise
            # pass through CatalogueCategoryIn first to ensure it has creation and modified times
            RepositoryTestHelpers.mock_find_one(
                self.catalogue_categories_collection,
                (
                    {
                        **CatalogueCategoryIn(**parent_catalogue_category_in_data).model_dump(by_alias=True),
                        "_id": self._catalogue_category_in.parent_id,
                    }
                    if parent_catalogue_category_in_data
                    else None
                ),
            )
        RepositoryTestHelpers.mock_find_one(
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
        RepositoryTestHelpers.mock_insert_one(self.catalogue_categories_collection, inserted_catalogue_category_id)
        RepositoryTestHelpers.mock_find_one(
            self.catalogue_categories_collection,
            {**self._catalogue_category_in.model_dump(by_alias=True), "_id": inserted_catalogue_category_id},
        )

    def call_create(self) -> None:
        """Calls the `CatalogueCategoryRepo` `create` method with the appropriate data from a prior call to
        `mock_create`."""

        self._created_catalogue_category = self.catalogue_category_repository.create(
            self._catalogue_category_in, session=self.mock_session
        )

    def call_create_expecting_error(self, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryRepo` `create` method with the appropriate data from a prior call to `mock_create`
        while expecting an error to be raised.

        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.create(self._catalogue_category_in)
        self._create_exception = exc

    def check_create_success(self):
        """Checks that a prior call to `call_create` worked as expected."""

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

    def check_create_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_categories_collection.insert_one.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreate(CreateDSL):
    """Tests for creating a catalogue category."""

    def test_create_non_leaf_without_parent(self):
        """Test creating a non-leaf catalogue category without a parent."""

        self.mock_create(CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        self.call_create()
        self.check_create_success()

    def test_create_leaf_without_properties(self):
        """Test creating a leaf catalogue category without properties."""

        self.mock_create(CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES)
        self.call_create()
        self.check_create_success()

    def test_create_leaf_with_properties(self):
        """Test creating a leaf catalogue category with properties."""

        self.mock_create(CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM)
        self.call_create()
        self.check_create_success()

    def test_create_with_parent(self):
        """Test creating a catalogue category with a parent."""

        self.mock_create(
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": str(ObjectId())},
            parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
        )
        self.call_create()
        self.check_create_success()

    def test_create_with_non_existent_parent_id(self):
        """Test creating a catalogue category with a non-existent `parent_id`."""

        parent_id = str(ObjectId())

        self.mock_create(
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": parent_id},
            parent_catalogue_category_in_data=None,
        )
        self.call_create_expecting_error(MissingRecordError)
        self.check_create_failed_with_exception(f"No parent catalogue category found with ID: {parent_id}")

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a catalogue category with a duplicate catalogue category being found in the parent
        catalogue category."""

        self.mock_create(
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": str(ObjectId())},
            parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            duplicate_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_create_expecting_error(DuplicateRecordError)
        self.check_create_failed_with_exception(
            "Duplicate catalogue category found within the parent catalogue category"
        )


class GetDSL(CatalogueCategoryRepoDSL):
    """Base class for `get` tests"""

    _obtained_catalogue_category_id: str
    _expected_catalogue_category_out: Optional[CatalogueCategoryOut]
    _obtained_catalogue_category: Optional[CatalogueCategoryOut]
    _get_exception: pytest.ExceptionInfo

    def mock_get(self, catalogue_category_id: str, catalogue_category_in_data: Optional[dict]) -> None:
        """Mocks database methods appropriately to test the `get` repo method.

        :param catalogue_category_id: ID of the catalogue category to be obtained.
        :param catalogue_category_in_data: Either `None` or a Dictionary containing the catalogue category data as would
                                           be required for a `CatalogueCategoryIn` database model (i.e. No ID or created
                                           and modified times required).
        """

        self._expected_catalogue_category_out = (
            CatalogueCategoryOut(
                **CatalogueCategoryIn(**catalogue_category_in_data).model_dump(by_alias=True),
                id=CustomObjectId(catalogue_category_id),
            )
            if catalogue_category_in_data
            else None
        )

        RepositoryTestHelpers.mock_find_one(
            self.catalogue_categories_collection,
            self._expected_catalogue_category_out.model_dump() if self._expected_catalogue_category_out else None,
        )

    def call_get(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryRepo` `get` method with the appropriate data from a prior call to `mock_get`.

        :param catalogue_category_id: ID of the catalogue category to be obtained.
        """

        self._obtained_catalogue_category_id = catalogue_category_id
        self._obtained_catalogue_category = self.catalogue_category_repository.get(
            catalogue_category_id, session=self.mock_session
        )

    def call_get_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryRepo` `get` method with the appropriate data from a prior call to `mock_get`
        while expecting an error to be raised.

        :param catalogue_category_id: ID of the catalogue category to be obtained.
        :param error_type: Expected exception to be raised.
        """

        self._obtained_catalogue_category_id = catalogue_category_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.get(catalogue_category_id)
        self._get_exception = exc

    def check_get_success(self) -> None:
        """Checks that a prior call to `call_get` worked as expected."""

        self.catalogue_categories_collection.find_one.assert_called_once_with(
            {"_id": CustomObjectId(self._obtained_catalogue_category_id)}, session=self.mock_session
        )
        assert self._obtained_catalogue_category == self._expected_catalogue_category_out

    def check_get_failed_with_exception(self, message: str, assert_find: bool = False) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        :param assert_find: If `True` it asserts whether a `find_one` call was made, else it asserts that no call was
                            made.
        """

        if assert_find:
            self.catalogue_categories_collection.find_one.assert_called_once_with(
                {"_id": CustomObjectId(self._obtained_catalogue_category_id)}, session=None
            )
        else:
            self.catalogue_categories_collection.find_one.assert_not_called()

        assert str(self._get_exception.value) == message


class TestGet(GetDSL):
    """Tests for getting a catalogue category."""

    def test_get(self):
        """Test getting a catalogue category."""

        catalogue_category_id = str(ObjectId())

        self.mock_get(catalogue_category_id, CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        self.call_get(catalogue_category_id)
        self.check_get_success()

    def test_get_with_non_existent_id(self):
        """Test getting a catalogue category with a non-existent ID."""

        catalogue_category_id = str(ObjectId())

        self.mock_get(catalogue_category_id, None)
        self.call_get_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_get_failed_with_exception(
            f"No catalogue category found with ID: {catalogue_category_id}", assert_find=True
        )

    def test_get_with_invalid_id(self):
        """Test getting a catalogue category with an invalid ID."""

        catalogue_category_id = "invalid-id"

        self.call_get_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_get_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class GetBreadcrumbsDSL(CatalogueCategoryRepoDSL):
    """Base class for `get_breadcrumbs` tests."""

    _breadcrumbs_query_result: list[dict]
    _mock_aggregation_pipeline = MagicMock()
    _expected_breadcrumbs: MagicMock
    _obtained_catalogue_category_id: str
    _obtained_breadcrumbs: MagicMock

    def mock_breadcrumbs(self, breadcrumbs_query_result: list[dict]) -> None:
        """
        Mocks database methods appropriately to test the `get_breadcrumbs` repo method.

        :param breadcrumbs_query_result: List of dictionaries containing the breadcrumbs query result from the
                                         aggregation pipeline.
        """

        self._breadcrumbs_query_result = breadcrumbs_query_result
        self._mock_aggregation_pipeline = MagicMock()
        self._expected_breadcrumbs = MagicMock()

        self.mock_utils.create_breadcrumbs_aggregation_pipeline.return_value = self._mock_aggregation_pipeline
        self.catalogue_categories_collection.aggregate.return_value = breadcrumbs_query_result
        self.mock_utils.compute_breadcrumbs.return_value = self._expected_breadcrumbs

    def call_get_breadcrumbs(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryRepo` `get_breadcrumbs` method.

        :param catalogue_category_id: ID of the catalogue category to obtain the breadcrumbs of.
        """

        self._obtained_catalogue_category_id = catalogue_category_id
        self._obtained_breadcrumbs = self.catalogue_category_repository.get_breadcrumbs(
            catalogue_category_id, session=self.mock_session
        )

    def check_get_breadcrumbs_success(self) -> None:
        """Checks that a prior call to `call_get_breadcrumbs` worked as expected."""

        self.mock_utils.create_breadcrumbs_aggregation_pipeline.assert_called_once_with(
            entity_id=self._obtained_catalogue_category_id,
            collection_name="catalogue_categories",
            entity_type="catalogue category",
        )
        self.catalogue_categories_collection.aggregate.assert_called_once_with(
            self._mock_aggregation_pipeline, session=self.mock_session
        )
        self.mock_utils.compute_breadcrumbs.assert_called_once_with(
            list(self._breadcrumbs_query_result),
            entity_id=self._obtained_catalogue_category_id,
            collection_name="catalogue_categories",
            entity_type="catalogue category",
        )

        assert self._obtained_breadcrumbs == self._expected_breadcrumbs


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting the breadcrumbs of a catalogue category."""

    def test_get_breadcrumbs(self):
        """Test getting a catalogue category's breadcrumbs."""

        self.mock_breadcrumbs(MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH)
        self.call_get_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_success()


class ListDSL(CatalogueCategoryRepoDSL):
    """Base class for `list` tests."""

    _expected_catalogue_categories_out: list[CatalogueCategoryOut]
    _parent_id_filter: Optional[str]
    _obtained_catalogue_categories_out: list[CatalogueCategoryOut]

    def mock_list(self, catalogue_categories_in_data: list[dict]) -> None:
        """Mocks database methods appropriately to test the `list` repo method.

        :param catalogue_categories_in_data: List of dictionaries containing the catalogue category data as would be
                                             required for a `CatalogueCategoryIn` database model (i.e. no ID or created
                                             and modified times required).
        """

        self._expected_catalogue_categories_out = [
            CatalogueCategoryOut(
                **CatalogueCategoryIn(**catalogue_category_in_data).model_dump(by_alias=True), id=ObjectId()
            )
            for catalogue_category_in_data in catalogue_categories_in_data
        ]

        RepositoryTestHelpers.mock_find(
            self.catalogue_categories_collection,
            [catalogue_category_out.model_dump() for catalogue_category_out in self._expected_catalogue_categories_out],
        )

    def call_list(self, parent_id: Optional[str]) -> None:
        """
        Calls the `CatalogueCategoryRepo` `list` method.

        :param parent_id: ID of the parent catalogue category to query by, or `None`.
        """

        self._parent_id_filter = parent_id

        self._obtained_catalogue_categories_out = self.catalogue_category_repository.list(
            parent_id=parent_id, session=self.mock_session
        )

    def check_list_success(self, assert_find: bool = True) -> None:
        """Checks that a prior call to `call_list` worked as expected.

        :param assert_find: If `True` it asserts whether a `find_one` call was made, else it asserts that no call was
                            made.
        """

        self.mock_utils.list_query.assert_called_once_with(self._parent_id_filter, "catalogue categories")
        if assert_find:
            self.catalogue_categories_collection.find.assert_called_once_with(
                self.mock_utils.list_query.return_value, session=self.mock_session
            )
        else:
            self.catalogue_categories_collection.find.assert_not_called()

        assert self._obtained_catalogue_categories_out == self._expected_catalogue_categories_out


class TestList(ListDSL):
    """Tests for listing catalogue categories."""

    def test_list(self):
        """Test listing all catalogue categories."""

        self.mock_list(
            [
                CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            ]
        )
        self.call_list(parent_id=None)
        self.check_list_success()

    def test_list_with_parent_id_filter(self):
        """Test listing all catalogue categories with a given `parent_id`."""

        self.mock_list(
            [
                CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            ]
        )
        self.call_list(parent_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_null_parent_id_filter(self):
        """Test listing all catalogue categories with a 'null' `parent_id`."""

        self.mock_list(
            [
                CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            ]
        )
        self.call_list(parent_id="null")
        self.check_list_success()

    def test_list_with_parent_id_with_no_results(self):
        """Test listing all catalogue categories with a `parent_id` filter returning no results."""

        self.mock_list([])
        self.call_list(parent_id=str(ObjectId()))
        self.check_list_success()

    def test_list_with_invalid_parent_id(self):
        """Test listing all catalogue categories with an invalid `parent_id` filter returning no results."""

        self.mock_list([])
        self.mock_utils.list_query.side_effect = InvalidObjectIdError("Invalid ID")
        self.call_list(parent_id="invalid-id")
        self.check_list_success(assert_find=False)


class UpdateDSL(CatalogueCategoryRepoDSL):
    """Base class for `update` tests."""

    # pylint:disable=too-many-instance-attributes
    _catalogue_category_in: CatalogueCategoryIn
    _stored_catalogue_category_out: Optional[CatalogueCategoryOut]
    _expected_catalogue_category_out: CatalogueCategoryOut
    _updated_catalogue_category_id: str
    _updated_catalogue_category: CatalogueCategoryOut
    _moving_catalogue_category: bool
    _update_exception: pytest.ExceptionInfo

    def set_update_data(self, new_catalogue_category_in_data: dict):
        """
        Assigns the update data to use during a call to `call_update`.

        :param new_catalogue_category_in_data: New catalogue category data as would be required for a
                         `CatalogueCategoryIn` database model to supply to the `CatalogueCategoryRepo`
                         `update` method.
        """
        self._catalogue_category_in = CatalogueCategoryIn(**new_catalogue_category_in_data)

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def mock_update(
        self,
        catalogue_category_id: str,
        new_catalogue_category_in_data: dict,
        stored_catalogue_category_in_data: Optional[dict],
        new_parent_catalogue_category_in_data: Optional[dict] = None,
        duplicate_catalogue_category_in_data: Optional[dict] = None,
        valid_move_result: bool = True,
    ) -> None:
        """
        Mocks database methods appropriately to test the `update` repo method.

        :param catalogue_category_id: ID of the catalogue category that will be updated.
        :param new_catalogue_category_in_data: Dictionary containing the new catalogue category data as would be
                                               required for a `CatalogueCategoryIn` database model (i.e. no ID or
                                               created and modified times required).
        :param stored_catalogue_category_in_data: Dictionary containing the catalogue category data for the existing
                                                  stored catalogue category as would be required for a
                                                  `CatalogueCategoryIn` database model.
        :param new_parent_catalogue_category_in_data: Either `None` or a dictionary containing the new parent catalogue
                                                      category data as would be required for a `CatalogueCategoryIn`
                                                      database model.
        :param duplicate_catalogue_category_in_data: Either `None` or a dictionary containing the data for a duplicate
                                                     catalogue category as would be required for a `CatalogueCategoryIn`
                                                     database model.
        :param valid_move_result: Whether to mock in a valid or invalid move result i.e. when `True` will simulate
                                  moving the catalogue category to one of its own children.
        """
        self.set_update_data(new_catalogue_category_in_data)

        # When a parent_id is given, need to mock the find_one for it too
        if new_catalogue_category_in_data["parent_id"]:
            # If new_parent_catalogue_category_data is given as none, then it is intentionally supposed to be, otherwise
            # pass through CatalogueCategoryIn first to ensure it has creation and modified times
            RepositoryTestHelpers.mock_find_one(
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
        RepositoryTestHelpers.mock_find_one(
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
            RepositoryTestHelpers.mock_find_one(
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
        RepositoryTestHelpers.mock_find_one(
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

    def call_update(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryRepo` `update` method with the appropriate data from a prior call to `mock_update`
        (or`set_update_data`).

        :param catalogue_category_id: ID of the catalogue category to be updated.
        """

        self._updated_catalogue_category_id = catalogue_category_id
        self._updated_catalogue_category = self.catalogue_category_repository.update(
            catalogue_category_id, self._catalogue_category_in, session=self.mock_session
        )

    def call_update_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryRepo` `update` method with the appropriate data from a prior call to `mock_update`
        (or `set_update_data`) while expecting an error to be raised.

        :param catalogue_category_id: ID of the catalogue category to be updated.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.update(catalogue_category_id, self._catalogue_category_in)
        self._update_exception = exc

    def check_update_success(self) -> None:
        """Checks that a prior call to `call_update` worked as expected."""

        # Obtain a list of expected find_one calls
        expected_find_one_calls = []

        # Parent existence check
        if self._catalogue_category_in.parent_id:
            expected_find_one_calls.append(
                call({"_id": self._catalogue_category_in.parent_id}, session=self.mock_session)
            )

        # Stored catalogue category
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
                "$set": self._catalogue_category_in.model_dump(by_alias=True),
            },
            session=self.mock_session,
        )

        assert self._updated_catalogue_category == self._expected_catalogue_category_out

    def check_update_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_categories_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdate(UpdateDSL):
    """Tests for updating a catalogue category."""

    def test_update(self):
        """Test updating a catalogue category."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_no_changes(self):
        """Test updating a catalogue category to have exactly the same contents."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_parent_id(self):
        """Test updating a catalogue category's `parent_id` to move it."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id=catalogue_category_id,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                "parent_id": str(ObjectId()),
            },
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            duplicate_catalogue_category_in_data=None,
            valid_move_result=True,
        )
        self.call_update(catalogue_category_id)
        self.check_update_success()

    def test_update_parent_id_to_child_of_self(self):
        """Test updating a catalogue category's `parent_id` to a child of it self (should prevent this)."""

        catalogue_category_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id=catalogue_category_id,
            new_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                "parent_id": str(ObjectId()),
            },
            stored_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            duplicate_catalogue_category_in_data=None,
            valid_move_result=False,
        )
        self.call_update_expecting_error(catalogue_category_id, InvalidActionError)
        self.check_update_failed_with_exception("Cannot move a catalogue category to one of its own children")

    def test_update_with_non_existent_parent_id(self):
        """Test updating a catalogue category's `parent_id` to a non-existent catalogue category."""

        catalogue_category_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": new_parent_id},
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            new_parent_catalogue_category_in_data=None,
        )
        self.call_update_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_update_failed_with_exception(f"No parent catalogue category found with ID: {new_parent_id}")

    def test_update_name_to_duplicate_within_parent(self):
        """Test updating a catalogue category's name to one that is a duplicate within the parent catalogue category."""

        catalogue_category_id = str(ObjectId())
        duplicate_name = "New Duplicate Name"

        self.mock_update(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "name": duplicate_name},
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            duplicate_catalogue_category_in_data={
                **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
                "name": duplicate_name,
            },
        )
        self.call_update_expecting_error(catalogue_category_id, DuplicateRecordError)
        self.check_update_failed_with_exception(
            "Duplicate catalogue category found within the parent catalogue category"
        )

    def test_update_parent_id_with_duplicate_within_parent(self):
        """Test updating a catalogue category's `parent_id` to one that contains a catalogue category with a duplicate
        name within the parent catalogue category."""

        catalogue_category_id = str(ObjectId())
        new_parent_id = str(ObjectId())

        self.mock_update(
            catalogue_category_id,
            {**CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A, "parent_id": new_parent_id},
            CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            new_parent_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
            duplicate_catalogue_category_in_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
        )
        self.call_update_expecting_error(catalogue_category_id, DuplicateRecordError)
        self.check_update_failed_with_exception(
            "Duplicate catalogue category found within the parent catalogue category"
        )

    def test_update_with_invalid_id(self):
        """Test updating a catalogue category with an invalid ID."""

        catalogue_category_id = "invalid-id"

        self.set_update_data(CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A)
        self.call_update_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_update_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class DeleteDSL(CatalogueCategoryRepoDSL):
    """Base class for `delete` tests."""

    _delete_catalogue_category_id: str
    _delete_exception: pytest.ExceptionInfo

    def mock_delete(
        self,
        deleted_count: int,
        child_catalogue_category_data: Optional[dict] = None,
        child_catalogue_item_data: Optional[dict] = None,
    ) -> None:
        """
        Mocks database methods appropriately to test the `delete` repo method.

        :param deleted_count: Number of documents deleted successfully.
        :param child_catalogue_category_data: Dictionary containing a child catalogue category's data (or `None`).
        :param child_catalogue_item_data: Dictionary containing a child catalogue item's data (or `None`).
        """

        self.mock_has_child_elements(child_catalogue_category_data, child_catalogue_item_data)
        RepositoryTestHelpers.mock_delete_one(self.catalogue_categories_collection, deleted_count)

    def call_delete(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryRepo` `delete` method.

        :param catalogue_category_id: ID of the catalogue category to be deleted.
        """

        self._delete_catalogue_category_id = catalogue_category_id
        self.catalogue_category_repository.delete(catalogue_category_id, session=self.mock_session)

    def call_delete_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryRepo` `delete` method while expecting an error to be raised.

        :param catalogue_category_id: ID of the catalogue category to be deleted.
        :param error_type: Expected exception to be raised.
        """

        self._delete_catalogue_category_id = catalogue_category_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.delete(catalogue_category_id)
        self._delete_exception = exc

    def check_delete_success(self) -> None:
        """Checks that a prior call to `call_delete` worked as expected."""

        self.check_has_child_elements_performed_expected_calls(self._delete_catalogue_category_id)
        self.catalogue_categories_collection.delete_one.assert_called_once_with(
            {"_id": CustomObjectId(self._delete_catalogue_category_id)}, session=self.mock_session
        )

    def check_delete_failed_with_exception(self, message: str, expecting_delete_one_called: bool = False) -> None:
        """
        Checks that a prior call to `call_delete_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        :param expecting_delete_one_called: Whether the `delete_one` method is expected to be called or not.
        """

        if not expecting_delete_one_called:
            self.catalogue_categories_collection.delete_one.assert_not_called()
        else:
            self.catalogue_categories_collection.delete_one.assert_called_once_with(
                {"_id": CustomObjectId(self._delete_catalogue_category_id)}, session=None
            )

        assert str(self._delete_exception.value) == message


class TestDelete(DeleteDSL):
    """Tests for deleting a catalogue category."""

    def test_delete(self):
        """Test deleting a catalogue category."""

        self.mock_delete(deleted_count=1)
        self.call_delete(str(ObjectId()))
        self.check_delete_success()

    def test_delete_with_child_catalogue_category(self):
        """Test deleting a catalogue category when it has a child catalogue category."""

        catalogue_category_id = str(ObjectId())

        self.mock_delete(
            deleted_count=1, child_catalogue_category_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A
        )
        self.call_delete_expecting_error(catalogue_category_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(
            f"Catalogue category with ID {catalogue_category_id} has child elements and cannot be deleted"
        )

    def test_delete_with_child_catalogue_item(self):
        """Test deleting a catalogue category when it has a child catalogue item."""

        catalogue_category_id = str(ObjectId())

        self.mock_delete(deleted_count=1, child_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY)
        self.call_delete_expecting_error(catalogue_category_id, ChildElementsExistError)
        self.check_delete_failed_with_exception(
            f"Catalogue category with ID {catalogue_category_id} has child elements and cannot be deleted"
        )

    def test_delete_non_existent_id(self):
        """Test deleting a catalogue category with a non-existent ID."""

        catalogue_category_id = str(ObjectId())

        self.mock_delete(deleted_count=0)
        self.call_delete_expecting_error(catalogue_category_id, MissingRecordError)
        self.check_delete_failed_with_exception(
            f"No catalogue category found with ID: {catalogue_category_id}", expecting_delete_one_called=True
        )

    def test_delete_invalid_id(self):
        """Test deleting a catalogue category with an invalid ID."""

        catalogue_category_id = "invalid-id"

        self.call_delete_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_delete_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class HasChildElementsDSL(CatalogueCategoryRepoDSL):
    """Base class for `has_child_elements` tests"""

    _has_child_elements_catalogue_category_id: str
    _has_child_elements_result: bool
    _has_child_elements_exception: pytest.ExceptionInfo

    def call_has_child_elements(self, catalogue_category_id: str) -> None:
        """Calls the `CatalogueCategoryRepo` `has_child_elements` method.

        :param catalogue_category_id: ID of the catalogue category to check.
        """

        self._has_child_elements_catalogue_category_id = catalogue_category_id
        self._has_child_elements_result = self.catalogue_category_repository.has_child_elements(
            catalogue_category_id, session=self.mock_session
        )

    def call_has_child_elements_expecting_error(
        self, catalogue_category_id: str, error_type: type[BaseException]
    ) -> None:
        """
        Calls the `CatalogueCategoryRepo` `has_child_elements` method while expecting an error to be raised.

        :param catalogue_category_id: ID of the catalogue category to check.
        :param error_type: Expected exception to be raised.
        """

        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.has_child_elements(catalogue_category_id)
        self._has_child_elements_exception = exc

    def check_has_child_elements_success(self, expected_result: bool) -> None:
        """Checks that a prior call to `call_has_child_elements` worked as expected.

        :param expected_result: The expected result returned by `has_child_elements`.
        """

        self.check_has_child_elements_performed_expected_calls(self._has_child_elements_catalogue_category_id)

        assert self._has_child_elements_result == expected_result

    def check_has_child_elements_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_get_expecting_error` worked as expected, raising an exception with the correct
        message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_categories_collection.find_one.assert_not_called()
        self.catalogue_items_collection.find_one.assert_not_called()

        assert str(self._has_child_elements_exception.value) == message


class TestHasChildElements(HasChildElementsDSL):
    """Tests for `has_child_elements`."""

    def test_has_child_elements_with_no_children(self):
        """Test `has_child_elements` when there are no child catalogue categories or catalogue items."""

        self.mock_has_child_elements(child_catalogue_category_data=None, child_catalogue_item_data=None)
        self.call_has_child_elements(catalogue_category_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=False)

    def test_has_child_elements_with_child_catalogue_category(self):
        """Test `has_child_elements` when there is a child catalogue category but no child catalogue items."""

        self.mock_has_child_elements(
            child_catalogue_category_data=CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
            child_catalogue_item_data=None,
        )
        self.call_has_child_elements(catalogue_category_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=True)

    def test_has_child_elements_with_child_catalogue_catalogue_item(self):
        """Test `has_child_elements` when there are no child catalogue categories but there is a child catalogue
        item."""

        self.mock_has_child_elements(
            child_catalogue_category_data=None,
            child_catalogue_item_data=CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
        )
        self.call_has_child_elements(catalogue_category_id=str(ObjectId()))
        self.check_has_child_elements_success(expected_result=True)

    def test_has_child_elements_with_invalid_id(self):
        """Test `has_child_elements` with an invalid ID."""

        catalogue_category_id = "invalid-id"

        self.call_has_child_elements_expecting_error(catalogue_category_id, InvalidObjectIdError)
        self.check_has_child_elements_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class CreatePropertyDSL(CatalogueCategoryRepoDSL):
    """Base class for `create_property` tests"""

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

    def mock_create_property(self, property_in_data: dict) -> None:
        """
        Mocks database methods appropriately to test the `create_property` repo method

        :param property_in_data: Dictionary containing the catalogue category property data as would be required for a
                                 `CatalogueCategoryPropertyIn` database model
        """

        self._property_in = CatalogueCategoryPropertyIn(**property_in_data)
        self._expected_property_out = CatalogueCategoryPropertyOut(**self._property_in.model_dump(by_alias=True))

        RepositoryTestHelpers.mock_update_one(self.catalogue_categories_collection)

    def call_create_property(self, catalogue_category_id: str) -> None:
        """
        Calls the `CatalogueCategoryRepo` `create_property` method with the appropriate data from a prior call to
        `mock_create_property`

        :param catalogue_category_id: ID of the catalogue category to create the property in.
        """

        self._catalogue_category_id = catalogue_category_id
        self._created_property = self.catalogue_category_repository.create_property(
            catalogue_category_id, self._property_in, session=self.mock_session
        )

    def call_create_property_expecting_error(self, catalogue_category_id: str, error_type: type[BaseException]) -> None:
        """
        Calls the `CatalogueCategoryRepo` `create_property` method with the appropriate data from a prior call to
        `mock_create_property`

        :param catalogue_category_id: ID of the catalogue category to create the property in.
        :param error_type: Expected exception to be raised.
        """

        self._catalogue_category_id = catalogue_category_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.create_property(
                catalogue_category_id, self._property_in, session=self.mock_session
            )
        self._create_exception = exc

    def check_create_property_success(self) -> None:
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

    def check_create_property_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_create_property_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_categories_collection.update_one.assert_not_called()

        assert str(self._create_exception.value) == message


class TestCreateProperty(CreatePropertyDSL):
    """Tests for creating a property."""

    def test_create_property(self):
        """Test creating a property in an existing catalogue category."""

        self.mock_create_property(CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.call_create_property(str(ObjectId()))
        self.check_create_property_success()

    def test_create_property_with_invalid_id(self):
        """Test creating a property in a catalogue category with an invalid ID."""

        self.mock_create_property(CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.call_create_property_expecting_error("invalid-id", InvalidObjectIdError)
        self.check_create_property_failed_with_exception("Invalid ObjectId value 'invalid-id'")


class UpdatePropertyDSL(CreatePropertyDSL):
    """Base class for `update_property` tests."""

    _updated_property: CatalogueCategoryPropertyOut
    _property_id: str
    _update_exception: pytest.ExceptionInfo

    def mock_update_property(self, property_in_data: dict) -> None:
        """
        Mocks database methods appropriately to test the `update_property` repo method.

        :param property_in_data: Dictionary containing the catalogue category property data as would be required for a
                                 `CatalogueCategoryPropertyIn` database model.
        """

        self._property_in = CatalogueCategoryPropertyIn(**property_in_data)
        self._expected_property_out = CatalogueCategoryPropertyOut(**self._property_in.model_dump(by_alias=True))

        RepositoryTestHelpers.mock_update_one(self.catalogue_categories_collection)

    def call_update_property(self, catalogue_category_id: str, property_id: str) -> None:
        """
        Calls the `CatalogueCategoryRepo` `update_property` method with the appropriate data from a prior call to
        `mock_update_property`.

        :param catalogue_category_id: ID of the catalogue category that will be updated.
        :param property_id: ID of the property that will be updated.
        """

        self._catalogue_category_id = catalogue_category_id
        self._property_id = property_id
        self._updated_property = self.catalogue_category_repository.update_property(
            catalogue_category_id, property_id, self._property_in, session=self.mock_session
        )

    def call_update_property_expecting_error(
        self, catalogue_category_id: str, property_id: str, error_type: type[BaseException]
    ) -> None:
        """
        Calls the `CatalogueCategoryRepo` `update_property` method with the appropriate data from a prior call to
        `mock_update_property`.

        :param catalogue_category_id: ID of the catalogue category to be updated.
        :param property_id: ID of the property to be updated.
        :param error_type: Expected exception to be raised.
        """

        self._catalogue_category_id = catalogue_category_id
        self._property_id = property_id
        with pytest.raises(error_type) as exc:
            self.catalogue_category_repository.update_property(
                catalogue_category_id, property_id, self._property_in, session=self.mock_session
            )
        self._update_exception = exc

    def check_update_property_success(self) -> None:
        """Checks that a prior call to `call_update_property` worked as expected."""

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

    def check_update_property_failed_with_exception(self, message: str) -> None:
        """
        Checks that a prior call to `call_update_property_expecting_error` worked as expected, raising an exception
        with the correct message.

        :param message: Expected message of the raised exception.
        """

        self.catalogue_categories_collection.update_one.assert_not_called()

        assert str(self._update_exception.value) == message


class TestUpdateProperty(UpdatePropertyDSL):
    """Tests for updating a property."""

    def test_update_property(self):
        """Test updating a property in an existing catalogue category."""

        self.mock_update_property(CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.call_update_property(catalogue_category_id=str(ObjectId()), property_id=str(ObjectId()))
        self.check_update_property_success()

    def test_update_property_with_invalid_catalogue_category_id(self):
        """Test updating a property in a catalogue category with an invalid ID."""

        self.mock_update_property(CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.call_update_property_expecting_error(
            catalogue_category_id="invalid-id", property_id=str(ObjectId()), error_type=InvalidObjectIdError
        )
        self.check_update_property_failed_with_exception("Invalid ObjectId value 'invalid-id'")

    def test_update_property_with_invalid_property_id(self):
        """Test updating a property with an invalid id in a catalogue category."""

        self.mock_update_property(CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT)
        self.call_update_property_expecting_error(
            catalogue_category_id=str(ObjectId()), property_id="invalid-id", error_type=InvalidObjectIdError
        )
        self.check_update_property_failed_with_exception("Invalid ObjectId value 'invalid-id'")
