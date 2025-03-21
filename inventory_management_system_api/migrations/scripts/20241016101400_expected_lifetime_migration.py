"""
Module providing a migration that adds expected_lifetime_days to catalogue items.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from typing import Any, Collection, List, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration
from inventory_management_system_api.models.catalogue_item import PropertyIn, PropertyOut
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


class NewItemBase(BaseModel):
    """
    Base database model for an item.
    """

    catalogue_item_id: CustomObjectIdField
    system_id: CustomObjectIdField
    purchase_order_number: Optional[str] = None
    is_defective: bool
    usage_status_id: CustomObjectIdField
    usage_status: str
    warranty_end_date: Optional[AwareDatetime] = None
    asset_number: Optional[str] = None
    serial_number: Optional[str] = None
    delivered_date: Optional[AwareDatetime] = None
    expected_lifetime_days: Optional[float] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # pylint: disable=duplicate-code
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


class NewItemIn(CreatedModifiedTimeInMixin, NewItemBase):
    """
    Input database model for an item.
    """


class OldItemBase(BaseModel):
    """
    Base database model for an item.
    """

    catalogue_item_id: CustomObjectIdField
    system_id: CustomObjectIdField
    purchase_order_number: Optional[str] = None
    is_defective: bool
    usage_status_id: CustomObjectIdField
    usage_status: str
    warranty_end_date: Optional[AwareDatetime] = None
    asset_number: Optional[str] = None
    serial_number: Optional[str] = None
    delivered_date: Optional[AwareDatetime] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # pylint: disable=duplicate-code
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


class OldItemOut(CreatedModifiedTimeOutMixin, OldItemBase):
    """
    Output database model for an item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_item_id: StringObjectIdField
    system_id: Optional[StringObjectIdField] = None
    usage_status_id: StringObjectIdField
    properties: List[PropertyOut] = []

    model_config = ConfigDict(populate_by_name=True)


class Migration(BaseMigration):
    """Migration that adds expected_lifetime_days to catalogue items."""

    description = "Adds expected_lifetime_days to catalogue items"

    def __init__(self, database: Database):

        self._items_collection: Collection = database.items

    def forward(self, session: ClientSession):
        """Applies database changes."""
        items = self._items_collection.find({}, session=session)

        for item in items:
            old_item = OldItemOut(**item)
            new_item = NewItemIn(**old_item.model_dump())

            update_data = {
                **new_item.model_dump(),
                "modified_time": old_item.modified_time,
            }

            self._items_collection.replace_one({"_id": item["_id"]}, update_data, session=session)

    def backward(self, session: ClientSession):
        """Reverses database changes."""

        result = self._items_collection.update_many({}, {"$unset": {"expected_lifetime_days": ""}}, session=session)
        return result
