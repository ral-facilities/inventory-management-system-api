"""
Unit tests for the `SystemRepo` repository
"""

from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from test.unit.repositories.test_utils import (
    MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH,
    MOCK_MOVE_QUERY_RESULT_INVALID,
    MOCK_MOVE_QUERY_RESULT_VALID,
)

from typing import Optional
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
from inventory_management_system_api.models.system import SystemIn, SystemOut


SYSTEM_A_INFO = {
    "parent_id": None,
    "name": "Test name a",
    "description": "Test description",
    "location": "Test location",
    "owner": "Test owner",
    "importance": "low",
    "code": "test-name-a",
}

SYSTEM_B_INFO = {
    "parent_id": None,
    "name": "Test name b",
    "description": "Test description",
    "location": "Test location",
    "owner": "Test owner",
    "importance": "low",
    "code": "test-name-b",
}


def _test_list(test_helpers, database_mock, system_repository, parent_id: Optional[str]):
    """
    Utility method that tests getting Systems

    Verifies that the `list` method properly handles the retrieval of systems with the given filters
    """
    # pylint: disable=duplicate-code
    system_a = SystemOut(id=str(ObjectId()), **SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME)
    system_b = SystemOut(id=str(ObjectId()), **SYSTEM_B_INFO, **MOCK_CREATED_MODIFIED_TIME)
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of System documents
    test_helpers.mock_find(
        database_mock.systems,
        [
            {"_id": CustomObjectId(system_a.id), **SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME},
            {"_id": CustomObjectId(system_b.id), **SYSTEM_B_INFO, **MOCK_CREATED_MODIFIED_TIME},
        ],
    )

    retrieved_systems = system_repository.list(parent_id, session=session)

    expected_filters = {}
    if parent_id:
        expected_filters["parent_id"] = None if parent_id == "null" else ObjectId(parent_id)

    database_mock.systems.find.assert_called_once_with(expected_filters, session=session)
    assert retrieved_systems == [system_a, system_b]


def test_create(test_helpers, database_mock, system_repository):
    """
    Test creating a System

    Verify that the `create` method properly handles the System to be created, checks that there is not
    a duplicate System, and creates the System
    """
    # pylint: disable=duplicate-code
    system_in = SystemIn(
        **{
            **SYSTEM_A_INFO,
            "parent_id": None,
        }
    )
    system_info = system_in.model_dump()
    system_out = SystemOut(id=str(ObjectId()), **system_info)
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate systen found in parent system
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `insert_one` to return an object for the inserted system document
    test_helpers.mock_insert_one(database_mock.systems, CustomObjectId(system_out.id))
    # Mock `find_one` to return the inserted system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {**system_info, "_id": CustomObjectId(system_out.id)},
    )

    created_system = system_repository.create(system_in, session=session)

    database_mock.systems.insert_one.assert_called_once_with(system_info, session=session)
    assert created_system == system_out


def test_create_with_parent_id(test_helpers, database_mock, system_repository):
    """
    Test creating a System with a parent ID

    Verify that the `create` method properly handles the creation of a System with a parent ID
    """
    # pylint: disable=duplicate-code
    system_in = SystemIn(
        **{
            **SYSTEM_A_INFO,
            "parent_id": str(ObjectId()),
        }
    )
    system_info = system_in.model_dump()
    system_out = SystemOut(id=str(ObjectId()), **system_info)
    session = MagicMock()

    # Mock `find_one` to return the parent system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {**system_info, "_id": CustomObjectId(system_out.parent_id), "parent_id": None},
    )
    # pylint: enable=duplicate-code
    # Mock `find_one` to return no duplicate systen found in parent system
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `insert_one` to return an object for the inserted system document
    test_helpers.mock_insert_one(database_mock.systems, CustomObjectId(system_out.id))
    # Mock `find_one` to return the inserted system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {**system_info, "_id": CustomObjectId(system_out.id)},
    )

    created_system = system_repository.create(system_in, session=session)

    database_mock.systems.insert_one.assert_called_once_with(
        {**system_info, "parent_id": CustomObjectId(system_out.parent_id)}, session=session
    )
    database_mock.systems.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(system_out.parent_id)}, session=session),
            call({"parent_id": CustomObjectId(system_out.parent_id), "code": system_out.code}, session=session),
            call({"_id": CustomObjectId(system_out.id)}, session=session),
        ]
    )
    assert created_system == system_out


def test_create_with_non_existent_parent_id(test_helpers, database_mock, system_repository):
    """
    Test creating a System with a non-existent parent ID

    Verify that the `create` method properly handles a System with a non-existent parent ID
    and does not create it
    """
    # pylint: disable=duplicate-code
    system_in = SystemIn(
        **{
            **SYSTEM_A_INFO,
            "parent_id": str(ObjectId()),
        }
    )
    system_info = system_in.model_dump()
    system_out = SystemOut(id=str(ObjectId()), **system_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to not return a parent system document
    test_helpers.mock_find_one(database_mock.systems, None)

    with pytest.raises(MissingRecordError) as exc:
        system_repository.create(system_in)

    database_mock.systems.insert_one.assert_not_called()
    assert str(exc.value) == f"No parent System found with ID: {system_out.parent_id}"


def test_create_with_duplicate_name_within_parent(test_helpers, database_mock, system_repository):
    """
    Test creating a System with a duplicate name within the parent System

    Verify that the `create` method properly handles a System with a duplicate name
    and does not create it
    """
    # pylint: disable=duplicate-code
    system_in = SystemIn(
        **{
            **SYSTEM_A_INFO,
            "parent_id": str(ObjectId()),
        }
    )
    system_info = system_in.model_dump()
    system_out = SystemOut(id=str(ObjectId()), **system_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the parent system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {**system_info, "_id": CustomObjectId(system_out.parent_id), "parent_id": str(ObjectId())},
    )
    # Mock `find_one` to return duplicate systen found in parent system
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            **system_info,
            "_id": ObjectId(),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        system_repository.create(system_in)

    database_mock.systems.insert_one.assert_not_called()
    assert str(exc.value) == "Duplicate System found within the parent System"


def test_get(test_helpers, database_mock, system_repository):
    """
    Test getting a System

    Verify that the `get` method properly handles the retrieval of a System by ID
    """
    system_out = SystemOut(id=str(ObjectId()), **SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME)
    session = MagicMock()

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(
        database_mock.systems,
        {**SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME, "_id": CustomObjectId(system_out.id)},
    )

    retrieved_system = system_repository.get(system_out.id, session=session)

    database_mock.systems.find_one.assert_called_with({"_id": CustomObjectId(system_out.id)}, session=session)
    assert retrieved_system == system_out


def test_get_with_invalid_id(database_mock, system_repository):
    """
    Test getting a System with an invalid ID

    Verify that the `get` method properly handles the retrieval of a System with an invalid ID
    """

    with pytest.raises(InvalidObjectIdError) as exc:
        system_repository.get("invalid")
    database_mock.systems.find_one.assert_not_called()
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_non_existent_id(test_helpers, database_mock, system_repository):
    """
    Test getting a System with a non-existent ID

    Verify that the `get` method properly handles the retrieval of a System with a non-existent ID
    """
    system_id = str(ObjectId())
    session = MagicMock()

    # Mock `find_one` to not return a system document
    test_helpers.mock_find_one(database_mock.systems, None)

    retrieved_system = system_repository.get(system_id, session=session)

    database_mock.systems.find_one.assert_called_with({"_id": CustomObjectId(system_id)}, session=session)
    assert retrieved_system is None


@patch("inventory_management_system_api.repositories.system.utils")
def test_get_breadcrumbs(mock_utils, database_mock, system_repository):
    """
    Test getting breadcrumbs for a specific system

    Verify that the 'get_breadcrumbs' method properly handles the retrieval of breadcrumbs for a system
    """
    system_id = str(ObjectId())
    mock_aggregation_pipeline = MagicMock()
    mock_breadcrumbs = MagicMock()
    session = MagicMock()

    mock_utils.create_breadcrumbs_aggregation_pipeline.return_value = mock_aggregation_pipeline
    mock_utils.compute_breadcrumbs.return_value = mock_breadcrumbs
    database_mock.systems.aggregate.return_value = MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH

    retrieved_breadcrumbs = system_repository.get_breadcrumbs(system_id, session=session)

    database_mock.systems.aggregate.assert_called_once_with(mock_aggregation_pipeline, session=session)
    mock_utils.create_breadcrumbs_aggregation_pipeline.assert_called_once_with(
        entity_id=system_id, collection_name="systems"
    )
    mock_utils.compute_breadcrumbs.assert_called_once_with(
        list(MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH),
        entity_id=system_id,
        collection_name="systems",
    )
    assert retrieved_breadcrumbs == mock_breadcrumbs


def test_list(test_helpers, database_mock, system_repository):
    """
    Test getting Systems

    Verify that the `list` method properly handles the retrieval of systems without filters
    """
    _test_list(test_helpers, database_mock, system_repository, None)


def test_list_with_parent_id_filter(test_helpers, database_mock, system_repository):
    """
    Test getting Systems based on the provided parent_id filter

    Verify that the `list` method properly handles the retrieval of systems based on the provided parent
    parent_id filter
    """
    _test_list(test_helpers, database_mock, system_repository, str(ObjectId()))


def test_list_with_null_parent_id_filter(test_helpers, database_mock, system_repository):
    """
    Test getting Systems when the provided parent_id filter is "null"

    Verify that the `list` method properly handles the retrieval of systems based on the provided
    parent_id filter
    """
    _test_list(test_helpers, database_mock, system_repository, "null")


def test_list_with_parent_id_filter_no_matching_results(test_helpers, database_mock, system_repository):
    """
    Test getting Systems based on the provided parent_id filter when there are no matching results
    in the database

    Verify that the `list` method properly handles the retrieval of systems based on the provided
    parent_id filter when there are no matching results in the database
    """
    session = MagicMock()

    # Mock `find` to return a list of System documents
    test_helpers.mock_find(database_mock.systems, [])

    parent_id = ObjectId()
    retrieved_systems = system_repository.list(str(parent_id), session=session)

    database_mock.systems.find.assert_called_once_with({"parent_id": parent_id}, session=session)
    assert retrieved_systems == []


# pylint:disable=W0613
def test_list_with_invalid_parent_id_filter(test_helpers, database_mock, system_repository):
    """
    Test getting Systems when given an invalid parent_id to filter on

    Verify that the `list` method properly handles the retrieval of systems when given an invalid parent_id
    filter
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        system_repository.list("invalid")
    database_mock.systems.find.assert_not_called()
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


@patch("inventory_management_system_api.repositories.system.utils")
def test_update(utils_mock, test_helpers, database_mock, system_repository):
    """
    Test updating a System

    Verify that the `update` method properly handles the update of a System
    """
    system = SystemOut(id=str(ObjectId()), **SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME)
    session = MagicMock()

    # Mock `find_one` to return the stored System document
    test_helpers.mock_find_one(
        database_mock.systems,
        system.model_dump(),
    )

    # Mock `update_one` to return an object for the updated System document
    test_helpers.mock_update_one(database_mock.systems)

    # Mock `find_one` to return the updated System document
    system_in = SystemIn(**SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME)
    test_helpers.mock_find_one(database_mock.systems, {**system_in.model_dump(), "_id": CustomObjectId(system.id)})

    updated_system = system_repository.update(system.id, system_in, session=session)

    utils_mock.create_breadcrumbs_aggregation_pipeline.assert_not_called()
    utils_mock.is_valid_move_result.assert_not_called()

    database_mock.systems.update_one.assert_called_once_with(
        {
            "_id": CustomObjectId(system.id),
        },
        {
            "$set": {
                **system_in.model_dump(),
            },
        },
        session=session,
    )
    database_mock.systems.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(system.id)}, session=session),
            call({"_id": CustomObjectId(system.id)}, session=session),
        ]
    )
    assert updated_system == SystemOut(id=system.id, **system_in.model_dump())


@patch("inventory_management_system_api.repositories.system.utils")
def test_update_parent_id(utils_mock, test_helpers, database_mock, system_repository):
    """
    Test updating a System's parent_id

    Verify that the `update` method properly handles the update of a System when the parent id changes
    """
    parent_system_id = str(ObjectId())
    system = SystemOut(
        id=str(ObjectId()), **{**SYSTEM_A_INFO, "parent_id": parent_system_id, **MOCK_CREATED_MODIFIED_TIME}
    )
    session = MagicMock()
    new_parent_id = str(ObjectId())

    # Mock `find_one` to return a parent System document
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            **SYSTEM_B_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(new_parent_id),
        },
    )

    # Mock `find_one` to return the stored System document
    test_helpers.mock_find_one(
        database_mock.systems,
        system.model_dump(),
    )
    # Mock `find_one` to return no duplicate systems found
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `update_one` to return an object for the updated System document
    test_helpers.mock_update_one(database_mock.systems)
    # Mock `find_one` to return the updated System document
    system_in = SystemIn(**{**SYSTEM_A_INFO, "parent_id": new_parent_id, **MOCK_CREATED_MODIFIED_TIME})
    test_helpers.mock_find_one(
        database_mock.systems,
        {**system_in.model_dump(), "_id": CustomObjectId(system.id)},
    )

    # Mock utils so not moving to a child of itself
    mock_aggregation_pipeline = MagicMock()
    utils_mock.create_move_check_aggregation_pipeline.return_value = mock_aggregation_pipeline
    utils_mock.is_valid_move_result.return_value = True
    database_mock.systems.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_VALID

    updated_system = system_repository.update(system.id, system_in, session=session)

    utils_mock.create_move_check_aggregation_pipeline.assert_called_once_with(
        entity_id=system.id, destination_id=new_parent_id, collection_name="systems"
    )
    database_mock.systems.aggregate.assert_called_once_with(mock_aggregation_pipeline, session=session)
    utils_mock.is_valid_move_result.assert_called_once()

    database_mock.systems.update_one.assert_called_once_with(
        {
            "_id": CustomObjectId(system.id),
        },
        {
            "$set": {
                **system_in.model_dump(),
            },
        },
        session=session,
    )
    database_mock.systems.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(new_parent_id)}, session=session),
            call({"_id": CustomObjectId(system.id)}, session=session),
            call({"parent_id": CustomObjectId(new_parent_id), "code": system.code}, session=session),
            call({"_id": CustomObjectId(system.id)}, session=session),
        ]
    )
    assert updated_system == SystemOut(id=system.id, **{**system_in.model_dump(), "parent_id": new_parent_id})


@patch("inventory_management_system_api.repositories.system.utils")
def test_update_parent_id_moving_to_child(utils_mock, test_helpers, database_mock, system_repository):
    """
    Test updating a System's parent_id when moving to a child of itself

    Verify that the `update` method properly handles the update of a System when the new parent_id
    is a child of itself
    """
    parent_system_id = str(ObjectId())
    system = SystemOut(
        id=str(ObjectId()), **{**SYSTEM_A_INFO, "parent_id": parent_system_id, **MOCK_CREATED_MODIFIED_TIME}
    )
    new_parent_id = str(ObjectId())

    # Mock `find_one` to return a parent System document
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            **SYSTEM_B_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(new_parent_id),
        },
    )

    # Mock `find_one` to return the stored System document
    test_helpers.mock_find_one(
        database_mock.systems,
        system.model_dump(),
    )
    # Mock `find_one` to return no duplicates found
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `update_one` to return an object for the updated System document
    test_helpers.mock_update_one(database_mock.systems)
    # Mock `find_one` to return the updated System document
    system_in = SystemIn(**{**SYSTEM_A_INFO, "parent_id": new_parent_id, **MOCK_CREATED_MODIFIED_TIME})
    test_helpers.mock_find_one(
        database_mock.systems,
        {**system_in.model_dump(), "_id": CustomObjectId(system.id)},
    )

    # Mock utils so moving to a child of itself
    mock_aggregation_pipeline = MagicMock()
    utils_mock.create_move_check_aggregation_pipeline.return_value = mock_aggregation_pipeline
    utils_mock.is_valid_move_result.return_value = False
    database_mock.systems.aggregate.return_value = MOCK_MOVE_QUERY_RESULT_INVALID

    system_in = SystemIn(**{**SYSTEM_A_INFO, "parent_id": new_parent_id})

    with pytest.raises(InvalidActionError) as exc:
        system_repository.update(system.id, system_in)
    assert str(exc.value) == "Cannot move a system to one of its own children"

    utils_mock.create_move_check_aggregation_pipeline.assert_called_once_with(
        entity_id=system.id, destination_id=new_parent_id, collection_name="systems"
    )
    database_mock.systems.aggregate.assert_called_once_with(mock_aggregation_pipeline, session=None)
    utils_mock.is_valid_move_result.assert_called_once()

    database_mock.systems.update_one.assert_not_called()
    database_mock.systems.find_one.assert_has_calls(
        [
            call({"_id": CustomObjectId(new_parent_id)}, session=None),
            call({"_id": CustomObjectId(system.id)}, session=None),
            call({"parent_id": CustomObjectId(new_parent_id), "code": system.code}, session=None),
        ]
    )


def test_update_with_invalid_id(database_mock, system_repository):
    """
    Test updating a System with an invalid ID

    Verify that the `update` method properly handles the update of a System with an invalid ID
    """
    system_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        system_repository.update(system_id, MagicMock())
    assert str(exc.value) == f"Invalid ObjectId value '{system_id}'"

    database_mock.systems.update_one.assert_not_called()
    database_mock.systems.find_one.assert_not_called()


def test_update_with_non_existent_parent_id(test_helpers, database_mock, system_repository):
    """
    Test updating a System with a non-existent parent ID

    Verify that the `update` method properly handles the update of a System with a non-existent parent ID
    """
    system = SystemIn(**{**SYSTEM_A_INFO, "parent_id": str(ObjectId())})
    system_id = str(ObjectId())

    # Mock `find_one` to not return a parent System document
    test_helpers.mock_find_one(database_mock.systems, None)

    with pytest.raises(MissingRecordError) as exc:
        system_repository.update(system_id, system)
    assert str(exc.value) == f"No parent System found with ID: {system.parent_id}"

    database_mock.systems.update_one.assert_not_called()
    database_mock.systems.find_one.assert_called_once_with({"_id": system.parent_id}, session=None)


def test_update_duplicate_name_within_parent(test_helpers, database_mock, system_repository):
    """
    Test updating a System with a duplicate name within the parent System

    Verify that the `update` method properly handles the update of a System with a duplicate name in the
    parent System
    """
    system = SystemIn(**SYSTEM_A_INFO, **MOCK_CREATED_MODIFIED_TIME)
    system_id = str(ObjectId())

    # Mock `find_one` to return a parent System document
    test_helpers.mock_find_one(
        database_mock.systems, {**SYSTEM_B_INFO, "_id": CustomObjectId(system_id), **MOCK_CREATED_MODIFIED_TIME}
    )
    # Mock `find_one` to return duplicate systen found in parent system
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            **SYSTEM_B_INFO,
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(system_id),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        system_repository.update(system_id, system)
    assert str(exc.value) == "Duplicate System found within the parent System"

    database_mock.systems.update_one.assert_not_called()


def test_delete(test_helpers, database_mock, system_repository):
    """
    Test deleting a System

    Verify that the `delete` method properly handles the deletion of a System by its ID
    """
    system_id = str(ObjectId())
    session = MagicMock()

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.systems, 1)

    # Mock `find_one` to return no systems
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `find_one` to return no items
    test_helpers.mock_find_one(database_mock.items, None)

    system_repository.delete(system_id, session=session)

    database_mock.systems.delete_one.assert_called_once_with({"_id": CustomObjectId(system_id)}, session=session)


def test_delete_with_child_systems(test_helpers, database_mock, system_repository):
    """
    Test deleting a System with child Systems

    Verify that the `delete` method properly handles the deletion of a System with child Systems
    """
    system_id = str(ObjectId())

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(database_mock.systems, MagicMock())
    # Mock `find_one` to return no items
    test_helpers.mock_find_one(database_mock.items, None)

    with pytest.raises(ChildElementsExistError) as exc:
        system_repository.delete(system_id)

    database_mock.systems.delete_one.assert_not_called()
    assert str(exc.value) == f"System with ID {system_id} has child elements and cannot be deleted"


def test_delete_with_child_items(test_helpers, database_mock, system_repository):
    """
    Test deleting a System with child Items

    Verify that the `delete` method properly handles the deletion of a System with child Items
    """
    system_id = str(ObjectId())

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `find_one` to return an item (child elements found)
    test_helpers.mock_find_one(database_mock.items, MagicMock())

    with pytest.raises(ChildElementsExistError) as exc:
        system_repository.delete(system_id)

    database_mock.systems.delete_one.assert_not_called()
    assert str(exc.value) == f"System with ID {system_id} has child elements and cannot be deleted"


def test_delete_with_invalid_id(database_mock, system_repository):
    """
    Test deleting a System with an invalid ID

    Verify that the `delete` method properly handles the deletion of a System with an invalid ID
    """

    with pytest.raises(InvalidObjectIdError) as exc:
        system_repository.delete("invalid")

    database_mock.systems.delete_one.assert_not_called()
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_non_existent_id(test_helpers, database_mock, system_repository):
    """
    Test deleting a System with a non-existent ID

    Verify that the `delete` method properly handles the deletion of a System with a non-existant ID
    """
    system_id = str(ObjectId())

    # Mock `delete_one` to return that no document has been deleted
    test_helpers.mock_delete_one(database_mock.systems, 0)

    # Mock `find_one` to return no systems
    test_helpers.mock_find_one(database_mock.systems, None)
    # Mock `find_one` to return no items
    test_helpers.mock_find_one(database_mock.items, None)

    with pytest.raises(MissingRecordError) as exc:
        system_repository.delete(system_id)
    assert str(exc.value) == f"No System found with ID: {system_id}"

    database_mock.systems.delete_one.assert_called_once_with({"_id": CustomObjectId(system_id)}, session=None)
