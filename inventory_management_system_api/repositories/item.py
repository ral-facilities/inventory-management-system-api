"""
Module for providing a repository for managing items in a MongoDB database.
"""

import logging
from typing import List, Optional

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database
from inventory_management_system_api.core.custom_object_id import CustomObjectId

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.item import ItemIn, ItemOut

logger = logging.getLogger()


class ItemRepo:
    """
    Repository for managing items in a MongoDB database.
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialize the `ItemRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._items_collection: Collection = self._database.items
        self._systems_collection: Collection = self._database.systems

    def create(self, item: ItemIn) -> ItemOut:
        """
        Create a new item in a MongoDB database.

        :param item: The item to be created.
        :return: The created item.
        """
        if item.system_id and not self._systems_collection.find_one({"_id": item.system_id}):
            raise MissingRecordError(f"No system found with ID: {item.system_id}")

        logger.info("Inserting the new item into the database")
        result = self._items_collection.insert_one(item.model_dump())

        item = self.get(str(result.inserted_id))
        return item

    def delete(self, item_id: str) -> None:
        """
        Delete an item by its ID from a MongoDB database.

        :param item_id: The ID of the item to delete.
        :raises MissingRecordError: If the item doesn't exist
        """
        item_id = CustomObjectId(item_id)
        logger.info("Deleting item with ID: %s from the database", item_id)
        result = self._items_collection.delete_one({"_id": item_id})
        if result.deleted_count == 0:
            raise MissingRecordError(f"No item found with ID: {str(item_id)}")

    def get(self, item_id: str) -> Optional[ItemOut]:
        """
        Retrieve an item by its ID from a MongoDB database.

        :param item_id: The ID of the item to retrieve
        :return: The retrieved item, or `None` if not found.
        """
        item_id = CustomObjectId(item_id)
        logger.info("Retrieving item with ID %s from the database", item_id)
        item = self._items_collection.find_one({"_id": item_id})
        if item:
            return ItemOut(**item)
        return None

    def list(self, system_id: Optional[str], catalogue_item_id: Optional[str]) -> List[ItemOut]:
        """
        Get all items from the MongoDB database

        :param system_id: The ID of the system to filter items by.
        :param catalogue_item_id: The ID of the catalogue item to filter by.
        :return List of items, or empty list if there are no items
        """
        query = {}
        if system_id:
            query["system_id"] = CustomObjectId(system_id)

        if catalogue_item_id:
            catalogue_item_id = CustomObjectId(catalogue_item_id)
            query["catalogue_item_id"] = catalogue_item_id

        message = "Retrieving all items from the database"
        if not query:
            logger.info(message)
        else:
            logger.info("%s matching the provided system ID and/or catalogue item ID filter", message)
            if system_id:
                logger.debug("Provided system ID filter: %s", system_id)
            if catalogue_item_id:
                logger.debug("Provided catalogue item ID filter: %s", catalogue_item_id)

        items = self._items_collection.find(query)
        return [ItemOut(**item) for item in items]

    def update(self, item_id: str, item: ItemIn) -> ItemOut:
        """
        Update an item by its ID in a MongoDB database.

        :param item_id: The ID of the item to update.
        :param item: The item containing the update data.
        :return: The updated item.
        """
        item_id = CustomObjectId(item_id)
        logger.info("Updating item with ID: %s in the database", item_id)
        self._items_collection.update_one({"_id": item_id}, {"$set": item.model_dump()})
        item = self.get(str(item_id))
        return item
