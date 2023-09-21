"""
Module for providing an API router which defines routes for managing catalogue items using the `CatalogueItemService`
service.
"""
import logging

from fastapi import APIRouter, status, Depends, HTTPException

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    InvalidObjectIdError,
    DuplicateRecordError,
    NonLeafCategoryError,
    InvalidCatalogueItemPropertyTypeError,
    MissingMandatoryCatalogueItemProperty,
)
from inventory_management_system_api.schemas.catalogue_item import CatalogueItemSchema, CatalogueItemPostRequestSchema
from inventory_management_system_api.services.catalogue_item import CatalogueItemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-items", tags=["catalogue items"])


@router.post(
    path="/",
    summary="Create a new catalogue item",
    response_description="The created catalogue item",
    status_code=status.HTTP_201_CREATED,
)
def create_catalogue_item(
    catalogue_item: CatalogueItemPostRequestSchema, catalogue_item_service: CatalogueItemService = Depends()
) -> CatalogueItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new catalogue item")
    logger.debug("Catalogue item data: %s", catalogue_item)
    try:
        catalogue_item = catalogue_item_service.create(catalogue_item)
        return CatalogueItemSchema(**catalogue_item.dict())
    except (InvalidCatalogueItemPropertyTypeError, MissingMandatoryCatalogueItemProperty) as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "The specified catalogue category ID does not exist in the database"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A catalogue item with the same name already exists within the catalogue category"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except NonLeafCategoryError as exc:
        message = "Adding a catalogue item to a non-leaf catalogue category is not allowed"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
