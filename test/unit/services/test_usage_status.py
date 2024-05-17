"""
Unit tests for the `UsageStatusService` service
"""

from unittest.mock import MagicMock
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW

from bson import ObjectId

from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.schemas.usage_status import UsageStatusPostRequestSchema


def test_create(
    test_helpers,
    usage_status_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    usage_status_service,
):
    """
    Testing creating a usage status
    """
    # pylint: disable=duplicate-code

    usage_status = UsageStatusOut(
        id=str(ObjectId()),
        value="New",
        code="new",
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )
    # pylint: enable=duplicate-code

    # Mock `create` to return the created usage status
    test_helpers.mock_create(usage_status_repository_mock, usage_status)

    created_usage_status = usage_status_service.create(
        UsageStatusPostRequestSchema(
            value=usage_status.value,
        )
    )
    usage_status_repository_mock.create.assert_called_once_with(
        UsageStatusIn(value=usage_status.value, code=usage_status.code)
    )
    assert created_usage_status == usage_status


def test_get(
    test_helpers,
    usage_status_repository_mock,
    usage_status_service,
):
    """Test getting a usage_status by ID"""
    usage_status_id = str(ObjectId())
    usage_status = MagicMock()

    # Mock `get` to return a usage status
    test_helpers.mock_get(usage_status_repository_mock, usage_status)

    retrieved_usage_status = usage_status_service.get(usage_status_id)

    usage_status_repository_mock.get.assert_called_once_with(usage_status_id)
    assert retrieved_usage_status == usage_status


def test_get_with_non_existent_id(
    test_helpers,
    usage_status_repository_mock,
    usage_status_service,
):
    """Test getting a usage status with an non-existent ID"""
    usage_status_id = str(ObjectId())
    test_helpers.mock_get(usage_status_repository_mock, None)

    # Mock `get` to return a usage status
    retrieved_usage_status = usage_status_service.get(usage_status_id)

    assert retrieved_usage_status is None
    usage_status_repository_mock.get.assert_called_once_with(usage_status_id)


def test_list(usage_status_repository_mock, usage_status_service):
    """
    Test listing usage statuses

    Verify that the `list` method properly calls the repository function
    """
    result = usage_status_service.list()

    usage_status_repository_mock.list.assert_called_once_with()
    assert result == usage_status_repository_mock.list.return_value
