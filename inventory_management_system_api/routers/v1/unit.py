"""
Module for providing an API router which defines routes for managing Units using the `UnitService`
service.
"""

# We don't define docstrings in router methods as they would end up in the openapi/swagger docs. We also expect
# some duplicate code inside routers as the code is similar between entities and error handling may be repeated.
# pylint: disable=missing-function-docstring
# pylint: disable=duplicate-code

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfCatalogueCategoryError,
)
from inventory_management_system_api.schemas.unit import UnitPostSchema, UnitSchema
from inventory_management_system_api.services.unit import UnitService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/units", tags=["units"])

UnitServiceDep = Annotated[UnitService, Depends(UnitService)]


@router.post(
    path="",
    summary="Create a new unit",
    response_description="The created unit",
    status_code=status.HTTP_201_CREATED,
)
def create_unit(unit: UnitPostSchema, unit_service: UnitServiceDep) -> UnitSchema:
    logger.info("Creating a new unit")
    logger.debug("Unit data: %s", unit)

    try:
        unit = unit_service.create(unit)
        return UnitSchema(**unit.model_dump())
    except DuplicateRecordError as exc:
        message = "A unit with the same value already exists"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.get(path="", summary="Get Units", response_description="List of Units")
def get_units(unit_service: UnitServiceDep) -> list[UnitSchema]:
    logger.info("Getting Units")

    units = unit_service.list()
    return [UnitSchema(**unit.model_dump()) for unit in units]


@router.get(
    path="/{unit_id}",
    summary="Get a unit by ID",
    response_description="Single unit",
)
def get_unit(
    unit_id: Annotated[str, Path(description="The ID of the unit to be retrieved")], unit_service: UnitServiceDep
) -> UnitSchema:
    logger.info("Getting unit with ID %s", unit_id)
    message = "Unit not found"
    try:
        unit = unit_service.get(unit_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc

    return UnitSchema(**unit.model_dump())


@router.delete(
    path="/{unit_id}",
    summary="Delete a unit by its ID",
    response_description="Unit deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_unit(
    unit_id: Annotated[str, Path(description="ID of the unit to delete")], unit_service: UnitServiceDep
) -> None:
    logger.info("Deleting unit with ID: %s", unit_id)
    try:
        unit_service.delete(unit_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Unit not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except PartOfCatalogueCategoryError as exc:
        message = "The specified unit is part of a Catalogue category"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
