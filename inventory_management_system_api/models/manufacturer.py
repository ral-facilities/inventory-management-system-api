"""
Module for defining the database models for representing manufacturer.
"""


from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer

from inventory_management_system_api.models.catalogue_category import StringObjectIdField
from inventory_management_system_api.schemas.manufacturer import AddressSchema


class ManufacturerIn(BaseModel):
    """Input database model for a manufacturer"""

    name: str
    code: str
    url: Optional[HttpUrl] = None
    address: AddressSchema
    telephone: Optional[str] = None

    @field_serializer("url")
    def serialize_url(self, url: Optional[HttpUrl]):
        """
        Convert `url` to string when the model is dumped (provided it isn't None)
        :param url: The `HttpUrl` object or None
        :return: The URL as a string.
        """
        return url if url is None else str(url)


class ManufacturerOut(ManufacturerIn):
    """Output database model for a manufacturer"""

    id: StringObjectIdField = Field(alias="_id")
    model_config = ConfigDict(populate_by_name=True)
