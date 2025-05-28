"""
Module for providing an API router which defines routes for managing catalogue categories using the
`CatalogueCategoryService` service.
"""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, status

from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPatchSchema,
    CatalogueCategoryPostSchema,
    CatalogueCategoryPropertyPatchSchema,
    CatalogueCategoryPropertyPostSchema,
    CatalogueCategoryPropertySchema,
    CatalogueCategorySchema,
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

    catalogue_categories = catalogue_category_service.list(parent_id)
    return [CatalogueCategorySchema(**catalogue_category.model_dump()) for catalogue_category in catalogue_categories]


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

    catalogue_category = catalogue_category_service.get(catalogue_category_id)
    return CatalogueCategorySchema(**catalogue_category.model_dump())


@router.get(path="/{catalogue_category_id}/breadcrumbs", summary="Get breadcrumbs data for a catalogue category")
def get_catalogue_category_breadcrumbs(
    catalogue_category_id: Annotated[
        str, Path(description="The ID of the catalogue category to get the breadcrumbs for")
    ],
    catalogue_category_service: CatalogueCategoryServiceDep,
) -> BreadcrumbsGetSchema:
    # pylint: disable=missing-function-docstring

    logger.info("Getting breadcrumbs for catalogue category with ID: %s", catalogue_category_id)
    return catalogue_category_service.get_breadcrumbs(catalogue_category_id)


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

    catalogue_category = catalogue_category_service.create(catalogue_category)
    return CatalogueCategorySchema(**catalogue_category.model_dump())


PathIDString = Annotated[str, Path(description="The ID of the catalogue category to update")]


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

    updated_catalogue_category = catalogue_category_service.update(catalogue_category_id, catalogue_category)
    return CatalogueCategorySchema(**updated_catalogue_category.model_dump())


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
    catalogue_category_service.delete(catalogue_category_id)


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

    return CatalogueCategoryPropertySchema(
        **catalogue_category_property_service.create(catalogue_category_id, catalogue_category_property).model_dump()
    )


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

    return CatalogueCategoryPropertySchema(
        **catalogue_category_property_service.update(
            catalogue_category_id, property_id, catalogue_category_property
        ).model_dump()
    )
