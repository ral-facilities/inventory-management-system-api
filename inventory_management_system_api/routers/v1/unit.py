"""
Module for providing an API router which defines routes for managing Units using the `UnitService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Path

from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfCatalogueCategoryError,
)
from inventory_management_system_api.schemas.unit import UnitPostRequestSchema, UnitSchema
from inventory_management_system_api.services.unit import UnitService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/units", tags=["units"])


@router.post(
    path="",
    summary="Create new unit",
    response_description="The new unit",
    status_code=status.HTTP_201_CREATED,
)
def create_unit(
    unit: UnitPostRequestSchema,
    unit_service: UnitService = Depends(),
) -> UnitSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new unit")
    logger.debug("Unit data is %s", unit)

    try:
        unit = unit_service.create(unit)
        return UnitSchema(**unit.model_dump())

    except DuplicateRecordError as exc:
        message = "A unit with the same name has been found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.get(
    path="/{unit_id}",
    summary="Get a unit by ID",
    response_description="Single unit",
)
def get_unit(
    unit_id: str = Path(description="The ID of the unit to be retrieved"),
    unit_service: UnitService = Depends(),
) -> UnitSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting unit with ID %s", unit_id)
    message = "Unit not found"
    try:
        unit = unit_service.get(unit_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid object value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc

    return UnitSchema(**unit.model_dump())


@router.get(path="", summary="Get units", response_description="List of units")
def get_units(unit_service: Annotated[UnitService, Depends(UnitService)]) -> list[UnitSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting Units")

    units = unit_service.list()
    return [UnitSchema(**unit.model_dump()) for unit in units]


@router.delete(
    path="/{unit_id}",
    summary="Delete a unit by its ID",
    response_description="Unit deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_unit(unit_id: str, unit_service: UnitService = Depends()) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting unit with ID: %s", unit_id)
    try:
        unit_service.delete(unit_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        logger.exception("The specified unit does not exist")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The specified unit does not exist") from exc
    except PartOfCatalogueCategoryError as exc:
        logger.exception("The specified unit is a part of a Catalogue category")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The specified unit is a part of a Catalogue category"
        ) from exc
