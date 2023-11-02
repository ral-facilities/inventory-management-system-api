"""
Module for defining the database models for representing manufacturer.
"""


from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


from inventory_management_system_api.models.catalogue_category import StringObjectIdField
from inventory_management_system_api.schemas.manufacturer import AddressSchema


class ManufacturerIn(BaseModel):
    """Input database model for a manufacturer"""

    name: str
    code: str
    url: Optional[HttpUrl] = None
    address: AddressSchema
    telephone: Optional[str] = None


class ManufacturerOut(ManufacturerIn):
    """Output database model for a manufacturer"""

    id: StringObjectIdField = Field(alias="_id")
