"""
Module for defining the database models for representing systems.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.catalogue_item import CatalogueItemOut
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.item import ItemOut
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


class SystemBase(BaseModel):
    """
    Base database model for a system.
    """

    parent_id: Optional[CustomObjectIdField] = None
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str


class SystemIn(CreatedModifiedTimeInMixin, SystemBase):
    """
    Input database model for a system.
    """


class SystemOut(CreatedModifiedTimeOutMixin, SystemBase):
    """
    Output database model for a system.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    model_config = ConfigDict(populate_by_name=True)


class CatalogueItemNodeOut(CatalogueItemOut):
    items: List[ItemOut]
    flagged: bool


class SystemTreeNodeOut(SystemOut):

    subsystems: List["SystemTreeNodeOut"]
    catalogue_items: List[CatalogueItemNodeOut]
    flagged: bool
