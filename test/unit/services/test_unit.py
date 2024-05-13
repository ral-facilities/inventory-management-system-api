"""
Unit tests for the `UnitService` service
"""

from unittest.mock import MagicMock
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW

from bson import ObjectId

from inventory_management_system_api.models.units import UnitIn, UnitOut
from inventory_management_system_api.schemas.unit import UnitPostRequestSchema


def test_create(
    test_helpers,
    unit_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    unit_service,
):
    """
    Testing creating a unit
    """
    # pylint: disable=duplicate-code

    unit = UnitOut(
        id=str(ObjectId()),
        value="New",
        code="new",
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )
    # pylint: enable=duplicate-code

    # Mock `create` to return the created unit
    test_helpers.mock_create(unit_repository_mock, unit)

    created_unit = unit_service.create(
        UnitPostRequestSchema(
            value=unit.value,
        )
    )
    unit_repository_mock.create.assert_called_once_with(UnitIn(value=unit.value, code=unit.code))
    assert created_unit == unit


def test_get(
    test_helpers,
    unit_repository_mock,
    unit_service,
):
    """Test getting a unit by ID"""
    unit_id = str(ObjectId())
    unit = MagicMock()

    # Mock `get` to return a unit
    test_helpers.mock_get(unit_repository_mock, unit)

    retrieved_unit = unit_service.get(unit_id)

    unit_repository_mock.get.assert_called_once_with(unit_id)
    assert retrieved_unit == unit


def test_get_with_nonexistent_id(
    test_helpers,
    unit_repository_mock,
    unit_service,
):
    """Test getting a unit with an non-existent ID"""
    unit_id = str(ObjectId())
    test_helpers.mock_get(unit_repository_mock, None)

    # Mock `get` to return a unit
    retrieved_unit = unit_service.get(unit_id)

    assert retrieved_unit is None
    unit_repository_mock.get.assert_called_once_with(unit_id)


def test_list(unit_repository_mock, unit_service):
    """
    Test listing units
    Verify that the `list` method properly calls the repository function
    """
    result = unit_service.list()

    unit_repository_mock.list.assert_called_once_with()
    assert result == unit_repository_mock.list.return_value


def test_delete(unit_repository_mock, unit_service):
    """Test deleting a unit"""
    unit_id = str(ObjectId())

    unit_service.delete(unit_id)

    unit_repository_mock.delete.assert_called_once_with(unit_id)
