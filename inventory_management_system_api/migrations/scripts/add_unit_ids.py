"""
Module providing a migration to add unit_ids to the properties stored within catalogue categories, catalogue
items and items
"""

from typing import Any, Optional, Union

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration
from inventory_management_system_api.models.catalogue_category import AllowedValues
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin
from inventory_management_system_api.services import utils

old_units = ["mm", "degrees", "nm", "ns", "Hz", "ppm", "J/cm²", "J", "W"]


class NewUnitBase(BaseModel):
    """
    New base database model for a Unit
    """

    value: str
    # Used for uniqueness checks (sanitised value)
    code: str


class NewUnitIn(CreatedModifiedTimeInMixin, NewUnitBase):
    """
    New input database model for a Unit
    """


# pylint:disable=duplicate-code
class OldCatalogueItemPropertyBase(BaseModel):
    """
    Old base database model for a catalogue item property.
    """

    name: str
    type: str
    unit: Optional[str] = None
    mandatory: bool
    allowed_values: Optional[AllowedValues] = None


class OldCatalogueItemPropertyOut(OldCatalogueItemPropertyBase):
    """
    Old output database model for a catalogue item property.
    """

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)

    def is_equal_without_id(self, other: Any) -> bool:
        """
        Compare this instance with another instance of `CatalogueItemPropertyOut` while ignoring the ID.

        :param other: An instance of a model to compare with.
        :return: `True` if the instances are of the same type and are equal when ignoring the ID field, `False`
            otherwise.
        """
        if not isinstance(other, OldCatalogueItemPropertyOut):
            return False

        return (
            self.name == other.name
            and self.type == other.type
            and self.unit == other.unit
            and self.mandatory == other.mandatory
            and self.allowed_values == other.allowed_values
        )


class NewCatalogueItemPropertyBase(BaseModel):
    """
    New base database model for a catalogue item property.
    """

    name: str
    type: str
    unit_id: Optional[CustomObjectIdField] = None
    unit: Optional[str] = None
    mandatory: bool
    allowed_values: Optional[AllowedValues] = None


class NewCatalogueItemPropertyIn(NewCatalogueItemPropertyBase):
    """
    Input database model for a catalogue item property.
    """

    # Because the catalogue item properties are stored in a list inside the catalogue categories and not in a separate
    # collection, it means that the IDs have to be manually generated here.
    id: CustomObjectIdField = Field(default_factory=ObjectId, serialization_alias="_id")


class OldPropertyOut(BaseModel):
    """
    Old model representing a catalogue item property.
    """

    id: StringObjectIdField = Field(alias="_id")
    name: str
    value: Any
    unit: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class NewPropertyIn(BaseModel):
    """
    New input database model for a catalogue item property
    """

    id: CustomObjectIdField = Field(serialization_alias="_id")
    name: str
    value: Any
    unit_id: Optional[CustomObjectIdField] = None
    unit: Optional[str] = None


# pylint:enable=duplicate-code


def add_unit_ids(
    old_property_out_type: Union[OldCatalogueItemPropertyOut, OldPropertyOut],
    new_property_in_type: Union[NewCatalogueItemPropertyIn, NewPropertyIn],
    new_unit_ids: list[dict],
    properties: list[dict],
):
    """
    Add unit ids to a list of properties by looking up the corresponding property in a given
    list of catalogue category properties

    :param new_unit_ids: New unit ids stored in a dict in the form {value: id}
    :param properties: List of properties to add ids to
    :return: List of properties but with the corresponding ids added
    """
    # For easy look up turn into dict of dicts instead of list of dicts using name as key
    for i, prop in enumerate(properties):
        if prop["unit"] is not None:
            unit = prop["unit"]
            unit_id = new_unit_ids.get(prop["unit"], None)
            if not unit_id:
                # This covers a case on dev machine where some units were given values of "" in the past
                if unit == "":
                    unit = None
                else:
                    raise ValueError(f"Could not find unit '{unit}' in list of new unit ids, could not migrate")
            else:
                unit_id = str(unit_id)

            properties[i] = new_property_in_type(
                **{
                    **old_property_out_type(**prop).model_dump(),
                    "unit": unit,
                    "unit_id": unit_id,
                }
            ).model_dump()
        else:
            properties[i] = new_property_in_type(
                **{**old_property_out_type(**prop).model_dump(), "unit_id": None}
            ).model_dump()

    return properties


def remove_unit_ids(properties: list[dict]):
    """Removes ids from a list of properties"""
    for i, _ in enumerate(properties):
        del (properties[i])["unit_id"]
    return properties


class Migration(BaseMigration):
    """Migration to add unit_ids to the properties stored within catalogue categories, catalogue
    items and items"""

    def __init__(self, database: Database):
        self._units_collection: Collection = database.units
        self._catalogue_categories_collection: Collection = database.catalogue_categories
        self._catalogue_items_collection: Collection = database.catalogue_items
        self._items_collection: Collection = database.items

    def forward(self, session: ClientSession):
        """Migrates catalogue categories, catalogue items and items to have unit_id's"""

        # First clear all existing unit data (generate new ids rather than looking them up - can't
        # guarantee they exist when testing locally as by the time this is used units.json will be gone)
        self._units_collection.delete_many({}, session=session)

        # New units for lookup (value: _id)
        new_unit_ids = {}

        # Add in the units
        for old_unit in old_units:
            result = self._units_collection.insert_one(
                NewUnitIn(value=old_unit, code=utils.generate_code(old_unit, "unit")).model_dump(), session=session
            )
            new_unit_ids[old_unit] = result.inserted_id

        # Migrate catalogue categories (only leaf has catalogue item properties)
        catalogue_categories = list(self._catalogue_categories_collection.find({"is_leaf": True}, session=session))
        for catalogue_category in catalogue_categories:
            catalogue_category["catalogue_item_properties"] = add_unit_ids(
                OldCatalogueItemPropertyOut,
                NewCatalogueItemPropertyIn,
                new_unit_ids,
                catalogue_category["catalogue_item_properties"],
            )
            self._catalogue_categories_collection.update_one(
                {"_id": catalogue_category["_id"]}, {"$set": catalogue_category}, session=session
            )

        # Migrate catalogue items
        catalogue_items = list(self._catalogue_items_collection.find({}, session=session))
        for catalogue_item in catalogue_items:
            catalogue_item["properties"] = add_unit_ids(
                OldPropertyOut, NewPropertyIn, new_unit_ids, catalogue_item["properties"]
            )
            self._catalogue_items_collection.update_one(
                {"_id": catalogue_item["_id"]}, {"$set": catalogue_item}, session=session
            )

        # Migrate items
        items = list(self._items_collection.find({}, session=session))
        for item in items:
            item["properties"] = add_unit_ids(OldPropertyOut, NewPropertyIn, new_unit_ids, item["properties"])
            self._items_collection.update_one({"_id": item["_id"]}, {"$set": item}, session=session)

    def backward(self, session: ClientSession):
        """Removes unit_id's from catalogue categories, catalogue items and items to undo the migration"""

        # First clear all existing unit data (simpler than deleting code)
        # This will not use fixed ids like the old units.json though
        self._units_collection.delete_many({}, session=session)
        for old_unit in old_units:
            self._units_collection.insert_one(
                {"value": old_unit, "code": utils.generate_code(old_unit, "unit")}, session=session
            )

        # Now remove unit_id from each entity in turn

        # Migrate catalogue categories (only leaf has catalogue item properties)
        catalogue_categories = list(self._catalogue_categories_collection.find({"is_leaf": True}, session=session))
        for catalogue_category in catalogue_categories:
            catalogue_category["catalogue_item_properties"] = remove_unit_ids(
                catalogue_category["catalogue_item_properties"]
            )
            self._catalogue_categories_collection.update_one(
                {"_id": catalogue_category["_id"]}, {"$set": catalogue_category}, session=session
            )

        # Migrate catalogue items
        catalogue_items = list(self._catalogue_items_collection.find({}, session=session))
        for catalogue_item in catalogue_items:
            catalogue_item["properties"] = remove_unit_ids(catalogue_item["properties"])
            self._catalogue_items_collection.update_one(
                {"_id": catalogue_item["_id"]}, {"$set": catalogue_item}, session=session
            )

        # Migrate items
        items = list(self._items_collection.find({}, session=session))
        for item in items:
            item["properties"] = remove_unit_ids(item["properties"])
            self._items_collection.update_one({"_id": item["_id"]}, {"$set": item}, session=session)
