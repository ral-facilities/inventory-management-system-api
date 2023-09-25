"""
Module for defining the database models for representing manufacturer.
"""
from typing import Optional, List

from bson import ObjectId
from pydantic import BaseModel, Field

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.models.catalogue_category import StringObjectIdField
from inventory_management_system_api.schemas.manufacturer import AddressProperty


class ManufacturerIn(BaseModel):
    """Input database model for a catalogue category"""

    name: str
    url: str
    address: AddressProperty


class ManufacturerOut(ManufacturerIn):
    id: StringObjectIdField = Field(alias="_id")
