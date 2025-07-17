"""
Module for defining the database models for representing systems.
"""

from typing import List, Optional

from inventory_management_system_api.models.catalogue_item import CatalogueItemOut
from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
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




class CatalogueItemNodeOut(BaseModel):
    """
    Schema model for the catalogue items for a single node in the systems tree 
    """
    id: StringObjectIdField = Field(alias="_id")
    catalogue_item: CatalogueItemOut
    itemsQuantity: int = Field(description="Quantity of items in the system")


class SystemNodeOut(SystemBase):
    """
    Schema model for a single node in the system tree
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    subsystems: Optional[List["SystemNodeOut"]] = Field(
        default=[], description="List of subsystems nested under this system"
    )
    catalogue_items: Optional[List[CatalogueItemNodeOut]] = Field(
        default=[], description="List of catalogue items under this system"
    )

    fullTree: Optional[bool] = None  # Add fullTree field

    model_config = ConfigDict(populate_by_name=True)


# Enable recursive models in Pydantic
SystemNodeOut.update_forward_refs()