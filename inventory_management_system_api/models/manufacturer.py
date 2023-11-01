"""
Module for defining the database models for representing manufacturer.
"""


from pydantic import BaseModel, Field, HttpUrl


from inventory_management_system_api.models.catalogue_category import StringObjectIdField


class ManufacturerIn(BaseModel):
    """Input database model for a manufacturer"""

    name: str
    code: str
    url: HttpUrl
    address: str


class ManufacturerOut(ManufacturerIn):
    """Output database model for a manufacturer"""

    id: StringObjectIdField = Field(alias="_id")
