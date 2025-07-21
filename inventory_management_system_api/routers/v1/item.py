"""
Module for providing an API router which defines routes for managing items using the `ItemService` service.
"""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, Request, status

from inventory_management_system_api.core.config import config
from inventory_management_system_api.schemas.item import ItemPatchSchema, ItemPostSchema, ItemSchema
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
def create_item(item: ItemPostSchema, item_service: ItemServiceDep) -> ItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new item")
    logger.debug("Item data: %s", item)

    item = item_service.create(item)
    return ItemSchema(**item.model_dump())


@router.delete(
    path="/{item_id}",
    summary="Delete an item by ID",
    response_description="Item deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_item(
    item_id: Annotated[str, Path(description="The ID of the item to delete")],
    item_service: ItemServiceDep,
    request: Request,
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting item with ID: %s", item_id)
    item_service.delete(item_id, request.state.token if config.authentication.enabled else None)


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

    items = item_service.list(system_id, catalogue_item_id)
    return [ItemSchema(**item.model_dump()) for item in items]


@router.get(path="/{item_id}", summary="Get an item by ID", response_description="Single item")
def get_item(
    item_id: Annotated[str, Path(description="The ID of the item to get")], item_service: ItemServiceDep
) -> ItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting item with ID %s", item_id)
    item = item_service.get(item_id)
    return ItemSchema(**item.model_dump())


@router.patch(
    path="/{item_id}",
    summary="Update an item partially by ID",
    response_description="Item updated successfully",
)
def partial_update_item(
    item: ItemPatchSchema,
    item_id: Annotated[str, Path(description="The ID of the item to update")],
    item_service: ItemServiceDep,
) -> ItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating item with ID: %s", item_id)
    logger.debug("Item data: %s", item)

    updated_item = item_service.update(item_id, item)
    return ItemSchema(**updated_item.model_dump())
