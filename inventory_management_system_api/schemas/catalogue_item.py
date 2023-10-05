"""
Module for defining the API schema models for representing catalogue items.
"""
from typing import List, Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class ManufacturerSchema(BaseModel):
    """
    Schema model for a catalogue item manufacturer creation request.
    """

    name: str = Field(description="The name of the manufacturer")
    address: str = Field(description="The address of the manufacturer")
    web_url: HttpUrl = Field(description="The website URL of the manufacturer")


class PropertyPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue item property creation request.
    """

    name: str = Field(description="The name of the catalogue item property")
    value: Any = Field(description="The value of the catalogue item property")


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
    name: str = Field(description="The name of the catalogue item")
    description: str = Field(description="The catalogue item description")
    properties: Optional[List[PropertyPostRequestSchema]] = Field(description="The catalogue item properties")
    manufacturer: ManufacturerSchema = Field(description="The details of the manufacturer")


class CatalogueItemPatchRequestSchema(CatalogueItemPostRequestSchema):
    """
    Schema model for a catalogue item update request.
    """

    catalogue_category_id: Optional[str] = Field(
        description="The ID of the catalogue category that the catalogue item belongs to"
    )
    name: Optional[str] = Field(description="The name of the catalogue item")
    description: Optional[str] = Field(description="The catalogue item description")
    manufacturer: Optional[ManufacturerSchema] = Field(description="The details of the manufacturer")


class CatalogueItemSchema(CatalogueItemPostRequestSchema):
    """
    Schema model for a catalogue item response.
    """

    id: str = Field(description="The ID of the catalogue item")
    properties: List[PropertySchema] = Field(description="The catalogue item properties")
