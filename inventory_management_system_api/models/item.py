"""
Module for defining the database models for representing items.
"""
from typing import Optional, List, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator, AwareDatetime

from inventory_management_system_api.models.catalogue_item import Property
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField


class ItemIn(BaseModel):
    """
    Input database model for an item.
    """

    catalogue_item_id: CustomObjectIdField
    system_id: Optional[CustomObjectIdField] = None
    purchase_order_number: Optional[str] = None
    is_defective: bool
    usage_status: int
    warranty_end_date: Optional[AwareDatetime] = None
    asset_number: Optional[str] = None
    serial_number: Optional[str] = None
    delivered_date: Optional[AwareDatetime] = None
    notes: Optional[str] = None
    catalogue_item_override_properties: List[Property] = []

    @field_validator("catalogue_item_override_properties", mode="before")
    @classmethod
    def validate_catalogue_item_override_properties(cls, catalogue_item_override_properties: Any) -> Any:
        """
        Validator for the `catalogue_item_override_properties` field that runs after field assignment but before type
        validation.

        If the value is `None`, it replaces it with an empty list allowing for items without override properties to be
        created.

        :param catalogue_item_override_properties: The list of override properties.
        :return: The list of override properties or an empty list.
        """
        if catalogue_item_override_properties is None:
            catalogue_item_override_properties = []
        return catalogue_item_override_properties


class ItemOut(ItemIn):
    """
    Output database model for an item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_item_id: StringObjectIdField
    system_id: Optional[StringObjectIdField] = None
    model_config = ConfigDict(populate_by_name=True)
