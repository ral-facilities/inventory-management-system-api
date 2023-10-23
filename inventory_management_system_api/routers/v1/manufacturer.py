"""
Module for providing an API router which defines routes for managing manufacturer using the
`Manufacturer` service.
"""
import logging
from typing import List
from fastapi import APIRouter, status, Depends, HTTPException
from inventory_management_system_api.core.exceptions import DuplicateRecordError, InvalidObjectIdError

from inventory_management_system_api.schemas.manufacturer import ManufacturerPostRequestSchema, ManufacturerSchema
from inventory_management_system_api.services.manufacturer import ManufacturerService


logger = logging.getLogger()

router = APIRouter(prefix="/v1/manufacturer", tags=["manufacturer"])


@router.post(
    path="/",
    summary="Create new manufacturer",
    response_description="The new manufacturer",
    status_code=status.HTTP_201_CREATED,
)
def create_manufacturer(
    manufacturer: ManufacturerPostRequestSchema,
    manufacturer_service: ManufacturerService = Depends(),
) -> ManufacturerSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new manufacturer")
    logger.debug("Manufacturer data is %s", manufacturer)

    try:
        manufacturer = manufacturer_service.create(manufacturer)
        return ManufacturerSchema(**manufacturer.dict())

    except DuplicateRecordError as exc:
        message = "A manufacturer with the same name has been found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.get(
    path="/",
    summary="Get all manufacturers",
    response_description="List of manufacturers",
)
def get_all_manufacturers(manufacturer_service: ManufacturerService = Depends()) -> List[ManufacturerSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting manufacturers")

    manufacturers = manufacturer_service.list()
    return [ManufacturerSchema(**manufacturer.dict()) for manufacturer in manufacturers]


@router.get(
    path="/{manufacturer_id}",
    summary="Get a manufacturer by ID",
    response_description="Single manufacturer",
)
def get_one_manufacturer(
    manufacturer_id: str, manufacturer_service: ManufacturerService = Depends()
) -> ManufacturerSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting manufacturer with ID %s", manufacturer_id)
    try:
        manufacturer = manufacturer_service.get(manufacturer_id)
        if not manufacturer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="The requested manufacturer was not found"
            )
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid object value")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The requested manufacturer was not found"
        ) from exc

    return ManufacturerSchema(**manufacturer.dict())