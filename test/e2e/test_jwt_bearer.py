"""
End-to-end tests for the `JWTBearer` routers' dependency.
"""

from test.conftest import (
    INVALID_ACCESS_TOKEN,
    EXPIRED_ACCESS_TOKEN,
    VALID_ACCESS_TOKEN,
    VALID_ACCESS_TOKEN_MISSING_USERNAME,
)

import pytest
from fastapi.routing import APIRoute


@pytest.mark.parametrize(
    "headers, expected_response_message",
    [
        pytest.param(
            {"Authorization": f"Bearer {INVALID_ACCESS_TOKEN}"},
            "Invalid token or expired token",
            id="invalid_bearer_token",
        ),
        pytest.param(
            {"Authorization": f"Bearer {EXPIRED_ACCESS_TOKEN}"},
            "Invalid token or expired token",
            id="expired_bearer_token",
        ),
        pytest.param(
            {"Authorization": f"Bearer {VALID_ACCESS_TOKEN_MISSING_USERNAME}"},
            "Invalid token or expired token",
            id="missing_username_in_bearer_token",
        ),
        pytest.param(
            {"Authorization": ""},
            "Not authenticated",
            id="empty_authorization_header",
        ),
        pytest.param(
            {"Authorization": "Bearer "},
            "Not authenticated",
            id="missing_bearer_token",
        ),
        pytest.param(
            {"Authorization": f"Invalid-Bearer {VALID_ACCESS_TOKEN}"},
            "Invalid authentication credentials",
            id="invalid_authorization_scheme",
        ),
    ],
)
def test_jwt_bearer_authorization_request(test_client, headers, expected_response_message):
    """
    Test the `JWTBearer` routers' dependency on all the API routes.
    """
    api_routes = [
        api_route for api_route in test_client.app.routes if isinstance(api_route, APIRoute) and api_route.path != "/"
    ]

    for api_route in api_routes:
        if "GET" in api_route.methods:
            response = test_client.get(api_route.path, headers=headers)
            assert response.status_code == 403
            assert response.json()["detail"] == expected_response_message
        if "DELETE" in api_route.methods:
            response = test_client.delete(api_route.path, headers=headers)
            assert response.status_code == 403
            assert response.json()["detail"] == expected_response_message
        if "PATCH" in api_route.methods:
            response = test_client.patch(api_route.path, headers=headers)
            assert response.status_code == 403
            assert response.json()["detail"] == expected_response_message
        if "POST" in api_route.methods:
            response = test_client.post(api_route.path, headers=headers)
            assert response.status_code == 403
            assert response.json()["detail"] == expected_response_message
