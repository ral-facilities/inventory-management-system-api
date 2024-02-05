"""
Module for defining the database models for representing items.
"""

from typing import Optional, List, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator, AwareDatetime

from inventory_management_system_api.models.catalogue_item import Property
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField

# pylint: disable=duplicate-code


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
    properties: List[Property] = []

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, properties: Any) -> Any:
        """
        Validator for the `properties` field that runs after field assignment but before type validation.

        If the value is `None`, it replaces it with an empty list allowing for items without properties to be created.

        :param properties: The list of properties specific to this item as defined in the corresponding catalogue
            category.
        :return: The list of properties specific to this item or an empty list.
        """
        if properties is None:
            properties = []
        return properties


# pylint: enable=duplicate-code


class ItemOut(ItemIn):
    """
    Output database model for an item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_item_id: StringObjectIdField
    system_id: Optional[StringObjectIdField] = None
    model_config = ConfigDict(populate_by_name=True)
