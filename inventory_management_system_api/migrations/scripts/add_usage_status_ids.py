"""
Module providing a migration to add usage statuses, add usage_status_id to items converting and convert their
existing usage_status to a string value
"""

from typing import Any, List, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration
from inventory_management_system_api.models.catalogue_item import Property
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin
from inventory_management_system_api.services import utils

old_usage_statuses = {0: "New", 1: "Used", 2: "In Use", 3: "Scrapped"}


# pylint:disable=duplicate-code
class OldItemBase(BaseModel):
    """
    Old base database model for an item.
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


class OldItemIn(CreatedModifiedTimeInMixin, OldItemBase):
    """
    Old input database model for an item.
    """


class OldItemOut(CreatedModifiedTimeOutMixin, OldItemBase):
    """
    Old output database model for an item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_item_id: StringObjectIdField
    system_id: Optional[StringObjectIdField] = None
    model_config = ConfigDict(populate_by_name=True)


class NewItemBase(BaseModel):
    """
    New base database model for an item.
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


class NewItemIn(CreatedModifiedTimeInMixin, NewItemBase):
    """
    New database model for an item.
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
    properties: List[Property] = []


class NewItemOut(CreatedModifiedTimeOutMixin, NewItemBase):
    """
    Nww output database model for an item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_item_id: StringObjectIdField
    system_id: Optional[StringObjectIdField] = None
    usage_status_id: StringObjectIdField

    model_config = ConfigDict(populate_by_name=True)


# pylint:enable=duplicate-code


class Migration(BaseMigration):
    """Migration to add usage statuses, add usage_status_id to items converting and convert their
    existing usage_status to a string value"""

    def __init__(self, database: Database):
        self._items_collection: Collection = database.items
        self._usage_status_collection: Collection = database.usage_statuses

    def forward(self, session: ClientSession):
        """Migrates items to have usage_status_id's"""

        # Add in old usage statuses while keeping track of their ids
        usage_statuses = {}
        for old_usage_status, old_usage_status_string in old_usage_statuses.items():
            # Insert and store in dict for looking up old usage status id
            result = self._usage_status_collection.insert_one(
                {
                    "value": old_usage_status_string,
                    "code": utils.generate_code(old_usage_status_string, "usage status"),
                },
                session=session,
            )
            usage_statuses[old_usage_status] = self._usage_status_collection.find_one(
                {"_id": result.inserted_id}, session=session
            )

        items = list(self._items_collection.find(session=session))
        for item in items:
            item = OldItemOut(**item).model_dump()
            item_id = CustomObjectIdField(item["id"])

            item["usage_status_id"] = str(usage_statuses[item["usage_status"]]["_id"])
            item["usage_status"] = usage_statuses[item["usage_status"]]["value"]

            item = {**NewItemIn(**item).model_dump(), "modified_time": item["modified_time"]}

            self._items_collection.replace_one(
                {"_id": item_id},
                {
                    "$set": item,
                },
                session=session,
            )

    def backward(self, session: ClientSession):
        """Removes usage_status_id from items to undo the migration"""

        # Reverse the order of usage statuses
        usage_status_lookup = {
            old_usage_status_string: old_usage_status
            for old_usage_status, old_usage_status_string in old_usage_statuses.items()
        }

        items = list(self._items_collection.find(session=session))
        for item in items:
            item = NewItemOut(**item).model_dump()
            item_id = CustomObjectIdField(item["id"])

            del item["usage_status_id"]
            item["usage_status"] = usage_status_lookup[item["usage_status"]]

            item = {**OldItemIn(**item).model_dump(), "modified_time": item["modified_time"]}
            self._items_collection.replace_one(
                {"_id": item_id},
                item,
                session=session,
            )

        # Can't drop the collection during a transaction
        self._usage_status_collection.delete_many({}, session=session)

    def backward_after_transaction(self, session: ClientSession):
        """Drops the usage status collection"""
        # Cant drop inside transaction so do here
        self._usage_status_collection.drop(session=session)
