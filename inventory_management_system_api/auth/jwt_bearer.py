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

    def __init__(self, check_role: bool, auto_error: bool = True) -> None:
        """
        Initialize the `JWTBearer`.

        :param auto_error: If `True`, it automatically raises `HTTPException` if the HTTP Bearer token is not provided
            (in an `Authorization` header).
        """
        super().__init__(auto_error=auto_error)
        self.check_role = check_role

    async def __call__(self, request: Request) -> str:
        """
        Callable method for JWT access token authentication/authorization.

        This method is called when `JWTBearer` is used as a dependency in a FastAPI route. It performs authentication/
        authorization by calling the parent class method and then verifying the JWT access token, and optionally verifying
        the role in the tokens payload
        :param request: The FastAPI `Request` object.
        :param check_role: If `True` the token's payload role will be verified to ensure it is authorised for the route
        :return: The JWT access token if authentication is successful.
        :raises HTTPException: If the supplied JWT access token is invalid or has expired; or if the user's role does not
        authorise them to make the request
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        token_payload = self._decode_jwt_access_token(credentials.credentials)

        if not self._is_jwt_access_token_valid(token_payload):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token or expired token")
        
        if self.check_role and not self._is_jwt_access_token_authorised(token_payload):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorised to perform this operation")

        request.state.token = credentials.credentials

        return credentials.credentials

    def _is_jwt_access_token_valid(self, payload: Any) -> bool:
        """
        Check if the JWT access token is valid.

        It does this by checking that it was signed by the corresponding private key and has not expired. It also
        requires the payload to contain a username.
        :param payload: The JWT access token to check.
        :return: `True` if the JWT access token is valid and its payload contains a username, `False` otherwise.
        """
        logger.info("Checking if JWT access token is valid")
        print(payload)
        return payload is not None and "username" in payload
        
    
    def _is_jwt_access_token_authorised(self, payload: Any) -> bool:
        """
        Check if the JWT access token is authorised.

        It does this by checking that the token's payload contains roles, and that (at least) one of these roles is one of
        the configured privileged_roles

        :param payload: The JWT access token's payload to check
        :return `True` if the JWT access token's payload contains roles, and overlaps the configured privileged_roles, `False` otherwise.
        """
        logging.info("Checking if JWT access token is authorised")
        return payload is not None and "roles" in payload and any(role in config.authentication.privileged_roles for role in payload["roles"])


    def _decode_jwt_access_token(self, access_token: str) -> Any | None:
        """
        Decode the given access token, returning the payload

        :param access_token: The JWT access token to decode.
        :return The payload of the given token, `None` if there is an error decoding the token.
        """
        try:
            payload = jwt.decode(access_token, PUBLIC_KEY, algorithms=[config.authentication.jwt_algorithm])
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Error decoding JWT access token")
            payload = None

        return payload

