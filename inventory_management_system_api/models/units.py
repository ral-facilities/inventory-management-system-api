"""
Module for defining the database models for representing a Unit
"""

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField


class UnitOut(BaseModel):
    """
    Output database model for a Unit
    """

    id: StringObjectIdField = Field(alias="_id")
    value: str

    model_config = ConfigDict(populate_by_name=True)
