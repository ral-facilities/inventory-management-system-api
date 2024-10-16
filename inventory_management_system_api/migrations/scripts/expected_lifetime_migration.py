"""
Module providing a migration for the optional expected_lifetime field under catalogue items
"""

import logging
from typing import Any, Collection, List, Optional

from pydantic import BaseModel, HttpUrl, field_serializer, field_validator
from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField

logger = logging.getLogger()

class OldCatalogueItem(BaseModel):
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


class Migration(BaseMigration):
    """Migration for Catalogue Items' Optional Expected Lifetime"""

    description = "Migration for Catalogue Items' Optional Expected Lifetime"

    def __init__(self, database: Database):

        self._catalogue_items_collection: Collection = database.catalogue_items

    def forward(self, session: ClientSession):
        """This function should actually perform the migration

        All database functions should be given the session in order to ensure all updates are done within a transaction
        """

        logger.info("expected_lifetime forward migration")
        result = self._catalogue_items_collection.update_many({}, {"$set": {"expected_lifetime": None}}, session = session)
        return result

    def backward(self, session: ClientSession):
        """This function should reverse the migration

        All database functions should be given the session in order to ensure all updates are done within a transaction
        """

        logger.info("expected_lifetime backward migration")
        result = self._catalogue_items_collection.update_many({}, {"$unset": {"expected_lifetime": ""}}, session = session)
        return result
