"""
Module for providing an API router which defines routes for managing Usage statuses using the `UsageStatusService`
service.
"""

# We don't define docstrings in router methods as they would end up in the openapi/swagger docs. We also expect
# some duplicate code inside routers as the code is similar between entities and error handling may be repeated.
# pylint: disable=missing-function-docstring
# pylint: disable=duplicate-code

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from inventory_management_system_api.auth.jwt_bearer import JWTBearer
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfItemError,
    PartOfRuleError,
)
from inventory_management_system_api.schemas.usage_status import UsageStatusPostSchema, UsageStatusSchema
from inventory_management_system_api.services.usage_status import UsageStatusService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/usage-statuses", tags=["usage statuses"])

UsageStatusServiceDep = Annotated[UsageStatusService, Depends(UsageStatusService)]


@router.post(
    path="",
    summary="Create a new usage status",
    response_description="The created usage status",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(JWTBearer(check_role=True))]
)
def create_usage_status(
    usage_status: UsageStatusPostSchema, usage_status_service: UsageStatusServiceDep
) -> UsageStatusSchema:
    logger.info("Creating a new usage status")
    logger.debug("Usage status data: %s", usage_status)

    try:
        usage_status = usage_status_service.create(usage_status)
        return UsageStatusSchema(**usage_status.model_dump())

    except DuplicateRecordError as exc:
        message = "A usage status with the same value already exists"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.get(path="", summary="Get usage statuses", response_description="List of usage statuses")
def get_usage_statuses(usage_status_service: UsageStatusServiceDep) -> list[UsageStatusSchema]:
    logger.info("Getting Usage statuses")

    usage_statuses = usage_status_service.list()
    return [UsageStatusSchema(**usage_status.model_dump()) for usage_status in usage_statuses]


@router.get(
    path="/{usage_status_id}",
    summary="Get a usage status by ID",
    response_description="Single usage status",
)
def get_usage_status(
    usage_status_id: Annotated[str, Path(description="The ID of the usage status to be retrieved")],
    usage_status_service: UsageStatusServiceDep,
) -> UsageStatusSchema:
    logger.info("Getting usage status with ID %s", usage_status_id)
    message = "Usage status not found"
    try:
        usage_status = usage_status_service.get(usage_status_id)
        if not usage_status:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc

    return UsageStatusSchema(**usage_status.model_dump())


@router.delete(
    path="/{usage_status_id}",
    summary="Delete a usage status by its ID",
    response_description="Usage status deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(JWTBearer(check_role=True))]
)
def delete_usage_status(
    usage_status_id: Annotated[str, Path(description="ID of the usage status to delete")],
    usage_status_service: UsageStatusServiceDep,
) -> None:
    logger.info("Deleting usage status with ID: %s", usage_status_id)
    try:
        usage_status_service.delete(usage_status_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Usage status not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except PartOfItemError as exc:
        message = "The specified usage status is part of an item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except PartOfRuleError as exc:
        message = "The specified usage status is part of a rule"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
