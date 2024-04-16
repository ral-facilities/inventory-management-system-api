"""
Module for providing an API router which defines routes for managing catalogue item property templates
using the `CatalogueItemPropertyTemplateService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Path

from inventory_management_system_api.core.exceptions import DuplicateRecordError, InvalidObjectIdError
from inventory_management_system_api.schemas.catalogue_item_property_template import (
    CatalogueItemPropertyTemplatePostRequestSchema,
    CatalogueItemPropertyTemplateSchema,
)
from inventory_management_system_api.services.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateService,
)

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-item-property-templates", tags=["catalogue item property templates"])


@router.post(
    path="",
    summary="Create new catalogue item property template",
    response_description="The new catalogue item property template",
    status_code=status.HTTP_201_CREATED,
)
def create_catalogue_item_property_template(
    catalogue_item_property_template: CatalogueItemPropertyTemplatePostRequestSchema,
    catalogue_item_property_template_service: CatalogueItemPropertyTemplateService = Depends(),
) -> CatalogueItemPropertyTemplateSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Creating a new catalogue item property template")
    logger.debug("Catalogue item property template data is %s", catalogue_item_property_template)

    try:
        catalogue_item_property_template = catalogue_item_property_template_service.create(
            catalogue_item_property_template
        )
        return CatalogueItemPropertyTemplateSchema(**catalogue_item_property_template.model_dump())

    except DuplicateRecordError as exc:
        message = "A catalogue item property template with the same name has been found"
        logger.exception(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.get(
    path="/{catalogue_item_property_template_id}",
    summary="Get a catalogue item property template by ID",
    response_description="Single catalogue item property template",
)
def get_catalogue_item_property_template(
    catalogue_item_property_template_id: str = Path(
        description="The ID of the catalogue item property template to be retrieved"
    ),
    catalogue_item_property_template_service: CatalogueItemPropertyTemplateService = Depends(),
) -> CatalogueItemPropertyTemplateSchema:
    # pylint: disable=missing-function-docstring
    logger.info("Getting catalogue item property template with ID %s", catalogue_item_property_template_id)
    message = "Catalogue item property template not found"
    try:
        catalogue_item_property_template = catalogue_item_property_template_service.get(
            catalogue_item_property_template_id
        )
        if not catalogue_item_property_template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    except InvalidObjectIdError as exc:
        logger.exception("The ID is not a valid object value")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc

    return CatalogueItemPropertyTemplateSchema(**catalogue_item_property_template.model_dump())


@router.get(
    path="",
    summary="Get catalogue item property templates",
    response_description="List of catalogue item property templates",
)
def get_catalogue_item_property_templates(
    catalogue_item_property_template_service: Annotated[
        CatalogueItemPropertyTemplateService, Depends(CatalogueItemPropertyTemplateService)
    ]
) -> list[CatalogueItemPropertyTemplateSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Get catalogue item property templates")

    catalogue_item_property_templates = catalogue_item_property_template_service.list()
    return [
        CatalogueItemPropertyTemplateSchema(**catalogue_item_property_template.model_dump())
        for catalogue_item_property_template in catalogue_item_property_templates
    ]
