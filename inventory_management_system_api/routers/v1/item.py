"""
Module for providing an API router which defines routes for managing items using the `ItemService` service.
"""
import logging

from fastapi import APIRouter, status, HTTPException, Depends, Path

from inventory_management_system_api.core.exceptions import (
    InvalidObjectIdError,
    MissingRecordError,
    DatabaseIntegrityError,
    InvalidCatalogueItemPropertyTypeError,
)
from inventory_management_system_api.schemas.item import ItemPostRequestSchema, ItemSchema
from inventory_management_system_api.services.item import ItemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/items", tags=["items"])


@router.post(
    path="/",
    summary="Create a new item",
    response_description="The created item",
    status_code=status.HTTP_201_CREATED,
)
def create_item(item: ItemPostRequestSchema, item_service: ItemService = Depends()) -> ItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new item")
    logger.debug("Item data: %s", item)
    try:
        item = item_service.create(item)
        return ItemSchema(**item.model_dump())
    except InvalidCatalogueItemPropertyTypeError as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if item.system_id and item.system_id in str(exc) or "system" in str(exc).lower():
            message = "The specified system ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "The specified catalogue item ID does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DatabaseIntegrityError as exc:
        message = "Unable to create item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc


@router.get(path="/{item_id}", summary="Get an item by ID", response_description="Single item")
def get_item(
    item_id: str = Path(description="The ID of the item to get"), item_service: ItemService = Depends()
) -> ItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting item with ID %s", item_id)
    message = "An item with such ID was not found"
    try:
        item = item_service.get(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return ItemSchema(**item.model_dump())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
