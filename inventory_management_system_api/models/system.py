"""
Module for defining the database models for representing a System
"""

from typing import Optional

from pydantic import BaseModel, Field

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField


class SystemIn(BaseModel):
    """
    Input database model for a System
    """

    name: str
    location: str
    owner: str
    importance: str

    # These two are purely for front end navigation
    path: str
    parent_path: str

    parent_id: Optional[CustomObjectIdField] = None


class SystemOut(SystemIn):
    """
    Output database model for a System
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None
