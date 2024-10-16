"""
Module providing a migration for the optional expected_lifetime field under catalogue items
"""

import logging
from typing import Any, Collection, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator
from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin

logger = logging.getLogger()

class PropertyIn(BaseModel):
    """
    Input database model for a property defined within a catalogue item or item
    """

    id: CustomObjectIdField = Field(serialization_alias="_id")
    name: str
    value: Any
    unit_id: Optional[CustomObjectIdField] = None
    unit: Optional[str] = None


class PropertyOut(BaseModel):
    """
    Output database model for a property defined within a catalogue item or item
    """

    id: StringObjectIdField = Field(alias="_id")
    name: str
    value: Any
    unit_id: Optional[StringObjectIdField] = None
    unit: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class NewCatalogueItemBase(BaseModel):
    """
    Base database model for a catalogue item.
    """

    catalogue_category_id: CustomObjectIdField
    manufacturer_id: CustomObjectIdField
    name: str
    description: Optional[str] = None
    cost_gbp: float
    cost_to_rework_gbp: Optional[float] = None
    days_to_replace: float
    days_to_rework: Optional[float] = None
    drawing_number: Optional[str] = None
    drawing_link: Optional[HttpUrl] = None
    expected_lifetime: Optional[float] = None
    item_model_number: Optional[str] = None
    is_obsolete: bool
    obsolete_reason: Optional[str] = None
    obsolete_replacement_catalogue_item_id: Optional[CustomObjectIdField] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # pylint: disable=duplicate-code
    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, properties: Any) -> Any:
        """
        Validator for the `properties` field that runs after field assignment but before type validation.
        If the value is `None`, it replaces it with an empty list allowing for catalogue items without properties to be
        created.
        :param properties: The list of properties specific to this catalogue item as defined in the corresponding
            catalogue category.
        :return: The list of properties specific to this catalogue item or an empty list.
        """
        if properties is None:
            properties = []
        return properties

    # pylint: enable=duplicate-code

    @field_serializer("drawing_link")
    def serialize_url(self, url: HttpUrl):
        """
        Convert `url` to string when the model is dumped.
        :param url: The `HttpUrl` object.
        :return: The URL as a string.
        """
        return url if url is None else str(url)
class NewCatalogueItemIn(CreatedModifiedTimeInMixin, NewCatalogueItemBase):
    """
    Input database model for a catalogue item.
    """


class NewCatalogueItemOut(CreatedModifiedTimeOutMixin, NewCatalogueItemBase):
    """
    Output database model for a catalogue item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_category_id: StringObjectIdField
    manufacturer_id: StringObjectIdField
    obsolete_replacement_catalogue_item_id: Optional[StringObjectIdField] = None
    properties: List[PropertyOut] = []

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class OldCatalogueItemBase(BaseModel):
    """
    Base database model for a catalogue item.
    """

    catalogue_category_id: CustomObjectIdField
    manufacturer_id: CustomObjectIdField
    name: str
    description: Optional[str] = None
    cost_gbp: float
    cost_to_rework_gbp: Optional[float] = None
    days_to_replace: float
    days_to_rework: Optional[float] = None
    drawing_number: Optional[str] = None
    drawing_link: Optional[HttpUrl] = None
    item_model_number: Optional[str] = None
    is_obsolete: bool
    obsolete_reason: Optional[str] = None
    obsolete_replacement_catalogue_item_id: Optional[CustomObjectIdField] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # pylint: disable=duplicate-code
    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, properties: Any) -> Any:
        """
        Validator for the `properties` field that runs after field assignment but before type validation.
        If the value is `None`, it replaces it with an empty list allowing for catalogue items without properties to be
        created.
        :param properties: The list of properties specific to this catalogue item as defined in the corresponding
            catalogue category.
        :return: The list of properties specific to this catalogue item or an empty list.
        """
        if properties is None:
            properties = []
        return properties

    # pylint: enable=duplicate-code

    @field_serializer("drawing_link")
    def serialize_url(self, url: HttpUrl):
        """
        Convert `url` to string when the model is dumped.
        :param url: The `HttpUrl` object.
        :return: The URL as a string.
        """
        return url if url is None else str(url)
class OldCatalogueItemIn(CreatedModifiedTimeInMixin, OldCatalogueItemBase):
    """
    Input database model for a catalogue item.
    """


class OldCatalogueItemOut(CreatedModifiedTimeOutMixin, OldCatalogueItemBase):
    """
    Output database model for a catalogue item.
    """

    id: StringObjectIdField = Field(alias="_id")
    catalogue_category_id: StringObjectIdField
    manufacturer_id: StringObjectIdField
    obsolete_replacement_catalogue_item_id: Optional[StringObjectIdField] = None
    properties: List[PropertyOut] = []

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)



class Migration(BaseMigration):
    """Migration for Catalogue Items' Optional Expected Lifetime"""

    description = "Migration for Catalogue Items' Optional Expected Lifetime"

    def __init__(self, database: Database):

        self._catalogue_items_collection: Collection = database.catalogue_items

    def forward(self, session: ClientSession):
        """This function should actually perform the migration

        All database functions should be given the session in order to ensure all updates are done within a transaction
        """
        catalogue_items = self._catalogue_items_collection.find({}, session=session)

        logger.info("expected_lifetime forward migration")
        for catalogue_item in catalogue_items:
            try:
                old_item = OldCatalogueItemOut(**catalogue_item)
                
                new_item_data = {
                    "catalogue_category_id": old_item.catalogue_category_id,
                    "manufacturer_id": old_item.manufacturer_id,
                    "name": old_item.name,
                    "description": old_item.description,
                    "cost_gbp": old_item.cost_gbp,
                    "cost_to_rework_gbp": old_item.cost_to_rework_gbp,
                    "days_to_replace": old_item.days_to_replace,
                    "days_to_rework": old_item.days_to_rework,
                    "drawing_number": old_item.drawing_number,
                    "drawing_link": old_item.drawing_link,
                    "expected_lifetime": None,
                    "item_model_number": old_item.item_model_number,
                    "is_obsolete": old_item.is_obsolete,
                    "obsolete_reason": old_item.obsolete_reason,
                    "obsolete_replacement_catalogue_item_id": old_item.obsolete_replacement_catalogue_item_id,
                    "notes": old_item.notes,
                    "properties": old_item.properties,
                    "created_time": catalogue_item["created_time"],
                    "modified_time": catalogue_item["modified_time"]
                }

                new_item = NewCatalogueItemIn(**new_item_data)

                update_data = new_item.model_dump()

                # Step 5: Update the document back into the collection, preserving 'modified_time'
                self._catalogue_items_collection.update_one(
                    {"_id": old_item.id},
                    {"$set": update_data},
                    session=session
                )

            except Exception as e:
                logger.error(f"Validation or migration failed for item with id {catalogue_item['_id']}: {e}")
                continue

    def backward(self, session: ClientSession):
        """This function should reverse the migration

        All database functions should be given the session in order to ensure all updates are done within a transaction
        """

        logger.info("expected_lifetime backward migration")
        result = self._catalogue_items_collection.update_many({}, {"$unset": {"expected_lifetime": ""}}, session = session)
        return result
