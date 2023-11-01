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

    parent_id: Optional[CustomObjectIdField] = None
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str


class SystemOut(SystemIn):
    """
    Output database model for a System
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    # Required just for unit tests
    class Config:
        # pylint: disable=C0115
        allow_population_by_field_name = True
