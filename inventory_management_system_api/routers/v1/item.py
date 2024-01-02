"""
Module for providing an API router which defines routes for managing items using the `ItemService` service.
"""
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Query, status, HTTPException, Depends

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


@router.get(path="/", summary="Get items", response_description="List of items")
def get_items(
    system_id: Annotated[Optional[str], Query(description="Filter items by system ID")] = None,
    catalogue_item_id: Annotated[Optional[str], Query(description="Filter items by catalogue item ID")] = None,
    item_service: Annotated[ItemService, None] = Depends(),
) -> List[ItemSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting items")
    if system_id:
        logger.debug("System ID filter: '%s'", system_id)
    if catalogue_item_id:
        logger.debug("Catalogue item ID filter: '%s'", catalogue_item_id)
    try:
        items = item_service.list(system_id, catalogue_item_id)
        return [ItemSchema(**item.model_dump()) for item in items]

    except InvalidObjectIdError:
        if system_id:
            logger.exception("The provided system ID filter value is not a valid ObjectId value")

        if catalogue_item_id:
            logger.exception("The provided catalogue item ID filter value is not a valid ObjectId value")

        return []
