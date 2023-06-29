"""
Module for providing an API router which defines routes for managing catalogue categories using the
`CatalogueCategoryService` service.
"""
import logging

from fastapi import APIRouter, status, Depends, HTTPException

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    InvalidObjectIdError,
    DuplicateRecordError,
    LeafCategoryError,
)
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategorySchema,
    CatalogueCategoryPostRequestSchema,
)
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-categories", tags=["catalogue categories"])


@router.get(path="/{catalogue_category_id}")
def get_catalogue_category(
    catalogue_category_id: str,
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> CatalogueCategorySchema:
    """
    Get a catalogue category by its ID.

    :param catalogue_category_id: The ID of the catalogue category to get.
    :param catalogue_category_service: The catalogue category service to use.
    :return: The catalogue category
    :raises HTTPException: If the specified catalogue category ID is invalid or does not exist in the database.
    """
    logger.info("Getting catalogue category with ID: %s", catalogue_category_id)
    try:
        catalogue_category = catalogue_category_service.get(catalogue_category_id)
        if not catalogue_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="The requested catalogue category was not found"
            )
        return CatalogueCategorySchema(**catalogue_category.dict())
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid ObjectId value")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The requested catalogue category was not found"
        ) from exc


@router.post(path="/", status_code=status.HTTP_201_CREATED)
def post(
    catalogue_category: CatalogueCategoryPostRequestSchema,
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> CatalogueCategorySchema:
    """
    Create a new catalogue category.

    :param catalogue_category: The catalogue category to be created.
    :param catalogue_category_service: The catalogue category service to use.
    :return: The created catalogue category.
    :raises HTTPException:
        - If the specified parent catalogue category ID is invalid or does not exist in the database.
        - If the catalogue category already exists within the parent catalogue category.
        - If the parent catalogue category is a leaf catalogue category
    """
    logger.info("Creating a new catalogue category")
    logger.debug("Catalogue category data: %s", catalogue_category)
    try:
        catalogue_category = catalogue_category_service.create(catalogue_category)
        return CatalogueCategorySchema(**catalogue_category.dict())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "The specified parent catalogue category ID does not exist in the database"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A catalogue category with the same name already exists within the parent catalogue category"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except LeafCategoryError as exc:
        message = "Adding a catalogue category to a leaf parent catalogue category is not allowed"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
