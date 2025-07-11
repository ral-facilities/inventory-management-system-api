"""
Module for providing an API router which defines routes for managing Units using the `UnitService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

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
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new unit")
    logger.debug("Unit data: %s", unit)

    unit = unit_service.create(unit)
    return UnitSchema(**unit.model_dump())


@router.get(
    path="/{unit_id}",
    summary="Get a unit by ID",
    response_description="Single unit",
)
def get_unit(
    unit_id: Annotated[str, Path(description="The ID of the unit to be retrieved")], unit_service: UnitServiceDep
) -> UnitSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting unit with ID %s", unit_id)

    unit = unit_service.get(unit_id)
    return UnitSchema(**unit.model_dump())


@router.get(path="", summary="Get Units", response_description="List of Units")
def get_units(unit_service: UnitServiceDep) -> list[UnitSchema]:
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
def delete_unit(
    unit_id: Annotated[str, Path(description="ID of the unit to delete")], unit_service: UnitServiceDep
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting unit with ID: %s", unit_id)
    unit_service.delete(unit_id)
