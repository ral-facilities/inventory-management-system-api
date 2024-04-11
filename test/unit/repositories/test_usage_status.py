"""
Unit tests for the `UsageStatusRepo` repository
"""

from bson import ObjectId
from inventory_management_system_api.core.custom_object_id import CustomObjectId

from inventory_management_system_api.models.usage_status import UsageStatusOut


USAGE_STATUS_A_INFO = {"value": "New"}
USAGE_STATUS_B_INFO = {"value": "Used"}


def test_list(test_helpers, database_mock, usage_status_repository):
    """
    Test getting usage statuses

    Verify that the `list` method properly handles the retrieval of usage statuses without filters
    """
    usage_status_a = UsageStatusOut(id=str(ObjectId()), **USAGE_STATUS_A_INFO)
    usage_status_b = UsageStatusOut(id=str(ObjectId()), **USAGE_STATUS_B_INFO)

    # Mock `find` to return a list of Usage statuses documents
    test_helpers.mock_find(
        database_mock.usage_statuses,
        [
            {"_id": CustomObjectId(usage_status_a.id), **USAGE_STATUS_A_INFO},
            {"_id": CustomObjectId(usage_status_b.id), **USAGE_STATUS_B_INFO},
        ],
    )

    retrieved_usage_statuses = usage_status_repository.list()

    database_mock.usage_statuses.find.assert_called_once_with()
    assert retrieved_usage_statuses == [usage_status_a, usage_status_b]
