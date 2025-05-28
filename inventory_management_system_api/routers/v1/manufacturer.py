"""
Module for providing an API router which defines routes for managing manufacturer using the `ManufacturerService`
service.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, Path, status

from inventory_management_system_api.schemas.manufacturer import (
    ManufacturerPatchSchema,
    ManufacturerPostSchema,
    ManufacturerSchema,
)
from inventory_management_system_api.services.manufacturer import ManufacturerService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/manufacturers", tags=["manufacturers"])

ManufacturerServiceDep = Annotated[ManufacturerService, Depends(ManufacturerService)]


@router.post(
    path="",
    summary="Create a new manufacturer",
    response_description="The created manufacturer",
    status_code=status.HTTP_201_CREATED,
)
def create_manufacturer(
    manufacturer: ManufacturerPostSchema, manufacturer_service: ManufacturerServiceDep
) -> ManufacturerSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new manufacturer")
    logger.debug("Manufacturer data is %s", manufacturer)
    manufacturer = manufacturer_service.create(manufacturer)
    return ManufacturerSchema(**manufacturer.model_dump())


@router.get(
    path="",
    summary="Get manufacturers",
    response_description="List of manufacturers",
)
def get_manufacturers(manufacturer_service: ManufacturerServiceDep) -> List[ManufacturerSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting manufacturers")
    manufacturers = manufacturer_service.list()
    return [ManufacturerSchema(**manufacturer.model_dump()) for manufacturer in manufacturers]


@router.get(
    path="/{manufacturer_id}",
    summary="Get a manufacturer by ID",
    response_description="Single manufacturer",
)
def get_manufacturer(
    manufacturer_id: Annotated[str, Path(description="The ID of the manufacturer to be retrieved")],
    manufacturer_service: ManufacturerServiceDep,
) -> ManufacturerSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting manufacturer with ID: %s", manufacturer_id)
    manufacturer = manufacturer_service.get(manufacturer_id)
    return ManufacturerSchema(**manufacturer.model_dump())


@router.patch(
    path="/{manufacturer_id}",
    summary="Update a manufacturer partially by ID",
    response_description="Manufacturer updated successfully",
)
def partial_update_manufacturer(
    manufacturer: ManufacturerPatchSchema,
    manufacturer_id: Annotated[str, Path(description="The ID of the manufacturer that is to be updated")],
    manufacturer_service: ManufacturerServiceDep,
) -> ManufacturerSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating manufacturer with ID: %s", manufacturer_id)
    updated_manufacturer = manufacturer_service.update(manufacturer_id, manufacturer)
    return ManufacturerSchema(**updated_manufacturer.model_dump())


@router.delete(
    path="/{manufacturer_id}",
    summary="Delete a manufacturer by ID",
    response_description="Manufacturer deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_manufacturer(
    manufacturer_id: Annotated[str, Path(description="The ID of the manufacturer that is to be deleted")],
    manufacturer_service: ManufacturerServiceDep,
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting manufacturer with ID: %s", manufacturer_id)
    manufacturer_service.delete(manufacturer_id)
