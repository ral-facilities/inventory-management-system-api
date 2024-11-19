"""
Module for providing an API router which defines routes for managing settings using the `SettingService` service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.schemas.setting import SparesDefinitionPutSchema, SparesDefinitionSchema
from inventory_management_system_api.services.setting import SettingService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/settings", tags=["settings"])

SettingServiceDep = Annotated[SettingService, Depends(SettingService)]


@router.put(
    path="/spares_definition",
    summary="Update the definition of a spare",
    response_description="Spares definition updated successfully",
)
def update_spares_definition(
    spares_definition: SparesDefinitionPutSchema, setting_service: SettingServiceDep
) -> SparesDefinitionSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Updating spares definition")
    logger.debug("Spares definition data: %s", spares_definition)

    # TODO: Appropriate excepts/error logging
    try:
        updated_spares_definition = setting_service.set_spares_definition(spares_definition)
        return SparesDefinitionSchema(**updated_spares_definition.model_dump())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "A specified usage status does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
