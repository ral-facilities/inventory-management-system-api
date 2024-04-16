"""
Module for defining the API schema models for representing catalogue item property templates.
"""

from pydantic import Field

from inventory_management_system_api.schemas.catalogue_category import CatalogueItemPropertySchema


class CatalogueItemPropertyTemplateSchema(CatalogueItemPropertySchema):
    """
    Schema model representing a catalogue item property template.
    """

    id: str = Field(description="ID of the catalogue item property template")
