"""
Module providing a migration to add property ids to catalogue categories, catalogue items and items
"""

from bson import ObjectId
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration


def add_property_ids(catalogue_category_properties: list[dict], properties: list[dict]):
    """
    Add property ids to a list of properties by looking up the corresponding property in a given
    list of catalogue category properties

    :param catalogue_category_properties: Catalogue category properties (with ids added)
    :param properties: List of properties to add ids to
    :return: List of properties but with the corresponding ids added
    """
    # For easy look up turn into dict of dicts instead of list of dicts using name as key
    catalogue_category_properties_dict = {prop["name"]: prop for prop in catalogue_category_properties}

    for i, prop in enumerate(properties):
        catalogue_category_property = catalogue_category_properties_dict.get(prop["name"], None)
        if not catalogue_category_property:
            raise ValueError(f"Could not find property '{prop['name']}' in catalogue category, could not migrate")

        properties[i] = {"_id": catalogue_category_property["_id"], **prop}

    return properties


def remove_property_ids(properties: list[dict]):
    """Removes ids from a list of properties"""
    for i, _ in enumerate(properties):
        del (properties[i])["_id"]
    return properties


class Migration(BaseMigration):
    """Migration to add property ids to catalogue categories, catalogue items and items"""

    def __init__(self, database: Database):
        self._catalogue_categories_collection: Collection = database.catalogue_categories
        self._catalogue_items_collection: Collection = database.catalogue_items
        self._items_collection: Collection = database.items

    def modify(self, session: ClientSession, backward: bool):
        """
        Does the add/removal of ids
        """
        # Get all leaf catalogue categories (these have properties)
        catalogue_categories = list(self._catalogue_categories_collection.find({"is_leaf": True}, session=session))

        # Each catalogue category needs ids for the properties
        for catalogue_category in catalogue_categories:
            if not backward:
                # For each property generate the id
                for i, prop in enumerate(catalogue_category.get("catalogue_item_properties", [])):
                    catalogue_category["catalogue_item_properties"][i] = {"_id": ObjectId(), **prop}
            else:
                catalogue_category["catalogue_item_properties"] = remove_property_ids(
                    catalogue_category["catalogue_item_properties"]
                )

            # Find all catalogue items within the catalogue category
            catalogue_items = list(
                self._catalogue_items_collection.find(
                    {"catalogue_category_id": catalogue_category["_id"]}, session=session
                )
            )

            for catalogue_item in catalogue_items:
                if not backward:
                    # Now need to merge in, use the names to distinguish
                    catalogue_item["properties"] = add_property_ids(
                        catalogue_category["catalogue_item_properties"], catalogue_item["properties"]
                    )
                else:
                    catalogue_item["properties"] = remove_property_ids(catalogue_item["properties"])

                # Find all items within the catalogue item
                items = list(self._items_collection.find({"catalogue_item_id": catalogue_item["_id"]}, session=session))

                for item in items:
                    if not backward:
                        item["properties"] = add_property_ids(
                            catalogue_category["catalogue_item_properties"], item["properties"]
                        )
                    else:
                        item["properties"] = remove_property_ids(item["properties"])

                    self._items_collection.update_one({"_id": item["_id"]}, {"$set": item}, session=session)

                self._catalogue_items_collection.update_one(
                    {"_id": catalogue_item["_id"]}, {"$set": catalogue_item}, session=session
                )

            self._catalogue_categories_collection.update_one(
                {"_id": catalogue_category["_id"]}, {"$set": catalogue_category}, session=session
            )

    def forward(self, session: ClientSession):
        """Migrates properties to have ids"""
        self.modify(session, False)

    def backward(self, session: ClientSession):
        """Removes property ids to undo the migration"""
        self.modify(session, True)
