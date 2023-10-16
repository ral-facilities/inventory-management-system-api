"""
Unit tests for the `SystemService` service
"""

from typing import Optional
from unittest.mock import MagicMock

from bson import ObjectId

from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.schemas.system import SystemPostRequestSchema


def _test_list(test_helpers, system_repository_mock, system_service, parent_id: Optional[str]):
    """
    Utility method that tests getting Systems

    Verifies that the `list` method properly handles the retrieval of systems with the given filters
    """
    systems = [MagicMock(), MagicMock()]

    # Mock `list` to return a list of systems
    test_helpers.mock_list(
        system_repository_mock,
        systems,
    )

    retrieved_systems = system_service.list(parent_id)

    system_repository_mock.list.assert_called_once_with(parent_id)
    assert retrieved_systems == systems


def test_create(test_helpers, system_repository_mock, system_service):
    """
    Test creating a System

    Verify that the `create` method properly handles the System to be created, generates the code and paths,
    and calls the repository's create method
    """
    # pylint: disable=duplicate-code
    system_info = {
        "name": "Test name",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "parent_id": None,
    }
    full_system_info = {
        **system_info,
        "code": "test-name",
        "path": "/test-name",
        "parent_path": "/",
    }
    system = SystemOut(id=str(ObjectId()), **full_system_info)
    # pylint: enable=duplicate-code

    # Mock `create` to return the created System
    test_helpers.mock_create(system_repository_mock, system)

    created_system = system_service.create(SystemPostRequestSchema(**system_info))

    system_repository_mock.create.assert_called_with(SystemIn(**full_system_info))
    assert created_system == system


def test_delete(system_repository_mock, system_service):
    """
    Test deleting a System

    Verify that the `delete` method properly handles the deletion of a System by ID
    """
    system_id = MagicMock()

    system_service.delete(system_id)

    system_repository_mock.delete.assert_called_once_with(system_id)


def test_create_with_parent_id(test_helpers, system_repository_mock, system_service):
    """
    Test creating a System with a parent ID

    Verify that the `create` method properly handles the System to be created when it has a parent ID
    """
    system_info = {
        "name": "Test name b",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "parent_id": str(ObjectId()),
    }
    full_system_info = {
        **system_info,
        "code": "test-name-b",
        "path": "/test-name-a/test-name-b",
        "parent_path": "/test-name-a",
    }
    system = SystemOut(id=str(ObjectId()), **full_system_info)

    # Mock `get` to return the parent system
    test_helpers.mock_get(
        system_repository_mock,
        SystemOut(
            id=system.parent_id,
            name="Test name a",
            location="Test location",
            owner="Test owner",
            importance="low",
            description="Test description",
            parent_id=None,
            code="test-name-a",
            path="/test-name-a",
            parent_path="/",
        ),
    )

    # Mock `create` to return the created System
    test_helpers.mock_create(system_repository_mock, system)

    created_system = system_service.create(SystemPostRequestSchema(**system_info))

    system_repository_mock.create.assert_called_with(SystemIn(**full_system_info))
    assert created_system == system


def test_create_with_whitespace_name(test_helpers, system_repository_mock, system_service):
    """
    Test creating a System with a name containing leading/trailing/consecutive whitespaces

    Verify that the `create` method trims the whitespace from the System name and handles
    it correctly
    """
    system_info = {
        "name": "      Test    name         ",
        "location": "Test location",
        "owner": "Test owner",
        "importance": "low",
        "description": "Test description",
        "parent_id": None,
    }
    full_system_info = {
        **system_info,
        "code": "test-name",
        "path": "/test-name",
        "parent_path": "/",
    }
    system = SystemOut(id=str(ObjectId()), **full_system_info)

    # Mock `create` to return the created System
    test_helpers.mock_create(system_repository_mock, system)

    created_system = system_service.create(SystemPostRequestSchema(**system_info))

    system_repository_mock.create.assert_called_with(SystemIn(**full_system_info))
    assert created_system == system


def test_get(test_helpers, system_repository_mock, system_service):
    """
    Test getting a System

    Verify that the `get` method properly handles the retrieval of a System
    """

    system_id = str(ObjectId())
    system = MagicMock()

    # Mock `get` to return a System
    test_helpers.mock_get(system_repository_mock, system)

    retrieved_system = system_service.get(system_id)

    system_repository_mock.get.assert_called_once_with(system_id)
    assert retrieved_system == system


def test_get_with_non_existent_id(test_helpers, system_repository_mock, system_service):
    """
    Test getting a System with a non-existent ID

    Verify that the `get` method properly handles the retrieval of a System with a non-existent ID
    """
    system_id = str(ObjectId())

    # Mock `get` to not return a System
    test_helpers.mock_get(system_repository_mock, None)

    retrieved_system = system_service.get(system_id)

    system_repository_mock.get.assert_called_once_with(system_id)
    assert retrieved_system is None


def test_list(test_helpers, system_repository_mock, system_service):
    """
    Test getting Systems

    Verify that the `list` method properly handles the retrieval of Systems without filters
    """
    _test_list(test_helpers, system_repository_mock, system_service, None)


def test_list_with_parent_id_filter(test_helpers, system_repository_mock, system_service):
    """
    Test getting Systems based on the provided parent_id filter

    Verify that the `list` method properly handles the retrieval of Systems based on the provided parent_id filter
    """
    _test_list(test_helpers, system_repository_mock, system_service, str(ObjectId()))


def test_list_with_null_parent_id_filter(test_helpers, system_repository_mock, system_service):
    """
    Test getting Systems based on the provided parent_id filter

    Verify that the `list` method properly handles the retrieval of Systems based on the provided parent_id filter
    """
    _test_list(test_helpers, system_repository_mock, system_service, "null")


def test_list_with_path_and_parent_path_filters_no_matching_results(
    test_helpers, system_repository_mock, system_service
):
    """
    Test getting Systems based on the provided parent path and parent path filters when there is no
    matching results in the database

    Verify that the `list` method properly handles the retrieval of Systems based on the provided path and
    parent path filters when there is no matching results in the database
    """

    # Mock `list` to return an empty list of Systems
    test_helpers.mock_list(system_repository_mock, [])

    parent_id = str(ObjectId())
    retrieved_systems = system_service.list(parent_id)

    system_repository_mock.list.assert_called_once_with(parent_id)
    assert retrieved_systems == []
