import logging

from fastapi import APIRouter, Depends, HTTPException, status
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
)

from inventory_management_system_api.schemas.system import SystemGetRequestSchema, SystemPostRequestSchema
from inventory_management_system_api.services.system import SystemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/systems", tags=["systems"])


@router.post(
    path="/",
    summary="Create a new System",
    response_description="The created System",
    status_code=status.HTTP_201_CREATED,
)
def create_system(system: SystemPostRequestSchema, system_service: SystemService = Depends()) -> SystemGetRequestSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new System")
    logger.debug("System data : %s", system)
    try:
        system = system_service.create(system)
        return SystemGetRequestSchema(**system.dict())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "The specified catalogue category ID does not exist in the database"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A System with the same name already exists within the catalogue category"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
