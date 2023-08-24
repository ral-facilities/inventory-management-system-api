"""
Module for providing an API router which defines routes for managing catalogue categories using the
`CatalogueCategoryService` service.
"""
import logging
from typing import Optional, Annotated, List

from fastapi import APIRouter, status, Depends, HTTPException, Path, Query

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    InvalidObjectIdError,
    DuplicateRecordError,
    LeafCategoryError,
    ChildrenElementsExistError,
)
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategorySchema,
    CatalogueCategoryPostRequestSchema,
)
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-categories", tags=["catalogue categories"])


@router.get(path="/", summary="Get catalogue categories", response_description="List of catalogue categories")
def get_catalogue_categories(
    path: Annotated[Optional[str], Query(description="Filter catalogue categories by path")] = None,
    parent_path: Annotated[Optional[str], Query(description="Filter catalogue categories by parent path")] = None,
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> List[CatalogueCategorySchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue categories")
    if path:
        logger.debug("Path filter: '%s'", path)
    if parent_path:
        logger.debug("Parent path filter: '%s'", parent_path)

    catalogue_categories = catalogue_category_service.list(path, parent_path)
    return [CatalogueCategorySchema(**catalogue_category.dict()) for catalogue_category in catalogue_categories]


@router.get(
    path="/{catalogue_category_id}",
    summary="Get a catalogue category by ID",
    response_description="Single catalogue category",
)
def get_catalogue_category(
    catalogue_category_id: str = Path(description="The ID of the catalogue category to get"),
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> CatalogueCategorySchema:
    # pylint: disable=missing-function-docstring
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


@router.post(
    path="/",
    summary="Create a new catalogue category",
    response_description="The created catalogue category",
    status_code=status.HTTP_201_CREATED,
)
def create_catalogue_category(
    catalogue_category: CatalogueCategoryPostRequestSchema,
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> CatalogueCategorySchema:
    # pylint: disable=missing-function-docstring
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


@router.delete(
    path="/{catalogue_category_id}",
    summary="Delete a catalogue category by ID",
    response_description="Catalogue category deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_catalogue_category(
    catalogue_category_id: str = Path(description="The ID of the catalogue category to delete"),
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting catalogue category with ID: %s", catalogue_category_id)
    try:
        catalogue_category_service.delete(catalogue_category_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "A catalogue category with such ID was not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildrenElementsExistError as exc:
        message = "Catalogue category has children elements and cannot be deleted"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
