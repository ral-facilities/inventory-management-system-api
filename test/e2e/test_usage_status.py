"""
End-to-End tests for the Usage status router
"""

from test.e2e.mock_schemas import USAGE_STATUSES_EXPECTED


def test_get_usage_statuses(test_client):
    """
    Test getting a list of Usage statuses
    """

    response = test_client.get("/v1/usage_statuses")

    assert response.status_code == 200
    assert response.json() == USAGE_STATUSES_EXPECTED
