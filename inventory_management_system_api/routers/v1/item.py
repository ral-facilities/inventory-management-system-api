"""
Module for providing an API router which defines routes for managing items using the `ItemService` service.
"""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Query, status, HTTPException, Depends, Path

from inventory_management_system_api.core.exceptions import (
    InvalidActionError,
    InvalidObjectIdError,
    MissingMandatoryCatalogueItemProperty,
    MissingRecordError,
    DatabaseIntegrityError,
    InvalidCatalogueItemPropertyTypeError,
)
from inventory_management_system_api.schemas.item import ItemPatchRequestSchema, ItemPostRequestSchema, ItemSchema
from inventory_management_system_api.services.item import ItemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/items", tags=["items"])

ItemServiceDep = Annotated[ItemService, Depends(ItemService)]


@router.post(
    path="",
    summary="Create a new item",
    response_description="The created item",
    status_code=status.HTTP_201_CREATED,
)
def create_item(item: ItemPostRequestSchema, item_service: ItemServiceDep) -> ItemSchema:
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
            message = "The specified system does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if item.usage_status_id and item.usage_status_id in str(exc) or "usage status" in str(exc).lower():
            message = "The specified usage status does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "The specified catalogue item does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DatabaseIntegrityError as exc:
        message = "Unable to create item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc


@router.delete(
    path="/{item_id}",
    summary="Delete an item by ID",
    response_description="Item deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_item(
    item_id: Annotated[str, Path(description="The ID of the item to delete")], item_service: ItemServiceDep
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting item with ID: %s", item_id)
    try:
        item_service.delete(item_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Item not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc


@router.get(path="", summary="Get items", response_description="List of items")
def get_items(
    item_service: ItemServiceDep,
    system_id: Annotated[Optional[str], Query(description="Filter items by system ID")] = None,
    catalogue_item_id: Annotated[Optional[str], Query(description="Filter items by catalogue item ID")] = None,
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


@router.get(path="/{item_id}", summary="Get an item by ID", response_description="Single item")
def get_item(
    item_id: Annotated[str, Path(description="The ID of the item to get")], item_service: ItemServiceDep
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


@router.patch(
    path="/{item_id}",
    summary="Update an item partially by ID",
    response_description="Item updated successfully",
)
def partial_update_item(
    item: ItemPatchRequestSchema,
    item_id: Annotated[str, Path(description="The ID of the item to update")],
    item_service: ItemServiceDep,
) -> ItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating item with ID: %s", item_id)
    logger.debug("Item data: %s", item)
    try:
        updated_item = item_service.update(item_id, item)
        return ItemSchema(**updated_item.model_dump())
    except (InvalidCatalogueItemPropertyTypeError, MissingMandatoryCatalogueItemProperty) as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if item.system_id and item.system_id in str(exc) or "system" in str(exc).lower():
            message = "The specified system does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if item.usage_status_id and item.usage_status_id in str(exc) or "usage status" in str(exc).lower():
            message = "The specified usage status does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        message = "Item not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except DatabaseIntegrityError as exc:
        message = "Unable to update item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message) from exc
    except InvalidActionError as exc:
        message = "Cannot change the catalogue item of an item"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
