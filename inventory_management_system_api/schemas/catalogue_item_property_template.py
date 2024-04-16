"""
Module for defining the API schema models for representing catalogue item property templates.
"""

from pydantic import Field

from inventory_management_system_api.schemas.catalogue_category import CatalogueItemPropertySchema
from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class CatalogueItemPropertyTemplateSchema(CreatedModifiedSchemaMixin, CatalogueItemPropertySchema):
    """
    Schema model representing a catalogue item property template.
    """

    id: str = Field(description="ID of the catalogue item property template")
    code: str = Field(description="The code of the catalogue item property template")


class CatalogueItemPropertyTemplatePostRequestSchema(CatalogueItemPropertySchema):
    """
    Schema model representing the post request for creating an catalogue item property template.
    """
