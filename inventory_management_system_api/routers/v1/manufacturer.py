"""
Module for providing an API router which defines routes for managing manufacturer using the
`Manufacturer` service.
"""
import logging

from fastapi import APIRouter, status, Depends, HTTPException
from inventory_management_system_api.core.exceptions import DuplicateRecordError

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
