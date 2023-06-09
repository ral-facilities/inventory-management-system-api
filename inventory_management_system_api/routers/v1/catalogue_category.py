"""
Module for providing an API router which defines routes for managing catalogue categories.
"""
import logging

from fastapi import APIRouter, status, Depends, HTTPException

from inventory_management_system_api.core.exceptions import MissingRecordError, InvalidObjectIdError
from inventory_management_system_api.schemas.catalogue_category import CatalogueCategorySchema, \
    CatalogueCategoryPostRequestSchema
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-categories")


@router.post(path="/", status_code=status.HTTP_201_CREATED)
def post(catalogue_category: CatalogueCategoryPostRequestSchema,
         catalogue_category_service: CatalogueCategoryService = Depends()) -> CatalogueCategorySchema:
    """
    Create a new catalogue category.

    :param catalogue_category: The catalogue category to be created.
    :param catalogue_category_service: The catalogue category service to use.
    :return: The created catalogue category.
    :raises HTTPException: If the specified parent catalogue category ID is invalid or does not exist in the database.
    """
    logger.info("Creating a new catalogue category")
    logger.debug("Catalogue category data: %s", catalogue_category)
    try:
        catalogue_category = catalogue_category_service.create(catalogue_category)
        return CatalogueCategorySchema(**catalogue_category.dict())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "The specified parent catalogue category ID does not exist in the database"
        logger.exception(message)
        raise HTTPException(status_code=422, detail=message) from exc
