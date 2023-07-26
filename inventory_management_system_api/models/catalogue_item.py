"""
Module for defining the database models for representing catalogue items.
"""
from typing import Optional, List, Any

from pydantic import BaseModel, Field

from inventory_management_system_api.models.catalogue_category import CustomObjectIdField, StringObjectIdField


class Property(BaseModel):
    """
    Model representing a catalogue item property.
    """

    name: str
    value: Any
    unit: Optional[str] = None


class CatalogueItemIn(BaseModel):
    """
    Input database model for a catalogue item.
    """

    catalogue_category_id: CustomObjectIdField
    name: str
    description: str
    properties: List[Property]


class CatalogueItemOut(CatalogueItemIn):
    """
    Output database model for a catalogue item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_category_id: StringObjectIdField

    class Config:
        # pylint: disable=C0115
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
