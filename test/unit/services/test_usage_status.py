"""
Unit tests for the `UsageStatusService` service
"""


def test_list(usage_status_repository_mock, usage_status_service):
    """
    Test listing usage statuses

    Verify that the `list` method properly calls the repository function
    """
    result = usage_status_service.list()

    usage_status_repository_mock.list.assert_called_once_with()
    assert result == usage_status_repository_mock.list.return_value
