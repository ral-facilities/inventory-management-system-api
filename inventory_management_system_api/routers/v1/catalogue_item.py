"""
Module for providing an API router which defines routes for managing catalogue items using the `CatalogueItemService`
service.
"""
import logging

from fastapi import APIRouter, status, Depends, HTTPException, Path, Query

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


@router.get(path="/", summary="Get catalogue items", response_description="List of catalogue items")
def get_catalogue_items(
    catalogue_category_id: str = Query(description="Filter catalogue items by catalogue category ID"),
    catalogue_item_service: CatalogueItemService = Depends(),
) -> List[CatalogueItemSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue items")
    logger.debug("Catalogue category id filter: '%s'", catalogue_category_id)
    catalogue_items = catalogue_item_service.list(catalogue_category_id)
    return [CatalogueItemSchema(**catalogue_item.dict()) for catalogue_item in catalogue_items]


@router.get(
    path="/{catalogue_item_id}", summary="Get a catalogue item by ID", response_description="Single catalogue item"
)
def get_catalogue_item(
    catalogue_item_id: str = Path(description="The ID of the catalogue item to get"),
    catalogue_item_service: CatalogueItemService = Depends(),
) -> CatalogueItemSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue item with ID: %s", catalogue_item_id)
    try:
        catalogue_item = catalogue_item_service.get(catalogue_item_id)
        if not catalogue_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="The requested catalogue item was not found"
            )
        return CatalogueItemSchema(**catalogue_item.dict())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The requested catalogue item was not found"
        ) from exc


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
