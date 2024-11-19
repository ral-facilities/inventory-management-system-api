"""
Module for providing an API router which defines routes for managing settings using the `SettingsService`
service.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from inventory_management_system_api.schemas.settings import SparesDefinitionPutSchema, SparesDefinitionSchema
from inventory_management_system_api.services.settings import SettingsService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/settings", tags=["settings"])

SettingsServiceDep = Annotated[SettingsService, Depends(SettingsService)]


@router.put(
    path="/spares_definition",
    summary="Update the definition of a spare",
    response_description="Spares definition updated successfully",
)
def update_spares_definition(
    spares_definition: SparesDefinitionPutSchema, settings_service: SettingsServiceDep
) -> SparesDefinitionSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Updating spares definition")
    logger.debug("Spares definition data: %s", spares_definition)

    # TODO: Supposed to have 201 for created and 200 for updated
    # TODO: Appropriate excepts/error logging
    updated_spares_definition = settings_service.update_spares_definition(spares_definition)
    return SparesDefinitionSchema(**updated_spares_definition.model_dump())
