"""
Module for providing an API router which defines routes for managing manufacturer using the
`Manufacturer` service.
"""
import logging
from typing import Optional, Annotated, List

from fastapi import APIRouter, status, Depends, HTTPException, Path, Query

from inventory_management_system_api.schemas.manufacturer import ManufacturerPostRequestSchema, ManufacturerSchema
from inventory_management_system_api.services.manufacturer import ManufacturerService


logger = logging.getLogger()

router = APIRouter(prefix="/v1/manufacturer", tags=["manufacturer"])


# add manufacturer
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
    logger.info("Creating a new manufacturer")
    logger.debug("Manufacturer data is %s", manufacturer)
    
    manufacturer = manufacturer_service.create(manufacturer)
    return ManufacturerSchema(**manufacturer.dict())


# #view manufacturer
# @router.get()

# #edit manufacturer
# @router.put()

# #delte manufacturer
# @router.delete()
