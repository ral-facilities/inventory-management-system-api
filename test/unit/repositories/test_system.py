"""
Unit tests for the `SystemRepo` repository
"""


from typing import Optional
from unittest.mock import MagicMock, call, patch

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildrenElementsExistError,
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.system import SystemIn, SystemOut


def _test_list(test_helpers, database_mock, system_repository, path: Optional[str], parent_path: Optional[str]):
    """
    Utility method that tests getting Systems

    Verifies that the `list` method properly handles the retrieval of systems with the given filters
    """
    # pylint: disable=duplicate-code
    system_a_info = {
        "name": "Test name a",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name-a",
        "parent_path": "/",
        "parent_id": str(ObjectId()),
    }
    system_a = SystemOut(id=str(ObjectId()), **system_a_info)
    system_b_info = {
        "name": "Test name b",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name-b",
        "parent_path": "/",
        "parent_id": str(ObjectId()),
    }
    system_b = SystemOut(id=str(ObjectId()), **system_b_info)
    # pylint: enable=duplicate-code

    # Mock `find` to return a list of System documents
    test_helpers.mock_find(
        database_mock.systems,
        [{"_id": CustomObjectId(system_a.id), **system_a_info}, {"_id": CustomObjectId(system_b.id), **system_b_info}],
    )

    retrieved_systems = system_repository.list(path, parent_path)

    expected_filters = {}
    if path:
        expected_filters["path"] = path
    if parent_path:
        expected_filters["parent_path"] = parent_path

    database_mock.systems.find.assert_called_once_with(expected_filters)
    assert retrieved_systems == [system_a, system_b]


def test_create(test_helpers, database_mock, system_repository):
    """
    Test creating a System

    Verify that the `create` method properly handles the System to be created, checks that there is not
    a duplicate System, and creates the System
    """
    # pylint: disable=duplicate-code
    system_info = {
        "name": "Test name",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name",
        "parent_path": "/",
        "parent_id": None,
    }
    system = SystemOut(id=str(ObjectId()), **system_info)
    # pylint: enable=duplicate-code

    # Mock `count_documents` to return 0 (no duplicate system found within the parent system)
    test_helpers.mock_count_documents(database_mock.systems, 0)
    # Mock `insert_one` to return an object for the inserted system document
    test_helpers.mock_insert_one(database_mock.systems, CustomObjectId(system.id))
    # Mock `find_one` to return the inserted system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {"_id": CustomObjectId(system.id), **system_info},
    )

    created_system = system_repository.create(SystemIn(**system_info))

    database_mock.systems.insert_one.assert_called_once_with(
        {**system_info},
    )
    assert created_system == system


def test_create_with_parent_id(test_helpers, database_mock, system_repository):
    """
    Test creating a System with a parent ID

    Verify that the `create` method properly handles the creation of a System with a parent ID
    """
    # pylint: disable=duplicate-code
    system_info = {
        "name": "Test name b",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name-a/test-name-b",
        "parent_path": "/test-name-a",
        "parent_id": str(ObjectId()),
    }
    system = SystemOut(id=str(ObjectId()), **system_info)

    # Mock `find_one` to return the parent system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            "_id": CustomObjectId(system.parent_id),
            "name": "Test name a",
            "location": "Test location",
            "owner": "Test owner",
            "importance": "low",
            "description": "Test description",
            "code": "test-name",
            "path": "/test-name-a",
            "parent_path": "/",
            "parent_id": None,
        },
    )
    # pylint: enable=duplicate-code
    # Mock `count_documents` to return 0 (no duplicate system found within the parent system)
    test_helpers.mock_count_documents(database_mock.systems, 0)
    # Mock `insert_one` to return an object for the inserted system document
    test_helpers.mock_insert_one(database_mock.systems, CustomObjectId(system.id))
    # Mock `find_one` to return the inserted system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {"_id": CustomObjectId(system.id), **system_info},
    )

    created_system = system_repository.create(SystemIn(**system_info))

    database_mock.systems.insert_one.assert_called_once_with(
        {**system_info, "parent_id": CustomObjectId(system.parent_id)},
    )
    database_mock.systems.find_one.assert_has_calls(
        [call({"_id": CustomObjectId(system.parent_id)}), call({"_id": CustomObjectId(system.id)})]
    )
    assert created_system == system


def test_create_with_non_existent_parent_id(test_helpers, database_mock, system_repository):
    """
    Test creating a System with a non-existent parent ID

    Verify that the `create` method properly handles a System with a non-existent parent ID
    and does not create it
    """
    # pylint: disable=duplicate-code
    system_info = {
        "name": "Test name b",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name-a/test-name-b",
        "parent_path": "/test-name-a",
        "parent_id": str(ObjectId()),
    }
    system = SystemOut(id=str(ObjectId()), **system_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to not return a parent system document
    test_helpers.mock_find_one(database_mock.systems, None)

    with pytest.raises(MissingRecordError) as exc:
        system_repository.create(SystemIn(**system_info))

    database_mock.systems.insert_one.assert_not_called()
    assert str(exc.value) == f"No parent System found with ID: {system.parent_id}"


def test_create_with_duplicate_name_within_parent(test_helpers, database_mock, system_repository):
    """
    Test creating a System with a duplicate name within the parent System

    Verify that the `create` method properly handles a System with a duplicate name
    and does not create it
    """
    # pylint: disable=duplicate-code
    system_info = {
        "name": "Test name b",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name-a/test-name-b",
        "parent_path": "/test-name-a",
        "parent_id": str(ObjectId()),
    }
    system = SystemOut(id=str(ObjectId()), **system_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the parent system document
    test_helpers.mock_find_one(
        database_mock.systems,
        {
            "_id": CustomObjectId(system.parent_id),
            "name": "Test name a",
            "location": "Test location",
            "owner": "Test owner",
            "importance": "low",
            "description": "Test description",
            "code": "test-name",
            "path": "/test-name-a",
            "parent_path": "/",
            "parent_id": None,
        },
    )
    # Mock `count_documents` to return 1 (duplicate system found within the parent system)
    test_helpers.mock_count_documents(database_mock.systems, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        system_repository.create(SystemIn(**system_info))

    database_mock.systems.insert_one.assert_not_called()
    assert str(exc.value) == "Duplicate System found within the parent System"


def test_get(test_helpers, database_mock, system_repository):
    """
    Test getting a System

    Verify that the `get` method properly handles the retrieval of a System by ID
    """
    # pylint: disable=duplicate-code
    system_info = {
        "name": "Test name a",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "code": "test-name",
        "path": "/test-name-a",
        "parent_path": "/",
        "parent_id": str(ObjectId()),
    }
    system = SystemOut(id=str(ObjectId()), **system_info)
    # pylint: enable=duplicate-code

    # Mock `find_one` to return a system
    test_helpers.mock_find_one(
        database_mock.systems,
        {"_id": CustomObjectId(system.id), **system_info},
    )

    retrieved_system = system_repository.get(system.id)

    database_mock.systems.find_one.assert_called_with({"_id": CustomObjectId(system.id)})
    assert retrieved_system == system


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

    # Mock `find_one` to not return a system document
    test_helpers.mock_find_one(database_mock.systems, None)

    retrieved_system = system_repository.get(system_id)

    database_mock.systems.find_one.assert_called_with({"_id": CustomObjectId(system_id)})
    assert retrieved_system is None


@patch("inventory_management_system_api.repositories.system.query_breadcrumbs")
def test_get_breadcrumbs(mock_query_breadcrumbs, database_mock, system_repository):
    """
    Test getting breadcrumbs for a specific system

    Verify that the 'get_breadcrumbs' method properly handles the retrieval of breadcrumbs for a system
    """
    system_id = str(ObjectId())
    mock_breadcrumbs = MagicMock()
    mock_query_breadcrumbs.return_value = mock_breadcrumbs

    retrieved_breadcrumbs = system_repository.get_breadcrumbs(system_id)

    mock_query_breadcrumbs.assert_called_once_with(
        entity_id=system_id,
        entity_collection=database_mock.systems,
        collection_name="systems",
    )
    assert retrieved_breadcrumbs == mock_breadcrumbs


def test_list(test_helpers, database_mock, system_repository):
    """
    Test getting Systems

    Verify that the `list` method properly handles the retrieval of systems without filters
    """
    _test_list(test_helpers, database_mock, system_repository, None, None)


def test_list_with_path_filter(test_helpers, database_mock, system_repository):
    """
    Test getting Systems based on the provided path filter

    Verify that the `list` method properly handles the retrieval of systems based on the provided
    path filter
    """
    _test_list(test_helpers, database_mock, system_repository, "/test-name-a", None)


def test_list_with_parent_path_filter(test_helpers, database_mock, system_repository):
    """
    Test getting Systems based on the provided parent path filter

    Verify that the `list` method properly handles the retrieval of systems based on the provided parent
    path filter
    """
    _test_list(test_helpers, database_mock, system_repository, None, "/")


def test_list_with_path_and_parent_path_filter(test_helpers, database_mock, system_repository):
    """
    Test getting Systems based on the provided path and parent path filters

    Verify that the `list` method properly handles the retrieval of systems based on the provided path
    and parent path filters
    """
    _test_list(test_helpers, database_mock, system_repository, "/test-name-a", "/")


def test_list_with_path_and_parent_path_filters_no_matching_results(test_helpers, database_mock, system_repository):
    """
    Test getting Systems based on the provided path and parent path filters when there are no matching results
    int he database

    Verify that the `list` method properly handles the retrieval of systems based on the provided path
    and parent path filters when there are no matching results in the database
    """
    # Mock `find` to return a list of System documents
    test_helpers.mock_find(database_mock.systems, [])

    retrieved_systems = system_repository.list("/test-name-a", "/")

    database_mock.systems.find.assert_called_once_with({"path": "/test-name-a", "parent_path": "/"})
    assert retrieved_systems == []


def test_delete(test_helpers, database_mock, system_repository):
    """
    Test deleting a System

    Verify that the `delete` method properly handles the deletion of a System by its ID
    """
    system_id = str(ObjectId())

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.systems, 1)

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.systems, 0)

    system_repository.delete(system_id)

    database_mock.systems.delete_one.assert_called_once_with({"_id": CustomObjectId(system_id)})


def test_delete_with_child_systems(test_helpers, database_mock, system_repository):
    """
    Test deleting a System with child Systems

    Verify that the `delete` method properly handles the deletion of a System with child Systems
    """
    system_id = str(ObjectId())

    # Mock `delete_one` to return that one document has been deleted
    test_helpers.mock_delete_one(database_mock.systems, 1)

    # Mock count_documents to return 1 (children elements found)
    test_helpers.mock_count_documents(database_mock.systems, 1)

    with pytest.raises(ChildrenElementsExistError) as exc:
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

    # Mock count_documents to return 0 (children elements not found)
    test_helpers.mock_count_documents(database_mock.systems, 0)

    with pytest.raises(MissingRecordError) as exc:
        system_repository.delete(system_id)
    assert str(exc.value) == f"No System found with ID: {system_id}"

    database_mock.systems.delete_one.assert_called_once_with({"_id": CustomObjectId(system_id)})
