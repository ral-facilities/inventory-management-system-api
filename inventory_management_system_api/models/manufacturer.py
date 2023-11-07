"""
Module for defining the database models for representing manufacturer.
"""
from pydantic import BaseModel, Field, HttpUrl, field_serializer

from inventory_management_system_api.models.catalogue_category import StringObjectIdField


class ManufacturerIn(BaseModel):
    """Input database model for a manufacturer"""

    name: str
    code: str
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


class ManufacturerOut(ManufacturerIn):
    """Output database model for a manufacturer"""

    id: StringObjectIdField = Field(alias="_id")
