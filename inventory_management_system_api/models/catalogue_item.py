"""
Module for defining the database models for representing catalogue items.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


def validate_properties(properties: Any) -> Any:
    """
    Method for validating properties specific to a catalogue item.

    :param properties: The list of properties specific to this catalogue item as defined in the corresponding
        catalogue category.
    :return: The list of properties specific to this catalogue item or an empty list.
    """
    if properties is None:
        properties = []
    return properties


class PropertyIn(BaseModel):
    """
    Model representing a catalogue item property.
    """

    id: CustomObjectIdField = Field(serialization_alias="_id")
    name: str
    value: Any
    unit: Optional[str] = None


class PropertyOut(BaseModel):
    """
    Model representing a catalogue item property.
    """

    id: StringObjectIdField = Field(alias="_id")
    name: str
    value: Any
    unit: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class CatalogueItemBase(BaseModel):
    """
    Base database model for a catalogue item.
    """

    catalogue_category_id: CustomObjectIdField
    manufacturer_id: CustomObjectIdField
    name: str
    description: Optional[str] = None
    cost_gbp: float
    cost_to_rework_gbp: Optional[float] = None
    days_to_replace: float
    days_to_rework: Optional[float] = None
    drawing_number: Optional[str] = None
    drawing_link: Optional[HttpUrl] = None
    item_model_number: Optional[str] = None
    is_obsolete: bool
    obsolete_reason: Optional[str] = None
    obsolete_replacement_catalogue_item_id: Optional[CustomObjectIdField] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # Validator for the `properties` field that runs after field assignment but before type validation
    validate_properties_field = field_validator("properties", mode="before")(validate_properties)

    @field_serializer("drawing_link")
    def serialize_url(self, url: HttpUrl):
        """
        Convert `url` to string when the model is dumped.
        :param url: The `HttpUrl` object.
        :return: The URL as a string.
        """
        return url if url is None else str(url)


class CatalogueItemIn(CreatedModifiedTimeInMixin, CatalogueItemBase):
    """
    Input database model for a catalogue item.
    """


class CatalogueItemOut(CreatedModifiedTimeOutMixin, CatalogueItemBase):
    """
    Output database model for a catalogue item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_category_id: StringObjectIdField
    manufacturer_id: StringObjectIdField
    obsolete_replacement_catalogue_item_id: Optional[StringObjectIdField] = None
    properties: List[PropertyOut] = []
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    # Validator for the `properties` field that runs after field assignment but before type validation.
    validate_properties_field = field_validator("properties", mode="before")(validate_properties)
