"""
Module for providing an implementation of the `JWTBearer` class.
"""

import logging
from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.consts import PUBLIC_KEY

logger = logging.getLogger()


class JWTBearer(HTTPBearer):
    """
    Extends the FastAPI `HTTPBearer` class to provide JSON Web Token (JWT) based authentication/authorization.
    """

    def __init__(self, auto_error: bool = True) -> None:
        """
        Initialize the `JWTBearer`.

        :param auto_error: If `True`, it automatically raises `HTTPException` if the HTTP Bearer token is not provided
            (in an `Authorization` header).
        """
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> str:
        """
        Callable method for JWT access token authentication/authorization.

        This method is called when `JWTBearer` is used as a dependency in a FastAPI route. It performs authentication/
        authorization by calling the parent class method and then verifying the JWT access token.
        :param request: The FastAPI `Request` object.
        :return: The JWT access token if authentication is successful.
        :raises HTTPException: If the supplied JWT access token is invalid or has expired.
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not self._is_jwt_access_token_valid(credentials.credentials):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token or expired token")

        request.state.token = credentials.credentials

        return credentials.credentials

    def _is_jwt_access_token_valid(self, access_token: str) -> bool:
        """
        Check if the JWT access token is valid.

        It does this by checking that it was signed by the corresponding private key and has not expired. It also
        requires the payload to contain a username.
        :param access_token: The JWT access token to check.
        :return: `True` if the JWT access token is valid and its payload contains a username, `False` otherwise.
        """
        logger.info("Checking if JWT access token is valid")
        try:
            payload = jwt.decode(access_token, PUBLIC_KEY, algorithms=[config.authentication.jwt_algorithm])
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Error decoding JWT access token")
            payload = None

        return payload is not None and "username" in payload

    def is_jwt_access_token_authorised(self, access_token: str) -> bool:
        """
        Check if the JWT access token is authorised.

        It does this by checking that the token's payload contains roles, and that (at least) one of
        these roles is one of the configured privileged_roles

        :param access_token: The JWT access token to check
        :return `True` if the JWT access token's payload contains roles, and overlaps the configured
        privileged_roles, `False` otherwise.
        """
        logging.info("Checking if JWT access token is authorised for operation")
        payload = jwt.decode(access_token, options={"verify_signature": False})
        return any(role in config.authentication.privileged_roles for role in (payload or {}).get("roles", []))
