"""
Module for providing an API router which defines routes for managing catalogue items using the `CatalogueItemService`
service.
"""

import logging
from typing import List, Annotated, Optional

from fastapi import APIRouter, status, Depends, HTTPException, Path, Query

from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    MissingRecordError,
    InvalidObjectIdError,
    NonLeafCategoryError,
    InvalidCatalogueItemPropertyTypeError,
    MissingMandatoryCatalogueItemProperty,
)
from inventory_management_system_api.schemas.catalogue_item import (
    CatalogueItemSchema,
    CatalogueItemPostRequestSchema,
    CatalogueItemPatchRequestSchema,
)
from inventory_management_system_api.services.catalogue_item import CatalogueItemService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-items", tags=["catalogue items"])


@router.get(path="", summary="Get catalogue items", response_description="List of catalogue items")
def get_catalogue_items(
    catalogue_category_id: Annotated[
        Optional[str], Query(description="Filter catalogue items by catalogue category ID")
    ] = None,
    catalogue_item_service: CatalogueItemService = Depends(),
) -> List[CatalogueItemSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue items")
    if catalogue_category_id:
        logger.debug("Catalogue category ID filter: '%s'", catalogue_category_id)

    try:
        catalogue_items = catalogue_item_service.list(catalogue_category_id)
        return [CatalogueItemSchema(**catalogue_item.model_dump()) for catalogue_item in catalogue_items]
    except InvalidObjectIdError:
        logger.exception("The provided catalogue category ID filter value is not a valid ObjectId value")
        return []


@router.get(
    path="/{catalogue_item_id}", summary="Get a catalogue item by ID", response_description="Single catalogue item"
)
def get_catalogue_item(
    catalogue_item_id: str = Path(description="The ID of the catalogue item to get"),
    catalogue_item_service: CatalogueItemService = Depends(),
) -> CatalogueItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue item with ID: %s", catalogue_item_id)
    message = "A catalogue item with such ID was not found"
    try:
        catalogue_item = catalogue_item_service.get(catalogue_item_id)
        if not catalogue_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return CatalogueItemSchema(**catalogue_item.model_dump())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc


@router.post(
    path="",
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
        return CatalogueItemSchema(**catalogue_item.model_dump())
    except (InvalidCatalogueItemPropertyTypeError, MissingMandatoryCatalogueItemProperty) as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if catalogue_item.catalogue_category_id in str(exc) or "catalogue category" in str(exc).lower():
            message = "The specified catalogue category ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if catalogue_item.manufacturer_id in str(exc) or "manufacturer" in str(exc).lower():
            message = "The specified manufacturer ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "The specified replacement catalogue item ID does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except NonLeafCategoryError as exc:
        message = "Adding a catalogue item to a non-leaf catalogue category is not allowed"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.patch(
    path="/{catalogue_item_id}",
    summary="Update a catalogue item partially by ID",
    response_description="Catalogue item updated successfully",
)
def partial_update_catalogue_item(
    catalogue_item: CatalogueItemPatchRequestSchema,
    catalogue_item_id: str = Path(description="The ID of the catalogue item to update"),
    catalogue_item_service: CatalogueItemService = Depends(),
) -> CatalogueItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating catalogue item with ID: %s", catalogue_item_id)
    logger.debug("Catalogue item data: %s", catalogue_item)
    try:
        updated_catalogue_item = catalogue_item_service.update(catalogue_item_id, catalogue_item)
        return CatalogueItemSchema(**updated_catalogue_item.model_dump())
    except (InvalidCatalogueItemPropertyTypeError, MissingMandatoryCatalogueItemProperty) as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if (
            catalogue_item.catalogue_category_id
            and catalogue_item.catalogue_category_id in str(exc)
            or "catalogue category" in str(exc).lower()
        ):
            message = "The specified catalogue category ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if (
            catalogue_item.manufacturer_id
            and catalogue_item.manufacturer_id in str(exc)
            or "manufacturer" in str(exc).lower()
        ):
            message = "The specified manufacturer ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        if (
            catalogue_item.obsolete_replacement_catalogue_item_id
            and catalogue_item.obsolete_replacement_catalogue_item_id in str(exc)
        ):
            message = "The specified replacement catalogue item ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "A catalogue item with such ID was not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except NonLeafCategoryError as exc:
        message = "Adding a catalogue item to a non-leaf catalogue category is not allowed"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except ChildElementsExistError as exc:
        message = "Catalogue item has child elements and cannot be updated"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.delete(
    path="/{catalogue_item_id}",
    summary="Delete a catalogue item by ID",
    response_description="Catalogue item deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_catalogue_item(
    catalogue_item_id: str = Path(description="The ID of the catalogue item to delete"),
    catalogue_item_service: CatalogueItemService = Depends(),
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting catalogue item with ID: %s", catalogue_item_id)
    try:
        catalogue_item_service.delete(catalogue_item_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "A catalogue item with such ID was not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildElementsExistError as exc:
        message = "Catalogue item has child elements and cannot be deleted"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
