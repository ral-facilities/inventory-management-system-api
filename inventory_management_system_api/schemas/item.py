"""
Module for defining the API schema models for representing items.
"""
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, AwareDatetime

from inventory_management_system_api.schemas.catalogue_item import PropertyPostRequestSchema, PropertySchema


class ItemUsageStatus(int, Enum):
    """
    Enumeration for item usage statuses.
    """

    NEW = 0
    IN_USE = 1
    USED = 2
    SCRAPPED = 3


class ItemPostRequestSchema(BaseModel):
    """
    Schema model for an item creation request.
    """

    catalogue_item_id: str = Field(description="The ID of the corresponding catalogue item for this item")
    system_id: Optional[str] = Field(default=None, description="The ID of the system that the item belongs to")
    purchase_order_number: Optional[str] = Field(default=None, description="The purchase order number of the item")
    is_defective: bool = Field(description="Whether the item is defective or not")
    usage_status: ItemUsageStatus = Field(
        description="The usage status of the item. 0 means new, 1 means in use, 2 means used, and 3 means scrapped."
    )
    warranty_end_date: Optional[AwareDatetime] = Field(default=None, description="The warranty end date of the item")
    asset_number: Optional[str] = Field(default=None, description="The asset number of the item")
    serial_number: Optional[str] = Field(default=None, description="The serial number of the item")
    delivered_date: Optional[AwareDatetime] = Field(default=None, description="The date the item was delivered")
    notes: Optional[str] = Field(default=None, description="Any notes about the item")
    catalogue_item_override_properties: Optional[List[PropertyPostRequestSchema]] = Field(
        default=None,
        description="The overriden catalogue item properties specific to this item. The properties from the catalogue "
        "item are automatically used for the ones that are not overriden.",
    )


class ItemSchema(ItemPostRequestSchema):
    """
    Schema model for an item response.
    """

    id: str = Field(description="The ID of the item")
    catalogue_item_override_properties: List[PropertySchema] = Field(
        description="The overriden catalogue item properties specific to this item. The properties from the catalogue "
        "item are automatically used for the ones that are not overriden.",
    )
