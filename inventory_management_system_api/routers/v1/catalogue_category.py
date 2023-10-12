"""
Module for providing an API router which defines routes for managing catalogue categories using the
`CatalogueCategoryService` service.
"""
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from inventory_management_system_api.core.breadcrumbs import compute_breadcrumbs
from inventory_management_system_api.core.exceptions import (
    ChildrenElementsExistError,
    DatabaseIntegrityError,
    DuplicateRecordError,
    EntityNotFoundError,
    InvalidObjectIdError,
    LeafCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPatchRequestSchema,
    CatalogueCategoryPostRequestSchema,
    CatalogueCategorySchema,
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
    message = "A catalogue category with such ID was not found"
    try:
        catalogue_category = catalogue_category_service.get(catalogue_category_id)
        if not catalogue_category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return CatalogueCategorySchema(**catalogue_category.dict())
    except InvalidObjectIdError as exc:
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc


@router.get(path="/{catalogue_category_id}/breadcrumbs", summary="Get breadcrumbs data for a catalogue category")
def get_catalogue_category_breadcrumbs(
    catalogue_category_id: str = Path(description="The ID of the catalogue category to get the breadcrumbs for"),
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> BreadcrumbsGetSchema:
    # pylint: disable=missing-function-docstring
    try:
        return compute_breadcrumbs(entity_id=catalogue_category_id, entity_service=catalogue_category_service)
    except (InvalidObjectIdError, EntityNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catalogue category with such ID was not found"
        ) from exc
    except DatabaseIntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to obtain breadcrumbs due to a database issue",
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
        message = "The specified parent catalogue category ID does not exist"
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


@router.patch(
    path="/{catalogue_category_id}",
    summary="Update a catalogue category partially by ID",
    response_description="Catalogue category updated successfully",
)
def partial_update_catalogue_category(
    catalogue_category: CatalogueCategoryPatchRequestSchema,
    catalogue_category_id: str = Path(description="The ID of the catalogue category to update"),
    catalogue_category_service: CatalogueCategoryService = Depends(),
) -> CatalogueCategorySchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating catalogue category with ID: %s", catalogue_category_id)
    logger.debug("Catalogue category data: %s", catalogue_category)
    try:
        updated_catalogue_category = catalogue_category_service.update(catalogue_category_id, catalogue_category)
        return CatalogueCategorySchema(**updated_catalogue_category.dict())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if (
            catalogue_category.parent_id
            and catalogue_category.parent_id in str(exc)
            or "parent catalogue category" in str(exc).lower()
        ):
            message = "The specified parent catalogue category ID does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "A catalogue category with such ID was not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildrenElementsExistError as exc:
        message = "Catalogue category has children elements and cannot be updated"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
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
