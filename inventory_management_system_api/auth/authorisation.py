"""
Module for providing an implementation of the `AuthorisedDep` dependency, which is then used in various routes.
"""

from typing import Annotated
from fastapi import Depends, Request
from inventory_management_system_api.auth.jwt_bearer import JWTBearer
from inventory_management_system_api.core.config import config

def _authorised_dep(request: Request) -> bool:
    if config.authentication.enabled is True:
        jwt_bearer = JWTBearer()
        return jwt_bearer.is_jwt_access_token_authorised(request.state.token)
    return True

AuthorisedDep = Annotated[bool, Depends(_authorised_dep)]