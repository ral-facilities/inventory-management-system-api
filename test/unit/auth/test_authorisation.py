"""
Unit test for the `AuthorisedDep` dependency
"""

from test.mock_data import VALID_ACCESS_TOKEN_ADMIN_ROLE, VALID_ACCESS_TOKEN_DEFAULT_ROLE
from unittest.mock import Mock, patch

import pytest
from fastapi import Request

from inventory_management_system_api.auth.authorisation import _authorised_dep

# pylint: disable=duplicate-code


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
def test_authorised_dep_returns_true_request_token_has_admin_role(jwt_decode_mock, request_mock):
    """
    Test `AuthorisedDep` with request token with admin role.
    """
    jwt_decode_mock.return_value = {
        "exp": 253402300799,
        "username": "username",
        "role": "admin",
        "userIsAdmin": False,
    }

    request_mock.headers = {"Authorization": f"Bearer {VALID_ACCESS_TOKEN_ADMIN_ROLE}"}
    assert _authorised_dep(request_mock) is True


@patch("inventory_management_system_api.auth.jwt_bearer.jwt.decode")
def test_authorised_dep_returns_true_request_token_has_default_role(jwt_decode_mock, request_mock):
    """
    Test `AuthorisedDep` with request token with admin role.
    """
    jwt_decode_mock.return_value = {
        "exp": 253402300799,
        "username": "username",
        "role": "default",
        "userIsAdmin": False,
    }

    request_mock.headers = {"Authorization": f"Bearer {VALID_ACCESS_TOKEN_DEFAULT_ROLE}"}
    assert _authorised_dep(request_mock) is False
