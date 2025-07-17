"""
Module for defining the API schema models for representing systems.
"""

from enum import Enum
from typing import List, Optional

from inventory_management_system_api.schemas.catalogue_item import CatalogueItemSchema
from pydantic import BaseModel, Field

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


class CatalogueItemNodeSchema(BaseModel):
    """
    Schema model for the catalogue items for a single node in the systems tree 
    """
    id: str = Field(description="ID of the system")
    catalogue_item: CatalogueItemSchema
    itemsQuantity: int = Field(description="Quantity of items in the system")


class SystemNodeSchema(SystemPostSchema):
    """
    Schema model for a single node in the system tree
    """

    id: str = Field(description="ID of the system")
    code: str = Field(description="Code of the system")

    subsystems: Optional[List["SystemNodeSchema"]] = Field(
        default=[], description="List of subsystems nested under this system"
    )
    catalogue_items: Optional[List[CatalogueItemNodeSchema]] = Field(
        default=[], description="List of catalogue items under this system"
    )

    fullTree: Optional[bool] = Field(
        default=[], description="Is this the full tree"
    )


# Enable recursive models in Pydantic
SystemNodeSchema.update_forward_refs()
