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

        # pylint: disable=fixme
        # TODO - Use the `get` repo method when implemented to get the item
        return ItemOut(**self._items_collection.find_one({"_id": result.inserted_id}))

    def list(self, system_id: Optional[str], catalogue_item_id: Optional[str]) -> List[ItemOut]:
        """
        Get all items from the MongoDB database

        :param system_id: The ID of the system to filter items by.
        :param catalogue_item_id: The ID of the catalogue item to filter by.
        :return List of items, or empty list if there are no items
        """
        query = {}
        if system_id:
            system_id = CustomObjectId(system_id)
            query["system_id"] = system_id
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
