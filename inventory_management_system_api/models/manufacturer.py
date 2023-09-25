"""
Module for defining the database models for representing manufacturer.
"""


from pydantic import BaseModel, Field


from inventory_management_system_api.models.catalogue_category import StringObjectIdField
from inventory_management_system_api.schemas.manufacturer import AddressProperty


class ManufacturerIn(BaseModel):
    """Input database model for a manufacturer"""

    name: str
    url: str
    address: AddressProperty


class ManufacturerOut(ManufacturerIn):
    """Output model form database for manufacturer"""

    id: StringObjectIdField = Field(alias="_id")
