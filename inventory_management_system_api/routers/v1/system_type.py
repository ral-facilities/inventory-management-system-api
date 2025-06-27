"""
Module for providing an API router which defines routes for managing system types using the `SystemTypeService` service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from inventory_management_system_api.schemas.system_type import SystemTypeSchema
from inventory_management_system_api.services.system_type import SystemTypeService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/system-types", tags=["system types"])

SystemTypeServiceDep = Annotated[SystemTypeService, Depends(SystemTypeService)]


@router.get(path="", summary="Get system types", response_description="List of system types")
def get_systems(
    system_type_service: SystemTypeServiceDep,
) -> list[SystemTypeSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting system types")

    system_types = system_type_service.list()
    return [SystemTypeSchema(**system_type.model_dump()) for system_type in system_types]
