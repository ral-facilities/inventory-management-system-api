"""
Module for defining the database models for representing catalogue items.
"""
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl, field_serializer

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField


class Property(BaseModel):
    """
    Model representing a catalogue item property.
    """

    name: str
    value: Any
    unit: Optional[str] = None


class Manufacturer(BaseModel):
    """Input database model for a manufacturer"""

    name: str
    url: HttpUrl
    address: str

    @field_serializer("url")
    def serialize_url(self, url: HttpUrl):
        """
        Convert `url` to string when the model is dumped.
        :param url: The `HttpUrl` object.
        :return: The URL as a string.
        """
        return url if url is None else str(url)


class CatalogueItemIn(BaseModel):
    """
    Input database model for a catalogue item.
    """

    catalogue_category_id: CustomObjectIdField
    manufacturer: Manufacturer  # TODO - Change from manufacturer to manufacturer id # pylint: disable=fixme
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
    obsolete_replace_catalogue_item_id: Optional[CustomObjectIdField] = None
    properties: List[Property] = []

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, properties: Any) -> Any:
        """
        Validator for the `properties` field that runs after field assignment but before type validation.

        If the value is `None`, it replaces it with an empty list allowing for catalogue items without properties to be
        created.

        :param properties: The list of properties.
        :return: The list of properties or an empty list.
        """
        if properties is None:
            properties = []
        return properties

    @field_serializer("drawing_link")
    def serialize_url(self, url: HttpUrl):
        """
        Convert `url` to string when the model is dumped.
        :param url: The `HttpUrl` object.
        :return: The URL as a string.
        """
        return url if url is None else str(url)


class CatalogueItemOut(CatalogueItemIn):
    """
    Output database model for a catalogue item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_category_id: StringObjectIdField
    obsolete_replace_catalogue_item_id: Optional[StringObjectIdField] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
