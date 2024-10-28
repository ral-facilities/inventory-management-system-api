"""
Unit test for the `JWTBearer` class.
"""

from test.mock_data import EXPIRED_ACCESS_TOKEN, INVALID_ACCESS_TOKEN, VALID_ACCESS_TOKEN
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request
from jwt import ExpiredSignatureError, InvalidTokenError

from inventory_management_system_api.auth.jwt_bearer import JWTBearer


@pytest.fixture(name="request_mock")
def fixture_request_mock() -> Mock:
    """
    Fixture to create an empty `Request` mock.
    :return: Mocked `Request` instance
    """
    request_mock = Mock(Request)
    request_mock.headers = {}
    return request_mock


@patch("inventory_management_system_api.auth.jwt_bearer.jwt.decode")
async def test_jwt_bearer_authorization_request(jwt_decode_mock, request_mock):
    """
    Test `JWTBearer` with valid access token.
    """
    jwt_decode_mock.return_value = {"exp": 253402300799, "username": "username"}
    request_mock.headers = {"Authorization": f"Bearer {VALID_ACCESS_TOKEN}"}

    jwt_bearer = JWTBearer()
    await jwt_bearer(request_mock)


@patch("inventory_management_system_api.auth.jwt_bearer.jwt.decode")
async def test_jwt_bearer_authorization_request_invalid_bearer_token(jwt_decode_mock, request_mock):
    """
    Test `JWTBearer` with invalid access token.
    """
    jwt_decode_mock.side_effect = InvalidTokenError()
    request_mock.headers = {"Authorization": f"Bearer {INVALID_ACCESS_TOKEN}"}

    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Invalid token or expired token"


@patch("inventory_management_system_api.auth.jwt_bearer.jwt.decode")
async def test_jwt_bearer_authorization_request_expired_bearer_token(jwt_decode_mock, request_mock):
    """
    Test `JWTBearer` with expired access token.
    """
    jwt_decode_mock.side_effect = ExpiredSignatureError()
    request_mock.headers = {"Authorization": f"Bearer {EXPIRED_ACCESS_TOKEN}"}

    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Invalid token or expired token"


@patch("inventory_management_system_api.auth.jwt_bearer.jwt.decode")
async def test_jwt_bearer_authorization_request_missing_username_in_bearer_token(jwt_decode_mock, request_mock):
    """
    Test `JWTBearer` with missing username in access token.
    """
    jwt_decode_mock.return_value = {"exp": 253402300799}
    request_mock.headers = {"Authorization": f"Bearer {VALID_ACCESS_TOKEN}"}

    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Invalid token or expired token"


async def test_jwt_bearer_authorization_request_missing_authorization_header(request_mock):
    """
    Test `JWTBearer` with missing authorization header.
    """
    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Not authenticated"


async def test_jwt_bearer_authorization_request_empty_authorization_header(request_mock):
    """
    Test `JWTBearer` with empty authorization header.
    """
    request_mock.headers = {"Authorization": ""}

    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Not authenticated"


async def test_jwt_bearer_authorization_request_missing_bearer_token(request_mock):
    """
    Test `JWTBearer` with missing access token.
    """
    request_mock.headers = {"Authorization": "Bearer "}

    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Not authenticated"


async def test_jwt_bearer_authorization_request_invalid_authorization_scheme(request_mock):
    """
    Test `JWTBearer` with invalid authorization scheme.
    """
    request_mock.headers = {"Authorization": f"Invalid-Bearer {VALID_ACCESS_TOKEN}"}

    jwt_bearer = JWTBearer()

    with pytest.raises(HTTPException) as exc:
        await jwt_bearer(request_mock)
    assert str(exc.value) == "403: Invalid authentication credentials"
