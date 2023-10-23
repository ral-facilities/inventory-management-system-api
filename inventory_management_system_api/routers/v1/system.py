"""
Module for providing an API router which defines routes for managing Systems using the `SystemService`
service.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from inventory_management_system_api.core.exceptions import (
    ChildrenElementsExistError,
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.schemas.system import SystemRequestSchema, SystemPostRequestSchema
from inventory_management_system_api.services.system import SystemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/systems", tags=["systems"])


@router.get(path="/", summary="Get Systems", response_description="List of Systems")
def get_systems(
    path: Annotated[Optional[str], Query(description="Filter Systems by path")] = None,
    parent_path: Annotated[Optional[str], Query(description="Filter Systems by parent path")] = None,
    system_service: SystemService = Depends(),
) -> list[SystemRequestSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting Systems")
    if path:
        logger.debug("Path filter: '%s'", path)
    if parent_path:
        logger.debug("Parent path filter: '%s'", parent_path)

    systems = system_service.list(path, parent_path)
    return [SystemRequestSchema(**system.dict()) for system in systems]


@router.get(path="/{system_id}", summary="Get a System by ID", response_description="Single System")
def get_system(
    system_id: Annotated[str, Path(description="ID of the System to get")], system_service: SystemService = Depends()
) -> SystemRequestSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting System with ID: %s", system_service)
    try:
        system = system_service.get(system_id)
        if not system:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A System with such ID was not found")
        return SystemRequestSchema(**system.dict())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="A System with such ID was not found"
        ) from exc


@router.post(
    path="/",
    summary="Create a new System",
    response_description="The created System",
    status_code=status.HTTP_201_CREATED,
)
def create_system(system: SystemPostRequestSchema, system_service: SystemService = Depends()) -> SystemRequestSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new System")
    logger.debug("System data : %s", system)
    try:
        system = system_service.create(system)
        return SystemRequestSchema(**system.dict())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "The specified parent System ID does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A System with the same name already exists within the same parent System"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.delete(
    path="/{system_id}",
    summary="Delete a system by ID",
    response_description="System deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_system(
    system_id: str = Path(description="ID of the system to delete"), system_service: SystemService = Depends()
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting system with ID: %s", system_id)
    try:
        system_service.delete(system_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "System with such ID was not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildrenElementsExistError as exc:
        message = "System has child elements and cannot be deleted"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
