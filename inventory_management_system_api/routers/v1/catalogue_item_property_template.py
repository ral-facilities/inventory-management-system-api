"""
Module for providing an API router which defines routes for managing catalogue item property templates
using the `CatalogueItemPropertyTemplateService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from inventory_management_system_api.schemas.catalogue_item_property_template import CatalogueItemPropertyTemplateSchema
from inventory_management_system_api.services.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateService,
)


logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-item-property-templates", tags=["catalogue item property templates"])


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
