"""
Module for defining the database models for representing a Unit
"""

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


class UnitBase(BaseModel):
    """
    Base database model for a Unit
    """

    value: str = Field(description="Value of the Unit")
    # Used for uniqueness checks (sanitised value)
    code: str = Field(description="Code of the Unit")


class UnitOut(CreatedModifiedTimeOutMixin, UnitBase):
    """
    Output database model for a Unit
    """

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)


class UnitIn(CreatedModifiedTimeInMixin, UnitBase):
    """
    Input database model for a Unit
    """
