"""
Module for defining the database models for representing items.
"""

from typing import Any, List, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from inventory_management_system_api.models.catalogue_item import PropertyIn, PropertyOut
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


def validate_properties(properties: Any) -> Any:
    """
    Method for validating properties specific to an item.

    If the value is `None`, it replaces it with an empty list allowing for items without properties to be created.

    :param properties: The list of properties specific to this item as defined in the corresponding catalogue
        category.
    :return: The list of properties specific to this item or an empty list.
    """
    if properties is None:
        properties = []
    return properties


class ItemBase(BaseModel):
    """
    Base database model for an item.
    """

    catalogue_item_id: CustomObjectIdField
    system_id: CustomObjectIdField
    purchase_order_number: Optional[str] = None
    is_defective: bool
    usage_status: int
    warranty_end_date: Optional[AwareDatetime] = None
    asset_number: Optional[str] = None
    serial_number: Optional[str] = None
    delivered_date: Optional[AwareDatetime] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # Validator for the `properties` field that runs after field assignment but before type validation
    validate_properties_field = field_validator("properties", mode="before")(validate_properties)


class ItemIn(CreatedModifiedTimeInMixin, ItemBase):
    """
    Input database model for an item.
    """


class ItemOut(CreatedModifiedTimeOutMixin, ItemBase):
    """
    Output database model for an item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_item_id: StringObjectIdField
    system_id: Optional[StringObjectIdField] = None
    properties: List[PropertyOut] = []
    model_config = ConfigDict(populate_by_name=True)

    # Validator for the `properties` field that runs after field assignment but before type validation
    validate_properties_field = field_validator("properties", mode="before")(validate_properties)
