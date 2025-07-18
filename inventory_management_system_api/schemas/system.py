"""
Module for defining the API schema models for representing systems.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.catalogue_item import CatalogueItemSchema
from inventory_management_system_api.schemas.item import ItemSchema
from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class SystemImportanceType(str, Enum):
    """
    Enumeration for system importance types.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SystemPostSchema(BaseModel):
    """
    Schema model for a system creation request.
    """

    parent_id: Optional[str] = Field(default=None, description="ID of the parent system (if applicable)")
    name: str = Field(description="Name of the system")
    description: Optional[str] = Field(default=None, description="Description of the system")
    location: Optional[str] = Field(default=None, description="Location of the system")
    owner: Optional[str] = Field(default=None, description="Owner of the systems")
    importance: SystemImportanceType = Field(description="Importance of the system")


class SystemPatchSchema(SystemPostSchema):
    """
    Schema model for a system update request.
    """

    name: Optional[str] = Field(default=None, description="Name of the system")
    importance: Optional[SystemImportanceType] = Field(default=None, description="Importance of the system")


class SystemSchema(CreatedModifiedSchemaMixin, SystemPostSchema):
    """
    Schema model for system get request response.
    """

    id: str = Field(description="ID of the system")
    code: str = Field(description="Code of the system")


class CatalogueItemNode(CatalogueItemSchema):
    items: List[ItemSchema]
    flagged: bool


class SystemTreeNode(SystemSchema):

    subsystems: List["SystemTreeNode"]
    catalogue_items: List[CatalogueItemNode]
    flagged: bool
