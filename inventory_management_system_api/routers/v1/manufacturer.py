"""
Module for providing an API router which defines routes for managing manufacturer using the `ManufacturerService`
service.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, status

from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfCatalogueItemError,
)
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
    try:
        manufacturer = manufacturer_service.create(manufacturer)
        return ManufacturerSchema(**manufacturer.model_dump())
    except DuplicateRecordError as exc:
        message = "A manufacturer with the same name already exists"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


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
    message = "Manufacturer not found"
    try:
        manufacturer = manufacturer_service.get(manufacturer_id)
        if not manufacturer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return ManufacturerSchema(**manufacturer.model_dump())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc


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
    try:
        updated_manufacturer = manufacturer_service.update(manufacturer_id, manufacturer)
        return ManufacturerSchema(**updated_manufacturer.model_dump())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Manufacturer not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A manufacturer with the same name already exists"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


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
    try:
        manufacturer_service.delete(manufacturer_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Manufacturer not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except PartOfCatalogueItemError as exc:
        message = "The specified manufacturer is a part of a catalogue item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
