"""
Module for providing an implementation of the `JWTBearer` class.
"""
import logging

from fastapi import  Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


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
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        return credentials.credentials
