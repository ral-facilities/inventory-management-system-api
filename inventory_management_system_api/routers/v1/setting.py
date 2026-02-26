"""
Module for providing an API router which defines routes for managing settings using the `SettingService` service.
"""

# We don't define docstrings in router methods as they would end up in the openapi/swagger docs. We also expect
# some duplicate code inside routers as the code is similar between entities and error handling may be repeated.
# pylint: disable=missing-function-docstring
# pylint: disable=duplicate-code

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from inventory_management_system_api.schemas.setting import InUseDefinitionSchema, SparesDefinitionSchema
from inventory_management_system_api.services.setting import SettingService

router = APIRouter(prefix="/v1/settings", tags=["settings"])

logger = logging.getLogger()

SettingServiceDep = Annotated[SettingService, Depends(SettingService)]


@router.get(
    path="/spares-definition",
    summary="Get the spares definition",
    responses={
        status.HTTP_200_OK: {"model": SparesDefinitionSchema, "description": "The spares definition"},
        status.HTTP_204_NO_CONTENT: {"model": None},
    },
)
def get_spares_definition(setting_service: SettingServiceDep):
    logger.info("Getting spares definition")

    setting = setting_service.get_spares_definition()

    if setting is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT, content=None)

    return SparesDefinitionSchema(**setting.model_dump())


@router.get(
    path="/in-use-definition",
    summary="Get the in use definition",
    responses={
        status.HTTP_200_OK: {"model": InUseDefinitionSchema, "description": "The in use definition"},
        status.HTTP_204_NO_CONTENT: {"model": None},
    },
)
def get_in_use_definition(setting_service: SettingServiceDep):
    logger.info("Getting in use definition")

    setting = setting_service.get_in_use_definition()

    if setting is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT, content=None)

    return InUseDefinitionSchema(**setting.model_dump())
