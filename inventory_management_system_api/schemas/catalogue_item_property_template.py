"""
Module for defining the API schema models for representing catalogue item property templates.
"""

from typing import Optional

from pydantic import BaseModel, Field


from inventory_management_system_api.schemas.catalogue_category import AllowedValuesSchema, CatalogueItemPropertyType


# pylint: disable=duplicate-code
class CatalogueItemPropertyTemplateSchema(BaseModel):
    """
    Schema model representing a catalogue item property template.
    """

    id: str = Field(description="ID of the catalogue item property template")
    name: str = Field(description="The name of the property")
    type: CatalogueItemPropertyType = Field(description="The type of the property")
    unit: Optional[str] = Field(default=None, description="The unit of the property such as 'nm', 'mm', 'cm' etc")
    mandatory: bool = Field(description="Whether the property must be supplied when a catalogue item is created")
    allowed_values: Optional[AllowedValuesSchema] = Field(
        default=None,
        description="Definition of the allowed values this property can take. 'null' indicates any value matching the "
        "type is allowed.",
    )
