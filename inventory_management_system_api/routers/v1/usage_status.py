"""
Module for providing an API router which defines routes for managing Usage statuses using the `UsageStatusService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Path

from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfItemError,
)
from inventory_management_system_api.schemas.usage_status import UsageStatusPostRequestSchema, UsageStatusSchema
from inventory_management_system_api.services.usage_status import UsageStatusService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/usage-statuses", tags=["usage statuses"])


@router.post(
    path="",
    summary="Create a new usage status",
    response_description="The created usage status",
    status_code=status.HTTP_201_CREATED,
)
def create_usage_status(
    usage_status: UsageStatusPostRequestSchema,
    usage_status_service: Annotated[UsageStatusService, Depends(UsageStatusService)],
) -> UsageStatusSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new usage status")
    logger.debug("Usage status data: %s", usage_status)

    try:
        usage_status = usage_status_service.create(usage_status)
        return UsageStatusSchema(**usage_status.model_dump())

    except DuplicateRecordError as exc:
        message = "A usage status with the same value already exists"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.get(
    path="/{usage_status_id}",
    summary="Get a usage status by ID",
    response_description="Single usage status",
)
def get_usage_status(
    usage_status_id: Annotated[str, Path(description="The ID of the usage status to be retrieved")],
    usage_status_service: Annotated[UsageStatusService, Depends(UsageStatusService)],
) -> UsageStatusSchema:
    # pylint: disable=missing-function-docstring
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


@router.get(path="", summary="Get usage statuses", response_description="List of usage statuses")
def get_usage_statuses(
    usage_status_service: Annotated[UsageStatusService, Depends(UsageStatusService)]
) -> list[UsageStatusSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting Usage statuses")

    usage_statuses = usage_status_service.list()
    return [UsageStatusSchema(**usage_status.model_dump()) for usage_status in usage_statuses]


@router.delete(
    path="/{usage_status_id}",
    summary="Delete a usage status by its ID",
    response_description="Usage status deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_usage_status(usage_status_id: str, usage_status_service: UsageStatusService = Depends()) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting usage status with ID: %s", usage_status_id)
    try:
        usage_status_service.delete(usage_status_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Usage status not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except PartOfItemError as exc:
        message = "The specified usage status is a part of an Item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
