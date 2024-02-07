"""
Unit tests for the `UnitService` service
"""


def test_list(unit_repository_mock, unit_service):
    """
    Test listing units

    Verify that the `list` method properly calls the repository function
    """
    result = unit_service.list()

    unit_repository_mock.list.assert_called_once_with()
    assert result == unit_repository_mock.list.return_value
