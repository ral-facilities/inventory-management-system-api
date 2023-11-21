"""
Unit tests for the `SystemService` service
"""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema

SYSTEM_A_INFO = {
    "name": "Test name a",
    "location": "Test location",
    "owner": "Test owner",
    "importance": "low",
    "description": "Test description",
    "parent_id": None,
}

SYSTEM_A_INFO_FULL = {
    **SYSTEM_A_INFO,
    "code": "test-name-a",
}

SYSTEM_B_INFO = {
    "name": "Test name b",
    "location": "Test location",
    "owner": "Test owner",
    "importance": "high",
    "description": "Test description",
    "parent_id": None,
}

SYSTEM_B_INFO_FULL = {
    **SYSTEM_A_INFO,
    "code": "test-name-b",
}


def test_create(test_helpers, system_repository_mock, system_service):
    """
    Test creating a System

    Verify that the `create` method properly handles the System to be created, generates the code,
    and calls the repository's create method
    """
    system = SystemOut(id=str(ObjectId()), **SYSTEM_A_INFO_FULL)

    # Mock `create` to return the created System
    test_helpers.mock_create(system_repository_mock, system)

    created_system = system_service.create(SystemPostSchema(**SYSTEM_A_INFO))

    system_repository_mock.create.assert_called_with(SystemIn(**SYSTEM_A_INFO_FULL))
    assert created_system == system


def test_create_with_parent_id(test_helpers, system_repository_mock, system_service):
    """
    Test creating a System with a parent ID

    Verify that the `create` method properly handles the System to be created when it has a parent ID
    """
    system_info = {
        **SYSTEM_B_INFO,
        "parent_id": str(ObjectId()),
    }
    full_system_info = {
        **system_info,
        "code": SYSTEM_B_INFO_FULL["code"],
    }
    system = SystemOut(id=str(ObjectId()), **full_system_info)

    # Mock `get` to return the parent system
    test_helpers.mock_get(
        system_repository_mock,
        SystemOut(id=system.parent_id, **SYSTEM_B_INFO_FULL),
    )

    # Mock `create` to return the created System
    test_helpers.mock_create(system_repository_mock, system)

    created_system = system_service.create(SystemPostSchema(**system_info))

    system_repository_mock.create.assert_called_with(SystemIn(**full_system_info))
    assert created_system == system


def test_create_with_whitespace_name(test_helpers, system_repository_mock, system_service):
    """
    Test creating a System with a name containing leading/trailing/consecutive whitespaces

    Verify that the `create` method trims the whitespace from the System name and handles
    it correctly
    """
    system_info = {
        **SYSTEM_A_INFO,
        "name": "      Test    name         ",
    }
    full_system_info = {
        **system_info,
        "code": "test-name",
    }
    system = SystemOut(id=str(ObjectId()), **full_system_info)

    # Mock `create` to return the created System
    test_helpers.mock_create(system_repository_mock, system)

    created_system = system_service.create(SystemPostSchema(**system_info))

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


def test_get_breadcrumbs(test_helpers, system_repository_mock, system_service):
    """
    Test getting breadcrumbs for a system

    Verify that the `get_breadcrumbs` method properly handles the retrieval of a System
    """
    system_id = str(ObjectId)
    breadcrumbs = MagicMock()

    # Mock `get` to return breadcrumbs
    test_helpers.mock_get_breadcrumbs(system_repository_mock, breadcrumbs)

    retrieved_breadcrumbs = system_service.get_breadcrumbs(system_id)

    system_repository_mock.get_breadcrumbs.assert_called_once_with(system_id)
    assert retrieved_breadcrumbs == breadcrumbs


def test_list(system_repository_mock, system_service):
    """
    Test listing systems

    Verify that the `list` method properly calls the repository function with any passed filters
    """

    parent_id = MagicMock()

    result = system_service.list(parent_id=parent_id)

    system_repository_mock.list.assert_called_once_with(parent_id)
    assert result == system_repository_mock.list.return_value


def test_update(test_helpers, system_repository_mock, system_service):
    """
    Test updating a System

    Verify that the 'update' method properly handles the update of a System
    """
    system = SystemOut(id=str(ObjectId()), **SYSTEM_A_INFO_FULL)

    # Mock `get` to return a System
    test_helpers.mock_get(
        system_repository_mock,
        SystemOut(id=system.id, **{**SYSTEM_A_INFO_FULL, "name": "Different name", "code": "different-name"}),
    )
    # Mock 'update' to return the updated System
    test_helpers.mock_update(system_repository_mock, system)

    updated_system = system_service.update(system.id, SystemPatchSchema(name=system.name))

    system_repository_mock.update.assert_called_once_with(system.id, SystemIn(**SYSTEM_A_INFO_FULL))
    assert updated_system == system


def test_update_with_non_existent_id(test_helpers, system_repository_mock, system_service):
    """
    Test updating a System with a non-existent ID

    Verify that the 'update' method properly handles the update of a System with a non-existent ID
    """
    # Mock `get` to not return a System
    test_helpers.mock_get(system_repository_mock, None)

    system_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        system_service.update(system_id, MagicMock())
    assert str(exc.value) == f"No System found with ID: {system_id}"


def test_delete(system_repository_mock, system_service):
    """
    Test deleting a System

    Verify that the `delete` method properly handles the deletion of a System by ID
    """
    system_id = MagicMock()

    system_service.delete(system_id)

    system_repository_mock.delete.assert_called_once_with(system_id)
