# pylint: disable=too-many-lines
"""
Unit tests for the `CatalogueCategoryRepo` repository.
"""
from test.unit.repositories.mock_models import MOCK_CATALOGUE_ITEM_PROPERTY_A_INFO, MOCK_CREATED_MODIFIED_TIME
from test.unit.repositories.test_catalogue_item import FULL_CATALOGUE_ITEM_A_INFO
from test.unit.repositories.test_utils import (
    MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH,
    MOCK_MOVE_QUERY_RESULT_VALID,
)
from unittest.mock import MagicMock, call, patch

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

CATALOGUE_CATEGORY_INFO = {
    "name": "Category A",
    "code": "category-a",
    "is_leaf": False,
    "parent_id": None,
    "properties": [],
}


def test_create(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category.

    Verify that the `create` method properly handles the catalogue category to be created, checks that there is not a
    duplicate catalogue category, and creates the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category_in = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
    )
    catalogue_category_info = catalogue_category_in.model_dump(by_alias=True)
    catalogue_category_out = CatalogueCategoryOut(id=str(ObjectId()), **catalogue_category_info)
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category_out.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_info,
            "_id": CustomObjectId(catalogue_category_out.id),
        },
    )

    created_catalogue_category = catalogue_category_repository.create(catalogue_category_in, session=session)

    database_mock.catalogue_categories.insert_one.assert_called_once_with(catalogue_category_info, session=session)
    assert created_catalogue_category == catalogue_category_out


def test_create_leaf_category_without_properties(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a leaf catalogue category without .

    Verify that the `create` method properly handles the catalogue category to be created, checks that there is not a
    duplicate catalogue category, and creates the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category_in = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[],
    )
    catalogue_category_info = catalogue_category_in.model_dump(by_alias=True)
    catalogue_category_out = CatalogueCategoryOut(id=str(ObjectId()), **catalogue_category_info)
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category_out.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {**catalogue_category_info, "_id": CustomObjectId(catalogue_category_out.id)},
    )

    created_catalogue_category = catalogue_category_repository.create(catalogue_category_in, session=session)

    database_mock.catalogue_categories.insert_one.assert_called_once_with(catalogue_category_info, session=session)
    assert created_catalogue_category == catalogue_category_out


def test_create_leaf_category_with_properties(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a leaf catalogue category with .

    Verify that the `create` method properly handles the catalogue category to be created, checks that there is not a
    duplicate catalogue category, and creates the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category_in = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=None,
        properties=[
            CatalogueCategoryPropertyIn(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueCategoryPropertyIn(name="Property B", type="boolean", mandatory=True),
        ],
    )
    catalogue_category_info = catalogue_category_in.model_dump(by_alias=True)
    catalogue_category_out = CatalogueCategoryOut(id=str(ObjectId()), **catalogue_category_info)
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category_out.id))
    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_info,
            "_id": CustomObjectId(catalogue_category_out.id),
        },
    )

    created_catalogue_category = catalogue_category_repository.create(catalogue_category_in, session=session)

    database_mock.catalogue_categories.insert_one.assert_called_once_with(catalogue_category_info, session=session)
    assert created_catalogue_category == catalogue_category_out


def test_create_with_parent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a parent ID.

    Verify that the `create` method properly handles a catalogue category with a parent ID.
    """
    # pylint: disable=duplicate-code
    catalogue_category_in = CatalogueCategoryIn(
        name="Category B",
        code="category-b",
        is_leaf=True,
        parent_id=str(ObjectId()),
        properties=[
            CatalogueCategoryPropertyIn(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueCategoryPropertyIn(name="Property B", type="boolean", mandatory=True),
        ],
    )
    catalogue_category_info = catalogue_category_in.model_dump(by_alias=True)
    catalogue_category_out = CatalogueCategoryOut(id=str(ObjectId()), **catalogue_category_info)
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_info,
            "_id": CustomObjectId(catalogue_category_out.parent_id),
        },
    )

    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    # Mock `insert_one` to return an object for the inserted catalogue category document
    test_helpers.mock_insert_one(database_mock.catalogue_categories, CustomObjectId(catalogue_category_out.id))

    # Mock `find_one` to return the inserted catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_info,
            "_id": CustomObjectId(catalogue_category_out.id),
        },
    )

    created_catalogue_category = catalogue_category_repository.create(catalogue_category_in, session=session)

    database_mock.catalogue_categories.insert_one.assert_called_once_with(catalogue_category_info, session=session)
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(catalogue_category_out.parent_id)}, session=session),
            call(
                {
                    "parent_id": CustomObjectId(catalogue_category_out.parent_id),
                    "code": catalogue_category_out.code,
                    "_id": {"$ne": None},
                },
                session=session,
            ),
            call({"_id": CustomObjectId(catalogue_category_out.id)}, session=session),
        ]
    )
    assert created_catalogue_category == catalogue_category_out


def test_create_with_non_existent_parent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a non-existent parent ID.

    Verify that the `create` method properly handles a catalogue category with a non-existent parent ID, does not find a
    parent catalogue category with an ID specified by `parent_id`, and does not create the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category_in = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=str(ObjectId()),
        properties=[],
    )
    catalogue_category_info = catalogue_category_in.model_dump(by_alias=True)
    catalogue_category_out = CatalogueCategoryOut(id=str(ObjectId()), **catalogue_category_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to not return a parent catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.create(catalogue_category_in)

    database_mock.catalogue_categories.insert_one.assert_not_called()
    assert str(exc.value) == f"No parent catalogue category found with ID: {catalogue_category_out.parent_id}"


def test_create_with_duplicate_name_within_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.

    Verify that the `create` method properly handles a catalogue category with a duplicate name, finds that there is a
    duplicate catalogue category, and does not create the catalogue category.
    """
    # pylint: disable=duplicate-code
    catalogue_category_in = CatalogueCategoryIn(
        name="Category B",
        code="category-b",
        is_leaf=True,
        parent_id=str(ObjectId()),
        properties=[
            CatalogueCategoryPropertyIn(name="Property A", type="number", unit="mm", mandatory=False),
            CatalogueCategoryPropertyIn(name="Property B", type="boolean", mandatory=True),
        ],
    )
    catalogue_category_info = catalogue_category_in.model_dump(by_alias=True)
    catalogue_category_out = CatalogueCategoryOut(id=str(ObjectId()), **catalogue_category_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_info,
            "_id": CustomObjectId(catalogue_category_out.parent_id),
        },
    )
    # Mock `find_one` to return duplicate catalogue category found
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_info,
            "_id": ObjectId(),
            "parent_id": CustomObjectId(catalogue_category_out.parent_id),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_category_repository.create(catalogue_category_in)

    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"
    database_mock.catalogue_categories.find_one.assert_called_with(
        {
            "parent_id": CustomObjectId(catalogue_category_out.parent_id),
            "code": catalogue_category_out.code,
            "_id": {"$ne": None},
        },
        session=None,
    )


def test_delete(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category.

    Verify that the `delete` method properly handles the deletion of a catalogue category by ID.
    """
    catalogue_category_id = str(ObjectId())
    session = MagicMock()

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_categories, 1)

    # Mock `find_one` to return no child catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    catalogue_category_repository.delete(catalogue_category_id, session=session)

    database_mock.catalogue_categories.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}, session=session
    )


def test_delete_with_child_catalogue_categories(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with child catalogue categories.

    Verify that the `delete` method properly handles the deletion of a catalogue category with child catalogue
    categories.
    """
    catalogue_category_id = str(ObjectId())

    # Mock find_one to return children catalogue category found
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "parent_id": catalogue_category_id,
        },
    )
    # Mock find_one to return no children catalogue items found
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    with pytest.raises(ChildElementsExistError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == (
        f"Catalogue category with ID {catalogue_category_id} has child elements and cannot be deleted"
    )


def test_delete_with_child_catalogue_items(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with child catalogue items.

    Verify that the `delete` method properly handles the deletion of a catalogue category with child catalogue items.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `find_one` to return no child catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # pylint: disable=duplicate-code
    # Mock `find_one` to return the child catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            **FULL_CATALOGUE_ITEM_A_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_category_id": CustomObjectId(catalogue_category_id),
        },
    )
    # pylint: enable=duplicate-code
    with pytest.raises(ChildElementsExistError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == (
        f"Catalogue category with ID {catalogue_category_id} has child elements and cannot be deleted"
    )


def test_delete_with_invalid_id(catalogue_category_repository):
    """
    Test deleting a catalogue category with an invalid ID.

    Verify that the `delete` method properly handles the deletion of a catalogue category with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.delete("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_non_existent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test deleting a catalogue category with a non-existent ID.

    Verify that the `delete` method properly handles the deletion of a catalogue category with a non-existent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `delete_one` to return that no document has been deleted
    test_helpers.mock_delete_one(database_mock.catalogue_categories, 0)

    # Mock `find_one` to return no child catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.delete(catalogue_category_id)
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"
    database_mock.catalogue_categories.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}, session=None
    )


def test_get(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting a catalogue category.

    Verify that the `get` method properly handles the retrieval of a catalogue category by ID.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(catalogue_category.id),
            "name": catalogue_category.name,
            "code": catalogue_category.code,
            "is_leaf": catalogue_category.is_leaf,
            "parent_id": catalogue_category.parent_id,
            "properties": catalogue_category.properties,
        },
    )

    retrieved_catalogue_category = catalogue_category_repository.get(catalogue_category.id, session=session)

    database_mock.catalogue_categories.find_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.id)}, session=session
    )
    assert retrieved_catalogue_category == catalogue_category


def test_get_with_invalid_id(catalogue_category_repository):
    """
    Test getting a catalogue category with an invalid ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with an invalid ID.
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_non_existent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting a catalogue category with a non-existent ID.

    Verify that the `get` method properly handles the retrieval of a catalogue category with a non-existent ID.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `find_one` to not return a catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    retrieved_catalogue_category = catalogue_category_repository.get(catalogue_category_id)

    assert retrieved_catalogue_category is None
    database_mock.catalogue_categories.find_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)}, session=None
    )


@patch("inventory_management_system_api.repositories.catalogue_category.utils")
def test_get_breadcrumbs(mock_utils, database_mock, catalogue_category_repository):
    """
    Test getting breadcrumbs for a specific catalogue category

    Verify that the 'get_breadcrumbs' method properly handles the retrieval of breadcrumbs for a catalogue
    category
    """
    catalogue_category_id = str(ObjectId())
    mock_aggregation_pipeline = MagicMock()
    mock_breadcrumbs = MagicMock()

    mock_utils.create_breadcrumbs_aggregation_pipeline.return_value = mock_aggregation_pipeline
    mock_utils.compute_breadcrumbs.return_value = mock_breadcrumbs
    database_mock.catalogue_categories.aggregate.return_value = MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH

    retrieved_breadcrumbs = catalogue_category_repository.get_breadcrumbs(catalogue_category_id)

    mock_utils.create_breadcrumbs_aggregation_pipeline.assert_called_once_with(
        entity_id=catalogue_category_id, collection_name="catalogue_categories"
    )
    mock_utils.compute_breadcrumbs.assert_called_once_with(
        list(MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH),
        entity_id=catalogue_category_id,
        collection_name="catalogue_categories",
    )
    assert retrieved_breadcrumbs == mock_breadcrumbs


def test_list(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories.

    Verify that the `list` method properly handles the retrieval of catalogue categories without filters.
    """
    # pylint: disable=duplicate-code
    catalogue_category_a = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )

    catalogue_category_b = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue category documents
    test_helpers.mock_find(
        database_mock.catalogue_categories,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_category_a.id),
                "name": catalogue_category_a.name,
                "code": catalogue_category_a.code,
                "is_leaf": catalogue_category_a.is_leaf,
                "parent_id": catalogue_category_a.parent_id,
                "properties": catalogue_category_a.properties,
            },
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_category_b.id),
                "name": catalogue_category_b.name,
                "code": catalogue_category_b.code,
                "is_leaf": catalogue_category_b.is_leaf,
                "parent_id": catalogue_category_b.parent_id,
                "properties": catalogue_category_b.properties,
            },
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list(None, session=session)

    database_mock.catalogue_categories.find.assert_called_once_with({}, session=session)
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_parent_id_filter(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided parent_id filter.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided
    parent_id filter.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue category documents
    test_helpers.mock_find(
        database_mock.catalogue_categories,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_category.id),
                "name": catalogue_category.name,
                "code": catalogue_category.code,
                "is_leaf": catalogue_category.is_leaf,
                "parent_id": catalogue_category.parent_id,
                "properties": catalogue_category.properties,
            }
        ],
    )

    parent_id = ObjectId()
    retrieved_catalogue_categories = catalogue_category_repository.list(str(parent_id), session=session)

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_id": parent_id}, session=session)
    assert retrieved_catalogue_categories == [catalogue_category]


def test_list_with_null_parent_id_filter(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories when the provided parent_id filter is "null"

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided parent
    parent_id filter.
    """
    # pylint: disable=duplicate-code
    catalogue_category_a = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )

    catalogue_category_b = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of catalogue category documents
    test_helpers.mock_find(
        database_mock.catalogue_categories,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_category_a.id),
                "name": catalogue_category_a.name,
                "code": catalogue_category_a.code,
                "is_leaf": catalogue_category_a.is_leaf,
                "parent_id": catalogue_category_a.parent_id,
                "properties": catalogue_category_a.properties,
            },
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_category_b.id),
                "name": catalogue_category_b.name,
                "code": catalogue_category_b.code,
                "is_leaf": catalogue_category_b.is_leaf,
                "parent_id": catalogue_category_b.parent_id,
                "properties": catalogue_category_b.properties,
            },
        ],
    )

    retrieved_catalogue_categories = catalogue_category_repository.list("null", session=session)

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_id": None}, session=session)
    assert retrieved_catalogue_categories == [catalogue_category_a, catalogue_category_b]


def test_list_with_parent_id_filter_no_matching_results(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue categories based on the provided parent_id filter when there is no matching
    results in the database.

    Verify that the `list` method properly handles the retrieval of catalogue categories based on the provided
    parent_id filter when there are no matching results in the database
    """
    session = MagicMock()

    # Mock `find` to return an empty list of catalogue category documents
    test_helpers.mock_find(database_mock.catalogue_categories, [])

    parent_id = ObjectId()
    retrieved_catalogue_categories = catalogue_category_repository.list(str(parent_id), session=session)

    database_mock.catalogue_categories.find.assert_called_once_with({"parent_id": parent_id}, session=session)
    assert retrieved_catalogue_categories == []


# pylint:disable=W0613
def test_list_with_invalid_parent_id_filter(test_helpers, database_mock, catalogue_category_repository):
    """
    Test getting catalogue_categories when given an invalid parent_id to filter on

    Verify that the `list` method properly handles the retrieval of catalogue categories when given an invalid
    parent_id filter
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.list("invalid")
    database_mock.catalogue_categories.find.assert_not_called()
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_update(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category.

    Verify that the `update` method properly handles the catalogue category to be updated, checks that the catalogue
    category does not have child elements, there is not a duplicate catalogue category, and updates the catalogue
    category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="Category B",
        code="category-b",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(catalogue_category.id),
            "is_leaf": catalogue_category.is_leaf,
            "parent_id": catalogue_category.parent_id,
            "properties": catalogue_category.properties,
        },
    )
    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # Mock `update_one` to return an object for the updated catalogue category document
    test_helpers.mock_update_one(database_mock.catalogue_categories)
    # pylint: disable=duplicate-code
    # Mock `find_one` to return the updated catalogue category document
    catalogue_category_in = CatalogueCategoryIn(
        **MOCK_CREATED_MODIFIED_TIME,
        name=catalogue_category.name,
        code=catalogue_category.code,
        is_leaf=catalogue_category.is_leaf,
        parent_id=catalogue_category.parent_id,
        properties=catalogue_category.properties,
    )
    # pylint: enable=duplicate-code
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_in.model_dump(by_alias=True),
            "_id": CustomObjectId(catalogue_category.id),
        },
    )

    updated_catalogue_category = catalogue_category_repository.update(
        catalogue_category.id, catalogue_category_in, session=session
    )

    database_mock.catalogue_categories.update_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.id)},
        {
            "$set": {
                **catalogue_category_in.model_dump(by_alias=True),
            }
        },
        session=session,
    )
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
            call(
                {
                    "parent_id": catalogue_category.parent_id,
                    "code": catalogue_category.code,
                    "_id": {"$ne": CustomObjectId(catalogue_category.id)},
                },
                session=session,
            ),
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
        ]
    )
    assert updated_catalogue_category == CatalogueCategoryOut(
        id=catalogue_category.id, **catalogue_category_in.model_dump(by_alias=True)
    )


@patch("inventory_management_system_api.repositories.catalogue_category.utils")
def test_update_parent_id(utils_mock, test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category's parent_id

    Verify that the `update` method properly handles the update of a catalogue category when the
    parent_id changes
    """
    parent_catalogue_category_id = str(ObjectId())
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        **{**CATALOGUE_CATEGORY_INFO, "parent_id": parent_catalogue_category_id, **MOCK_CREATED_MODIFIED_TIME},
    )
    session = MagicMock()
    new_parent_id = str(ObjectId())
    expected_catalogue_category = CatalogueCategoryOut(
        **{**catalogue_category.model_dump(), "parent_id": new_parent_id}
    )

    # Mock `find_one` to return a parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(new_parent_id),
        },
    )
    # Mock `find_one` to return the stored catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        catalogue_category.model_dump(),
    )
    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # Mock `update_one` to return an object for the updated catalogue category document
    test_helpers.mock_update_one(database_mock.catalogue_categories)
    # Mock `find_one` to return the updated catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {**catalogue_category.model_dump(), "parent_id": CustomObjectId(new_parent_id)},
    )

    # Mock utils so not moving to a child of itself
    mock_aggregation_pipeline = MagicMock()
    utils_mock.create_move_check_aggregation_pipeline.return_value = mock_aggregation_pipeline
    utils_mock.is_valid_move_result.return_value = True
    database_mock.catalogue_categories.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_VALID

    catalogue_category_in = CatalogueCategoryIn(
        **{**CATALOGUE_CATEGORY_INFO, "parent_id": new_parent_id, **MOCK_CREATED_MODIFIED_TIME}
    )
    updated_catalogue_category = catalogue_category_repository.update(
        catalogue_category.id, catalogue_category_in, session=session
    )

    utils_mock.create_move_check_aggregation_pipeline.assert_called_once_with(
        entity_id=catalogue_category.id, destination_id=new_parent_id, collection_name="catalogue_categories"
    )
    database_mock.catalogue_categories.aggregate.assert_called_once_with(mock_aggregation_pipeline, session=session)
    utils_mock.is_valid_move_result.assert_called_once()

    database_mock.catalogue_categories.update_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.id)},
        {"$set": {**catalogue_category_in.model_dump(by_alias=True)}},
        session=session,
    )
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(new_parent_id)}, session=session),
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
            call(
                {
                    "parent_id": CustomObjectId(new_parent_id),
                    "code": catalogue_category.code,
                    "_id": {"$ne": CustomObjectId(catalogue_category.id)},
                },
                session=session,
            ),
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
        ]
    )
    assert updated_catalogue_category == expected_catalogue_category


@patch("inventory_management_system_api.repositories.catalogue_category.utils")
def test_update_parent_id_moving_to_child(utils_mock, test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category's parent_id when moving to a child of itself

    Verify that the `update` method properly handles the update of a catalogue category when the new
    parent_id is a child of itself
    """
    parent_catalogue_category_id = str(ObjectId())
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        **{**CATALOGUE_CATEGORY_INFO, "parent_id": parent_catalogue_category_id, **MOCK_CREATED_MODIFIED_TIME},
    )
    session = MagicMock()
    new_parent_id = str(ObjectId())

    # Mock `find_one` to return a parent catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(new_parent_id),
        },
    )
    # Mock `find_one` to return the stored catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        catalogue_category.model_dump(),
    )
    # Mock `find_one` to return no duplicate catalogue categories found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # Mock `update_one` to return an object for the updated catalogue category document
    test_helpers.mock_update_one(database_mock.catalogue_categories)
    # Mock `find_one` to return the updated catalogue category document
    catalogue_category_in = CatalogueCategoryIn(
        **{**CATALOGUE_CATEGORY_INFO, "parent_id": new_parent_id, **MOCK_CREATED_MODIFIED_TIME}
    )
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_in.model_dump(by_alias=True),
            "_id": CustomObjectId(catalogue_category.id),
            "parent_id": CustomObjectId(new_parent_id),
        },
    )

    # Mock utils so not moving to a child of itself
    mock_aggregation_pipeline = MagicMock()
    utils_mock.create_move_check_aggregation_pipeline.return_value = mock_aggregation_pipeline
    utils_mock.is_valid_move_result.return_value = False
    database_mock.catalogue_categories.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_VALID

    with pytest.raises(InvalidActionError) as exc:
        catalogue_category_repository.update(catalogue_category.id, catalogue_category_in, session=session)
    assert str(exc.value) == "Cannot move a catalogue category to one of its own children"

    utils_mock.create_move_check_aggregation_pipeline.assert_called_once_with(
        entity_id=catalogue_category.id, destination_id=new_parent_id, collection_name="catalogue_categories"
    )
    database_mock.catalogue_categories.aggregate.assert_called_once_with(mock_aggregation_pipeline, session=session)
    utils_mock.is_valid_move_result.assert_called_once()

    database_mock.catalogue_categories.update_one.assert_not_called()
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(new_parent_id)}, session=session),
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
            call(
                {
                    "parent_id": CustomObjectId(new_parent_id),
                    "code": catalogue_category.code,
                    "_id": {"$ne": CustomObjectId(catalogue_category.id)},
                },
                session=session,
            ),
        ]
    )


def test_update_with_invalid_id(catalogue_category_repository):
    """
    Test updating a catalogue category with invalid ID.

    Verify that the `update` method properly handles the update of a catalogue category with an invalid ID.
    """
    update_catalogue_category = MagicMock()
    catalogue_category_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert str(exc.value) == f"Invalid ObjectId value '{catalogue_category_id}'"


def test_update_with_non_existent_parent_id(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with non-existent parent ID.

    Verify that the `update` method properly handles the update of a catalogue category with non-existent parent ID.
    """
    # pylint: disable=duplicate-code
    update_catalogue_category = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=False,
        parent_id=str(ObjectId()),
        properties=[],
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to not return a parent catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    with pytest.raises(MissingRecordError) as exc:
        catalogue_category_repository.update(str(ObjectId()), update_catalogue_category)
    assert str(exc.value) == f"No parent catalogue category found with ID: {update_catalogue_category.parent_id}"


def test_update_duplicate_name_within_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with a duplicate name within the parent catalogue category.

    Verify that the `update` method properly handles the update of a catalogue category with a duplicate name in a
    parent catalogue category.
    """
    # pylint: disable=duplicate-code
    update_catalogue_category = CatalogueCategoryIn(
        name="Category B",
        code="category-B",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    # pylint: enable=duplicate-code

    catalogue_category_id = str(ObjectId())
    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(catalogue_category_id),
            "is_leaf": update_catalogue_category.is_leaf,
            "parent_id": update_catalogue_category.parent_id,
            "properties": update_catalogue_category.properties,
        },
    )
    # Mock `find_one` to return duplicate catalogue category found
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": ObjectId(),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"


def test_update_duplicate_name_within_new_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category with a duplicate name within a new parent catalogue category.

    Verify that the `update` method properly handles the update of a catalogue category with a duplicate name in a new
    parent catalogue category.
    """
    update_catalogue_category = CatalogueCategoryIn(
        name="Category A",
        code="category-a",
        is_leaf=True,
        parent_id=str(ObjectId()),
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )

    # Mock `find_one` to return a parent catalogue category document
    # pylint: disable=duplicate-code
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": update_catalogue_category.parent_id,
            "name": "Category B",
            "code": "category-b",
            "is_leaf": False,
            "parent_id": None,
            "properties": [],
            **MOCK_CREATED_MODIFIED_TIME,
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category_id = str(ObjectId())
    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            "_id": CustomObjectId(catalogue_category_id),
            "name": update_catalogue_category.name,
            "code": update_catalogue_category.code,
            "is_leaf": update_catalogue_category.is_leaf,
            "parent_id": None,
            "properties": update_catalogue_category.properties,
            **MOCK_CREATED_MODIFIED_TIME,
        },
    )
    # Mock `find_one` to return duplicate catalogue category found
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": ObjectId(),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_category_repository.update(catalogue_category_id, update_catalogue_category)
    assert str(exc.value) == "Duplicate catalogue category found within the parent catalogue category"


def test_update_change_capitalisation_of_name_within_parent(test_helpers, database_mock, catalogue_category_repository):
    """
    Test updating a catalogue category when the code is the same and the capitalisation of the name has changed.

    Verify that the `update` method properly handles the catalogue category to be updated, checks that the catalogue
    category does not have child elements, there is not a duplicate catalogue category, and updates the catalogue
    category.
    """
    # pylint: disable=duplicate-code
    catalogue_category = CatalogueCategoryOut(
        id=str(ObjectId()),
        name="CaTeGoRy a",
        code="category-a",
        is_leaf=False,
        parent_id=None,
        properties=[],
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a catalogue category document
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(catalogue_category.id),
            "is_leaf": catalogue_category.is_leaf,
            "parent_id": catalogue_category.parent_id,
            "properties": catalogue_category.properties,
        },
    )
    # Mock `find_one` to return None as a duplicate was not found
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # Mock `update_one` to return an object for the updated catalogue category document
    test_helpers.mock_update_one(database_mock.catalogue_categories)
    # pylint: disable=duplicate-code
    # Mock `find_one` to return the updated catalogue category document
    catalogue_category_in = CatalogueCategoryIn(
        **MOCK_CREATED_MODIFIED_TIME,
        name=catalogue_category.name,
        code=catalogue_category.code,
        is_leaf=catalogue_category.is_leaf,
        parent_id=catalogue_category.parent_id,
        properties=catalogue_category.properties,
    )
    # pylint: enable=duplicate-code
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **catalogue_category_in.model_dump(by_alias=True),
            "_id": CustomObjectId(catalogue_category.id),
        },
    )

    updated_catalogue_category = catalogue_category_repository.update(
        catalogue_category.id, catalogue_category_in, session=session
    )

    database_mock.catalogue_categories.update_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category.id)},
        {
            "$set": {
                **catalogue_category_in.model_dump(by_alias=True),
            }
        },
        session=session,
    )
    database_mock.catalogue_categories.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
            call(
                {
                    "parent_id": catalogue_category.parent_id,
                    "code": catalogue_category.code,
                    "_id": {"$ne": CustomObjectId(catalogue_category.id)},
                },
                session=session,
            ),
            call({"_id": CustomObjectId(catalogue_category.id)}, session=session),
        ]
    )
    assert updated_catalogue_category == CatalogueCategoryOut(
        id=catalogue_category.id, **catalogue_category_in.model_dump(by_alias=True)
    )


def test_has_child_elements_with_no_child_categories(test_helpers, database_mock, catalogue_category_repository):
    """
    Test has_child_elements returns false when there are no child categories
    """
    # Mock `find_one` to return no child catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    result = catalogue_category_repository.has_child_elements(ObjectId())

    assert not result


def test_has_child_elements_with_child_categories(test_helpers, database_mock, catalogue_category_repository):
    """
    Test has_child_elements returns true when there are child categories
    """

    catalogue_category_id = str(ObjectId())

    # Mock find_one to return 1 (child catalogue categories found)
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "parent_id": catalogue_category_id,
        },
    )
    # Mock find_one to return 0 (child catalogue items not found)
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    result = catalogue_category_repository.has_child_elements(catalogue_category_id)

    assert result


def test_has_child_elements_with_child_catalogue_items(test_helpers, database_mock, catalogue_category_repository):
    """
    Test has_child_elements returns true when there are child catalogue items.
    """
    catalogue_category_id = str(ObjectId())

    # Mock `find_one` to return no child catalogue category document
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)
    # pylint: disable=duplicate-code
    # Mock `find_one` to return the child catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            **FULL_CATALOGUE_ITEM_A_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_category_id": CustomObjectId(catalogue_category_id),
        },
    )
    # pylint: enable=duplicate-code
    result = catalogue_category_repository.has_child_elements(catalogue_category_id)

    assert result


@patch("inventory_management_system_api.repositories.catalogue_category.datetime")
def test_create_property(datetime_mock, test_helpers, database_mock, catalogue_category_repository):
    """
    Test create_property performs the correct database update query
    """
    session = MagicMock()
    catalogue_category_id = str(ObjectId())
    property_in = CatalogueCategoryPropertyIn(**MOCK_CATALOGUE_ITEM_PROPERTY_A_INFO)

    # Mock 'update_one'
    test_helpers.mock_update_one(database_mock.catalogue_categories)

    result = catalogue_category_repository.create_property(catalogue_category_id, property_in, session=session)

    database_mock.catalogue_categories.update_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_category_id)},
        {
            "$push": {"properties": property_in.model_dump(by_alias=True)},
            "$set": {"modified_time": datetime_mock.now.return_value},
        },
        session=session,
    )
    assert result == CatalogueCategoryPropertyOut(**property_in.model_dump(by_alias=True))


def test_create_property_with_invalid_id(database_mock, catalogue_category_repository):
    """
    Test create_property performs the correct database update query when given an invalid id
    """

    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.create_property(
            "invalid", CatalogueCategoryPropertyIn(**MOCK_CATALOGUE_ITEM_PROPERTY_A_INFO)
        )
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"
    database_mock.catalogue_categories.update_one.assert_not_called()


@patch("inventory_management_system_api.repositories.catalogue_category.datetime")
def test_update_property(datetime_mock, test_helpers, database_mock, catalogue_category_repository):
    """
    Test update_property performs the correct database update query
    """
    session = MagicMock()
    catalogue_category_id = str(ObjectId())
    property_id = str(ObjectId())
    property_in = CatalogueCategoryPropertyIn(**MOCK_CATALOGUE_ITEM_PROPERTY_A_INFO)

    # Mock 'update_one'
    test_helpers.mock_update_one(database_mock.catalogue_categories)

    result = catalogue_category_repository.update_property(
        catalogue_category_id, property_id, property_in, session=session
    )

    database_mock.catalogue_categories.update_one.assert_called_once_with(
        {
            "_id": CustomObjectId(catalogue_category_id),
            "properties._id": CustomObjectId(property_id),
        },
        {
            "$set": {
                "properties.$[elem]": property_in.model_dump(by_alias=True),
                "modified_time": datetime_mock.now.return_value,
            },
        },
        array_filters=[{"elem._id": CustomObjectId(property_id)}],
        session=session,
    )
    assert result == CatalogueCategoryPropertyOut(**property_in.model_dump(by_alias=True))


def test_update_property_with_invalid_catalogue_category_id(database_mock, catalogue_category_repository):
    """
    Test update_property performs the correct database update query when given an invalid catalogue
    category id
    """

    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.update_property(
            "invalid", str(ObjectId()), CatalogueCategoryPropertyIn(**MOCK_CATALOGUE_ITEM_PROPERTY_A_INFO)
        )
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"
    database_mock.catalogue_categories.update_one.assert_not_called()


def test_update_property_with_invalid_property_id(database_mock, catalogue_category_repository):
    """
    Test update_property performs the correct database update query when given an invalid catalogue
    item property id
    """

    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_category_repository.update_property(
            str(ObjectId()), "invalid", CatalogueCategoryPropertyIn(**MOCK_CATALOGUE_ITEM_PROPERTY_A_INFO)
        )
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"
    database_mock.catalogue_categories.update_one.assert_not_called()
