"""
Module providing a migration that adds number_of_spares_required and criticality to catalogue items, and is_flagged to
catalogue categories, catalogue items, and systems.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from typing import Any, Collection, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationInfo, field_serializer, field_validator
from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryPropertyIn,
    CatalogueCategoryPropertyOut,
)
from inventory_management_system_api.models.catalogue_item import PropertyIn, PropertyOut
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


class NewCatalogueCategoryBase(BaseModel):
    """
    Base database model for a catalogue category.
    """

    name: str
    code: str
    is_leaf: bool
    parent_id: Optional[CustomObjectIdField] = None
    properties: List[CatalogueCategoryPropertyIn] = []

    # Computed
    is_flagged: bool = False

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, properties: Any, info: ValidationInfo) -> Any:
        """
        Validator for the `properties` field that runs after field assignment but before type validation.

        If the value is `None`, it replaces it with an empty list allowing for catalogue categories without properties
        to be created. If the category is a non-leaf category and if properties are supplied, it replaces it with an
        empty list because they cannot have properties.

        :param properties: The list of properties.
        :param info: Validation info from pydantic.
        :return: The list of properties or an empty list.
        """
        if properties is None or ("is_leaf" in info.data and info.data["is_leaf"] is False and properties):
            properties = []

        return properties


class NewCatalogueCategoryIn(CreatedModifiedTimeInMixin, NewCatalogueCategoryBase):
    """
    Input database model for a catalogue category.
    """


class OldCatalogueCategoryBase(BaseModel):
    """
    Base database model for a catalogue category.
    """

    name: str
    code: str
    is_leaf: bool
    parent_id: Optional[CustomObjectIdField] = None
    properties: List[CatalogueCategoryPropertyIn] = []

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, properties: Any, info: ValidationInfo) -> Any:
        """
        Validator for the `properties` field that runs after field assignment but before type validation.

        If the value is `None`, it replaces it with an empty list allowing for catalogue categories without properties
        to be created. If the category is a non-leaf category and if properties are supplied, it replaces it with an
        empty list because they cannot have properties.

        :param properties: The list of properties.
        :param info: Validation info from pydantic.
        :return: The list of properties or an empty list.
        """
        if properties is None or ("is_leaf" in info.data and info.data["is_leaf"] is False and properties):
            properties = []

        return properties


class OldCatalogueCategoryOut(CreatedModifiedTimeOutMixin, OldCatalogueCategoryBase):
    """
    Output database model for a catalogue category.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None
    properties: List[CatalogueCategoryPropertyOut] = []

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


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

    # Computed
    number_of_spares: Optional[int] = None
    number_of_spares_required: Optional[float] = None
    criticality: Optional[float] = None
    is_flagged: Optional[bool] = None

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
    expected_lifetime_days: Optional[float] = None
    drawing_number: Optional[str] = None
    drawing_link: Optional[HttpUrl] = None
    item_model_number: Optional[str] = None
    is_obsolete: bool
    obsolete_reason: Optional[str] = None
    obsolete_replacement_catalogue_item_id: Optional[CustomObjectIdField] = None
    notes: Optional[str] = None
    properties: List[PropertyIn] = []

    # Computed
    number_of_spares: Optional[int] = None

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


class NewSystemBase(BaseModel):
    """
    Base database model for a system.
    """

    parent_id: Optional[CustomObjectIdField] = None
    name: str
    type_id: CustomObjectIdField = None
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str

    # Computed
    is_flagged: bool = False


class NewSystemIn(CreatedModifiedTimeInMixin, NewSystemBase):
    """
    Input database model for a system.
    """


class OldSystemBase(BaseModel):
    """
    Base database model for a system.
    """

    parent_id: Optional[CustomObjectIdField] = None
    name: str
    type_id: CustomObjectIdField = None
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str


class OldSystemOut(CreatedModifiedTimeOutMixin, OldSystemBase):
    """
    Output database model for a system.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None
    type_id: StringObjectIdField

    model_config = ConfigDict(populate_by_name=True)


class Migration(BaseMigration):
    """
    Migration that adds number_of_spares_required and criticality to catalogue items, and is_flagged to catalogue
    categories, catalogue items, and systems.
    """

    description = (
        "Adds number_of_spares_required and criticality to catalogue items, and is_flagged to catalogue categories,"
        "catalogue items, and systems."
    )

    def __init__(self, database: Database):
        self._catalogue_categories_collection: Collection = database.catalogue_categories
        self._catalogue_items_collection: Collection = database.catalogue_items
        self._systems_collection: Collection = database.systems

    def forward(self, session: ClientSession):
        """Applies database changes."""
        catalogue_categories = self._catalogue_categories_collection.find({}, session=session)
        for catalogue_category in catalogue_categories:
            old_catalogue_category = OldCatalogueCategoryOut(**catalogue_category)
            new_catalogue_category = NewCatalogueCategoryIn(**old_catalogue_category.model_dump())

            update_data = {
                **new_catalogue_category.model_dump(),
                "modified_time": old_catalogue_category.modified_time,
            }
            self._catalogue_categories_collection.replace_one(
                {"_id": catalogue_category["_id"]}, update_data, session=session
            )

        catalogue_items = self._catalogue_items_collection.find({}, session=session)
        for catalogue_item in catalogue_items:
            old_catalogue_item = OldCatalogueItemOut(**catalogue_item)
            new_catalogue_item = NewCatalogueItemIn(**old_catalogue_item.model_dump())

            update_data = {
                **new_catalogue_item.model_dump(),
                "modified_time": old_catalogue_item.modified_time,
            }
            self._catalogue_items_collection.replace_one({"_id": catalogue_item["_id"]}, update_data, session=session)

        systems = self._systems_collection.find({}, session=session)
        for system in systems:
            old_system = OldSystemOut(**system)
            new_system = NewSystemIn(**old_system.model_dump())

            update_data = {
                **new_system.model_dump(),
                "modified_time": old_system.modified_time,
            }
            self._systems_collection.replace_one({"_id": system["_id"]}, update_data, session=session)

    def backward(self, session: ClientSession):
        """Reverses database changes."""
        self._catalogue_categories_collection.update_many({}, {"$unset": {"is_flagged": ""}}, session=session)

        self._catalogue_items_collection.update_many(
            {}, {"$unset": {"number_of_spares_required": "", "criticality": "", "is_flagged": ""}}, session=session
        )

        self._systems_collection.update_many({}, {"$unset": {"is_flagged": ""}}, session=session)
