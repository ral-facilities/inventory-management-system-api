"""
Module for defining the database models for representing catalogue items.
"""
from typing import Optional, List, Any

from pydantic import BaseModel, Field, validator

from inventory_management_system_api.models.catalogue_category import CustomObjectIdField, StringObjectIdField


class Manufacturer(BaseModel):
    """
    Model representing a catalogue item manufacturer.
    """

    name: str
    address: str
    web_url: Optional[str] = None


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
    manufacturer: Manufacturer

    @validator("properties", pre=True, always=True)
    @classmethod
    def validate_properties(cls, properties: List[Property] | None) -> List[Property] | List:
        """
        Validator for the `properties` field that runs always (even if the field is missing) and before any Pydantic
        validation checks.

        If the value is `None`, it replaces it with an empty list.

        :param properties: The list of properties.
        :return: The list of properties or an empty list.
        """
        if properties is None:
            properties = []
        return properties


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
