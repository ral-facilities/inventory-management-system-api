"""
Module for defining the API schema models for representing catalogue items.
"""
from typing import List, Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class ManufacturerPostRequestSchema(BaseModel):
    """Schema model for a manufacturer creation request"""

    name: str
    url: HttpUrl
    address: str


class PropertyPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue item property creation request.
    """

    name: str = Field(description="The name of the catalogue item property")
    value: Any = Field(default=None, description="The value of the catalogue item property")


class PropertySchema(PropertyPostRequestSchema):
    """
    Schema model for a catalogue item property response.
    """

    unit: Optional[str] = Field(default=None, description="The unit of the property such as 'nm', 'mm', 'cm' etc")


class CatalogueItemPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue item creation request.
    """

    catalogue_category_id: str = Field(
        description="The ID of the catalogue category that the catalogue item belongs to"
    )
    # pylint: disable=fixme
    # TODO - Change from manufacturer Sto manufacturer id
    manufacturer: ManufacturerPostRequestSchema = Field(description="The details of the manufacturer")
    name: str = Field(description="The name of the catalogue item")
    description: Optional[str] = Field(default=None, description="The description of the catalogue item")
    cost_gbp: float = Field(description="The cost of the catalogue item")
    cost_to_rework_gbp: Optional[float] = Field(default=None, description="The cost to rework the catalogue item")
    days_to_replace: float = Field(description="The number of days to replace the catalogue item")
    days_to_rework: Optional[float] = Field(default=None, description="The number of days to rework the catalogue item")
    drawing_number: Optional[str] = Field(default=None, description="The drawing number of the catalogue item")
    drawing_link: Optional[HttpUrl] = Field(default=None, description="The link to the drawing of the catalogue item")
    item_model_number: Optional[str] = Field(default=None, description="The model number of the catalogue item")
    is_obsolete: bool = Field(description="Whether the catalogue item is obsolete or not")
    obsolete_reason: Optional[str] = Field(
        default=None, description="The reason why the catalogue item item became obsolete"
    )
    obsolete_replace_catalogue_item_id: Optional[str] = Field(
        default=None, description="The ID of the catalogue item that replaces this catalogue item if obsolete"
    )
    properties: Optional[List[PropertyPostRequestSchema]] = Field(
        default=None, description="The catalogue item properties"
    )


class CatalogueItemPatchRequestSchema(CatalogueItemPostRequestSchema):
    """
    Schema model for a catalogue item update request.
    """

    catalogue_category_id: Optional[str] = Field(
        default=None, description="The ID of the catalogue category that the catalogue item belongs to"
    )
    # pylint: disable=fixme
    # TODO - Change from manufacturer Sto manufacturer id
    manufacturer: Optional[ManufacturerPostRequestSchema] = Field(
        default=None, description="The details of the manufacturer"
    )
    name: Optional[str] = Field(default=None, description="The name of the catalogue item")
    cost_gbp: Optional[float] = Field(default=None, description="The cost of the catalogue item")
    days_to_replace: Optional[float] = Field(
        default=None, description="The number of days to replace the catalogue item"
    )
    is_obsolete: Optional[bool] = Field(default=None, description="Whether the catalogue item is obsolete or not")


class CatalogueItemSchema(CatalogueItemPostRequestSchema):
    """
    Schema model for a catalogue item response.
    """

    id: str = Field(description="The ID of the catalogue item")
    properties: List[PropertySchema] = Field(description="The catalogue item properties")
