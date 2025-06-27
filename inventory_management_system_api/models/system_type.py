"""
Module for defining the database models for representing system types.
"""

from pydantic import BaseModel, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField


class SystemTypeOut(BaseModel):
    """
    Output database model for a system type.
    """

    id: StringObjectIdField = Field(alias="_id")
    value: str
