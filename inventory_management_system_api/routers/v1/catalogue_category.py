"""
Module for providing an API router which defines routes for managing catalogue categories using the
`CatalogueCategoryService` service.
"""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DatabaseIntegrityError,
    DuplicateCatalogueCategoryPropertyNameError,
    DuplicateRecordError,
    InvalidActionError,
    InvalidObjectIdError,
    LeafCatalogueCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPatchSchema,
    CatalogueCategoryPostSchema,
    CatalogueCategoryPropertyPatchSchema,
    CatalogueCategoryPropertyPostSchema,
    CatalogueCategoryPropertySchema,
    CatalogueCategorySchema,
    CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS,
)
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService
from inventory_management_system_api.services.catalogue_category_property import CatalogueCategoryPropertyService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-categories", tags=["catalogue categories"])

CatalogueCategoryServiceDep = Annotated[CatalogueCategoryService, Depends(CatalogueCategoryService)]

CatalogueCategoryPropertyServiceDep = Annotated[
    CatalogueCategoryPropertyService, Depends(CatalogueCategoryPropertyService)
]


@router.get(path="", summary="Get catalogue categories", response_description="List of catalogue categories")
def get_catalogue_categories(
    catalogue_category_service: CatalogueCategoryServiceDep,
    parent_id: Annotated[Optional[str], Query(description="Filter catalogue categories by parent ID")] = None,
) -> List[CatalogueCategorySchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue categories")
    if parent_id:
        logger.debug("Parent ID filter: '%s'", parent_id)

    try:
        catalogue_categories = catalogue_category_service.list(parent_id)
        return [
            CatalogueCategorySchema(**catalogue_category.model_dump()) for catalogue_category in catalogue_categories
        ]
    except InvalidObjectIdError:
        # As this endpoint filters, and to hide the database behaviour, we treat any invalid id
        # the same as a valid one that doesn't exist i.e. return an empty list
        return []


@router.get(
    path="/{catalogue_category_id}",
    summary="Get a catalogue category by ID",
    response_description="Single catalogue category",
)
def get_catalogue_category(
    catalogue_category_id: Annotated[str, Path(description="The ID of the catalogue category to get")],
    catalogue_category_service: CatalogueCategoryServiceDep,
) -> CatalogueCategorySchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue category with ID: %s", catalogue_category_id)
    message = "Catalogue category not found"
    try:
        catalogue_category = catalogue_category_service.get(catalogue_category_id)
        if not catalogue_category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return CatalogueCategorySchema(**catalogue_category.model_dump())
    except InvalidObjectIdError as exc:
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc


@router.get(path="/{catalogue_category_id}/breadcrumbs", summary="Get breadcrumbs data for a catalogue category")
def get_catalogue_category_breadcrumbs(
    catalogue_category_id: Annotated[
        str, Path(description="The ID of the catalogue category to get the breadcrumbs for")
    ],
    catalogue_category_service: CatalogueCategoryServiceDep,
) -> BreadcrumbsGetSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting breadcrumbs for catalogue category with ID: %s", catalogue_category_id)
    try:
        return catalogue_category_service.get_breadcrumbs(catalogue_category_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Catalogue category not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except DatabaseIntegrityError as exc:
        message = "Unable to obtain breadcrumbs"
        logger.exception(message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc


@router.post(
    path="",
    summary="Create a new catalogue category",
    response_description="The created catalogue category",
    status_code=status.HTTP_201_CREATED,
)
def create_catalogue_category(
    catalogue_category: CatalogueCategoryPostSchema, catalogue_category_service: CatalogueCategoryServiceDep
) -> CatalogueCategorySchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new catalogue category")
    logger.debug("Catalogue category data: %s", catalogue_category)
    try:
        catalogue_category = catalogue_category_service.create(catalogue_category)
        return CatalogueCategorySchema(**catalogue_category.model_dump())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if (
            catalogue_category.properties is not None
            and any(str(prop.unit_id) in str(exc) for prop in catalogue_category.properties)
        ) or "unit" in str(exc).lower():
            message = "The specified unit does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "The specified parent catalogue category does not exist"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A catalogue category with the same name already exists within the parent catalogue category"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except LeafCatalogueCategoryError as exc:
        message = "Adding a catalogue category to a leaf parent catalogue category is not allowed"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except DuplicateCatalogueCategoryPropertyNameError as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch(
    path="/{catalogue_category_id}",
    summary="Update a catalogue category partially by ID",
    response_description="Catalogue category updated successfully",
)
def partial_update_catalogue_category(
    catalogue_category: CatalogueCategoryPatchSchema,
    catalogue_category_id: Annotated[str, Path(description="The ID of the catalogue category to update")],
    catalogue_category_service: CatalogueCategoryServiceDep,
) -> CatalogueCategorySchema:
    # pylint: disable=missing-function-docstring
    logger.info("Partially updating catalogue category with ID: %s", catalogue_category_id)
    logger.debug("Catalogue category data: %s", catalogue_category)
    try:
        updated_catalogue_category = catalogue_category_service.update(catalogue_category_id, catalogue_category)
        return CatalogueCategorySchema(**updated_catalogue_category.model_dump())
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if (
            catalogue_category.parent_id
            and catalogue_category.parent_id in str(exc)
            or "parent catalogue category" in str(exc).lower()
        ):
            message = "The specified parent catalogue category does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if (
            catalogue_category.properties is not None
            and any(str(prop.unit_id) in str(exc) for prop in catalogue_category.properties)
        ) or "unit" in str(exc).lower():
            message = "The specified unit does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc

        message = "Catalogue category not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildElementsExistError as exc:
        message = "Catalogue category has child elements, so the following fields cannot be updated: " + ", ".join(
            CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS
        )
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except DuplicateRecordError as exc:
        message = "A catalogue category with the same name already exists within the parent catalogue category"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except LeafCatalogueCategoryError as exc:
        message = "Adding a catalogue category to a leaf parent catalogue category is not allowed"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except DuplicateCatalogueCategoryPropertyNameError as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InvalidActionError as exc:
        message = str(exc)
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc


@router.delete(
    path="/{catalogue_category_id}",
    summary="Delete a catalogue category by ID",
    response_description="Catalogue category deleted successfully",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_catalogue_category(
    catalogue_category_id: Annotated[str, Path(description="The ID of the catalogue category to delete")],
    catalogue_category_service: CatalogueCategoryServiceDep,
) -> None:
    # pylint: disable=missing-function-docstring
    logger.info("Deleting catalogue category with ID: %s", catalogue_category_id)
    try:
        catalogue_category_service.delete(catalogue_category_id)
    except (MissingRecordError, InvalidObjectIdError) as exc:
        message = "Catalogue category not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except ChildElementsExistError as exc:
        message = "Catalogue category has child elements and cannot be deleted"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.post(
    path="/{catalogue_category_id}/properties",
    summary="Create a new property at the catalogue category level",
    response_description="The created property as defined at the catalogue category level",
    status_code=status.HTTP_201_CREATED,
)
def create_property(
    catalogue_category_property: CatalogueCategoryPropertyPostSchema,
    catalogue_category_id: Annotated[str, Path(description="The ID of the catalogue category to add a property to")],
    catalogue_category_property_service: CatalogueCategoryPropertyServiceDep,
) -> CatalogueCategoryPropertySchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new property at the catalogue category level")
    logger.debug("Catalogue category property data: %s", catalogue_category_property)

    try:
        return CatalogueCategoryPropertySchema(
            **catalogue_category_property_service.create(
                catalogue_category_id, catalogue_category_property
            ).model_dump()
        )
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if (
            catalogue_category_property.unit_id is not None
            and catalogue_category_property.unit_id in str(exc)
            or "unit" in str(exc).lower()
        ):
            message = "The specified unit does not exist"
            logger.exception(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        message = "Catalogue category not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    except DuplicateCatalogueCategoryPropertyNameError as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InvalidActionError as exc:
        message = str(exc)
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc


@router.patch(
    path="/{catalogue_category_id}/properties/{property_id}",
    summary="Update property at the catalogue category level",
    response_description="The updated property as defined at the catalogue category level",
)
def partial_update_property(
    catalogue_category_property: CatalogueCategoryPropertyPatchSchema,
    catalogue_category_id: Annotated[
        str, Path(description="The ID of the catalogue category containing the property to patch")
    ],
    property_id: Annotated[str, Path(description="The ID of the property to patch")],
    catalogue_category_property_service: CatalogueCategoryPropertyServiceDep,
) -> CatalogueCategoryPropertySchema:
    # pylint: disable=missing-function-docstring
    logger.info(
        "Partially updating catalogue category with ID %s's property with ID: %s",
        catalogue_category_id,
        property_id,
    )
    logger.debug("Catalogue category property data: %s", catalogue_category_property)

    try:
        return CatalogueCategoryPropertySchema(
            **catalogue_category_property_service.update(
                catalogue_category_id, property_id, catalogue_category_property
            ).model_dump()
        )
    except (MissingRecordError, InvalidObjectIdError) as exc:
        if property_id in str(exc):
            message = "Catalogue category property not found"
        else:
            message = "Catalogue category not found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    # pylint:disable=duplicate-code
    except DuplicateCatalogueCategoryPropertyNameError as exc:
        logger.exception(str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InvalidActionError as exc:
        message = str(exc)
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except ValueError as exc:
        message = str(exc)
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
