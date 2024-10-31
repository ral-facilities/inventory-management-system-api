"""
Module providing a migration for the optional expected_lifetime_days field under catalogue items
"""

import logging
from typing import Any, Collection, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
)
from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration
from inventory_management_system_api.models.catalogue_item import (
    PropertyIn,
    PropertyOut,
)
from inventory_management_system_api.models.custom_object_id_data_types import (
    CustomObjectIdField,
    StringObjectIdField,
)
from inventory_management_system_api.models.mixins import (
    CreatedModifiedTimeInMixin,
    CreatedModifiedTimeOutMixin,
)

logger = logging.getLogger()


# pylint: disable=duplicate-code
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
    expected_lifetime_days: Optional[float] = None
    drawing_number: Optional[str] = None
    drawing_link: Optional[HttpUrl] = None
    item_model_number: Optional[str] = None
    is_obsolete: bool
    obsolete_reason: Optional[str] = None
    obsolete_replacement_catalogue_item_id: Optional[CustomObjectIdField] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

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

    @field_serializer("drawing_link")
    def serialize_url(self, url: HttpUrl):
        """
        Convert `url` to string when the model is dumped.
        :param url: The `HttpUrl` object.
        :return: The URL as a string.
        """
        return url if url is None else str(url)


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


# pylint: enable=duplicate-code


class Migration(BaseMigration):
    """Migration for Catalogue Items' Optional Expected Lifetime Days Field"""

    description = "Migration for Catalogue Items' Optional Expected Lifetime Days Field"

    def __init__(self, database: Database):

        self._catalogue_items_collection: Collection = database.catalogue_items

    def forward(self, session: ClientSession):
        """Forward Migration for Catalogue Items' Optional Expected Lifetime Days Field"""
        catalogue_items = self._catalogue_items_collection.find({}, session=session)

        logger.info("expected_lifetime_days forward migration")
        for catalogue_item in catalogue_items:
            old_catalogue_item = OldCatalogueItemOut(**catalogue_item)

            new_catalogue_item = NewCatalogueItemIn(**old_catalogue_item.model_dump())

            update_data = {
                **new_catalogue_item.model_dump(),
                "modified_time": old_catalogue_item.modified_time,
            }

            self._catalogue_items_collection.replace_one(
                {"_id": catalogue_item["_id"]},
                update_data,
                session=session,
            )

    def backward(self, session: ClientSession):
        """Backward Migration for Catalogue Items' Optional Expected Lifetime Days Field"""

        logger.info("expected_lifetime_days backward migration")
        result = self._catalogue_items_collection.update_many(
            {}, {"$unset": {"expected_lifetime_days": ""}}, session=session
        )
        return result
