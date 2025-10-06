"""
Module for providing an API router which defines routes for managing system types using the `SystemTypeService` service.
"""

# We don't define docstrings in router methods as they would end up in the openapi/swagger docs. We also expect
# some duplicate code inside routers as the code is similar between entities and error handling may be repeated.
# pylint: disable=missing-function-docstring
# pylint: disable=duplicate-code

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from inventory_management_system_api.schemas.setting import SparesDefinitionSchema
from inventory_management_system_api.services.setting import SettingService

router = APIRouter(prefix="/v1/setting", tags=["setting"])

logger = logging.getLogger()

SettingServiceDep = Annotated[SettingService, Depends(SettingService)]


@router.get(
    path="/spares-definition", summary="Get spares definition", response_description="List of spares definition"
)
def get_spares_definition(
    setting_service: SettingServiceDep,
) -> SparesDefinitionSchema:
    logger.info("Getting spares definition")

    setting = setting_service.get_spares_definition()

    if setting is None:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

    return SparesDefinitionSchema(**setting.model_dump())
