"""
Module for providing a repository for managing items in a MongoDB database.
"""
import logging

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database
from inventory_management_system_api.core.custom_object_id import CustomObjectId

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField
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