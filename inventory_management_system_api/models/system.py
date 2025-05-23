"""
Module for defining the database models for representing systems.
"""

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.models.custom_object_id_data_types import (
    CustomObjectIdFieldType,
    StringObjectIdField,
)
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin

ParentSystemIdType = Annotated[
    CustomObjectId, CustomObjectIdFieldType(entity_type="parent system", not_found_if_invalid=False)
]


class SystemBase(BaseModel):
    """
    Base database model for a system
    """

    parent_id: Optional[ParentSystemIdType] = None
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str


class SystemIn(CreatedModifiedTimeInMixin, SystemBase):
    """
    Input database model for a system
    """


class SystemOut(CreatedModifiedTimeOutMixin, SystemBase):
    """
    Output database model for a system
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    model_config = ConfigDict(populate_by_name=True)
