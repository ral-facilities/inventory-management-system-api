"""
Module for providing an API router which defines routes for managing systems using the `SystemService` service.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DatabaseIntegrityError,
    DuplicateRecordError,
    InvalidActionError,
    InvalidObjectIdError,
    MissingRecordError,
    ObjectStorageAPIAuthError,
    ObjectStorageAPIServerError,
)
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema, SystemSchema
from inventory_management_system_api.services.system import SystemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/systems", tags=["systems"])

SystemServiceDep = Annotated[SystemService, Depends(SystemService)]


@router.post(
    path="",
    summary="Create a new system",
    response_description="The created system",
    status_code=status.HTTP_201_CREATED,
)
def create_system(system: SystemPostSchema, system_service: SystemServiceDep) -> SystemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new system")
    logger.debug("System data: %s", system)
    try:
        system = system_service.create(system)
        return SystemSchema(**system.model_dump())
    # pylint: disable=duplicate-code
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if system.type_id in str(exc) or "system type" in str(exc).lower():
            message = "The specified system type does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "The specified parent system does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A system with the same name already exists within the parent system"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except InvalidActionError as exc:
        message = str(exc)
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    # pylint: enable=duplicate-code


@router.get(path="", summary="Get systems", response_description="List of systems")
def get_systems(
    system_service: SystemServiceDep,
    parent_id: Annotated[Optional[str], Query(description="Filter systems by parent ID")] = None,
) -> list[SystemSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting Systems")
    if parent_id:
        logger.debug("Parent ID filter: '%s'", parent_id)

    try:
        systems = system_service.list(parent_id)
        return [SystemSchema(**system.model_dump()) for system in systems]
    except InvalidObjectIdError:
        # As this endpoint filters, and to hide the database behaviour, we treat any invalid id
        # the same as a valid one that doesn't exist i.e. return an empty list
        return []


@router.get(path="/{system_id}", summary="Get a system by ID", response_description="Single system")
def get_system(
    system_id: Annotated[str, Path(description="ID of the system to get")], system_service: SystemServiceDep
) -> SystemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting system with ID: %s", system_service)
    message = "System not found"
    try:
        system = system_service.get(system_id)
        if not system:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return SystemSchema(**system.model_dump())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc


@router.get(path="/{system_id}/breadcrumbs", summary="Get breadcrumbs data for a system")
def get_system_breadcrumbs(
    system_id: Annotated[str, Path(description="The ID of the system to get the breadcrumbs for")],
    system_service: SystemServiceDep,
) -> BreadcrumbsGetSchema:
    # pylint: disable=missing-function-docstring
    # pylint: disable=duplicate-code
    logger.info("Getting breadcrumbs for system with ID: %s", system_id)
    try:
        return system_service.get_breadcrumbs(system_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "System not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except DatabaseIntegrityError as exc:
        message = "Unable to obtain breadcrumbs"
        logger.exception(message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc
    # pylint: enable=duplicate-code


@router.patch(path="/{system_id}", summary="Update a system by ID", response_description="System updated successfully")
def partial_update_system(system_id: str, system: SystemPatchSchema, system_service: SystemServiceDep) -> SystemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating system with ID: %s", system_id)
    logger.debug("System data: %s", system)

    try:
        updated_system = system_service.update(system_id, system)
        return SystemSchema(**updated_system.model_dump())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if system.parent_id and system.parent_id in str(exc) or "parent system" in str(exc).lower():
            message = "The specified parent system does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if system.type_id and system.type_id in str(exc) or "system type" in str(exc).lower():
            message = "The specified system type does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "System not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A system with the same name already exists within the parent system"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    # pylint:disable=duplicate-code
    except InvalidActionError as exc:
        message = str(exc)
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    # pylint:enable=duplicate-code


@router.delete(
    path="/{system_id}",
    summary="Delete a system by ID",
    response_description="System deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_system(
    system_id: Annotated[str, Path(description="ID of the system to delete")],
    system_service: SystemServiceDep,
    request: Request,
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting system with ID: %s", system_id)
    try:
        system_service.delete(system_id, request.state.token if config.authentication.enabled else None)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "System not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildElementsExistError as exc:
        message = "System has child elements and cannot be deleted"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    # pylint: disable=duplicate-code
    except (ObjectStorageAPIAuthError, ObjectStorageAPIServerError) as exc:
        message = "Unable to delete attachments and/or images"
        logger.exception(message)

        if exc.args[0] == "Invalid token or expired token":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.args[0]) from exc

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc
    # pylint: enable=duplicate-code
