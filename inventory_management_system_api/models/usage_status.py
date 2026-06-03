"""
Module for defining the database models for representing a Usage status
"""

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.mixins import BaseFieldsInMixin, BaseFieldsOutMixin


class UsageStatusBase(BaseModel):
    """
    Base database model for a UsageStatus
    """

    value: str
    # Used for uniqueness checks (sanitised value)
    code: str


class UsageStatusOut(BaseFieldsOutMixin, UsageStatusBase):
    """
    Output database model for a Usage status
    """

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)


class UsageStatusIn(BaseFieldsInMixin, UsageStatusBase):
    """
    Input database model for a Usage status
    """
