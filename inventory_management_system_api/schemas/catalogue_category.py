"""
Module for defining the API schema models for representing catalogue categories.
"""
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


class CatalogueItemPropertyType(str, Enum):
    """
    Enumeration for catalogue item property types.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


class CatalogueItemProperty(BaseModel):
    """
    Model representing a catalogue item property.
    """

    name: str
    type: CatalogueItemPropertyType
    unit: Optional[str] = None
    mandatory: bool


class CatalogueCategoryPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue category creation request.
    """

    name: str
    is_leaf: bool
    parent_id: Optional[str] = None
    catalogue_item_properties: List[CatalogueItemProperty]


class CatalogueCategorySchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str
    code: str
    path: str
    parent_path: str
