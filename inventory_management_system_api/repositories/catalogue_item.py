"""
Module for providing a repository for managing catalogue items in a MongoDB database.
"""
import logging
from typing import Optional, List

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut, CatalogueItemIn

logger = logging.getLogger()


class CatalogueItemRepo:
    """
    Repository for managing catalogue items in a MongoDB database.
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialize the `CatalogueItemRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._collection: Collection = self._database.catalogue_items

    def create(self, catalogue_item: CatalogueItemIn) -> CatalogueItemOut:
        """
        Create a new catalogue item in a MongoDB database.

        :param catalogue_item: The catalogue item to be created.
        :return: The created catalogue item.
        """
        logger.info("Inserting the new catalogue item into the database")
        result = self._collection.insert_one(catalogue_item.dict())
        catalogue_item = self.get(str(result.inserted_id))
        return catalogue_item

    def delete(self, catalogue_item_id: str) -> None:
        """
        Delete a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to delete.
        :raises MissingRecordError: If the catalogue item doesn't exist.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)
        # pylint: disable=fixme
        # TODO - (when the relevant item logic is implemented) check if catalogue item has children elements
        logger.info("Deleting catalogue item with ID: %s from the database", catalogue_item_id)
        result = self._collection.delete_one({"_id": catalogue_item_id})
        if result.deleted_count == 0:
            raise MissingRecordError(f"No catalogue item found with ID: {str(catalogue_item_id)}")

    def get(self, catalogue_item_id: str) -> Optional[CatalogueItemOut]:
        """
        Retrieve a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to retrieve.
        :return: The retrieved catalogue item, or `None` if not found.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)
        logger.info("Retrieving catalogue item with ID: %s from the database", catalogue_item_id)
        catalogue_item = self._collection.find_one({"_id": catalogue_item_id})
        if catalogue_item:
            return CatalogueItemOut(**catalogue_item)
        return None

    def update(self, catalogue_item_id: str, catalogue_item: CatalogueItemIn) -> CatalogueItemOut:
        """
        Update a catalogue item by its ID in a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to update.
        :param catalogue_item: The catalogue item containing the update data.
        :return: The updated catalogue item.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)
        # pylint: disable=fixme
        # TODO - (when the relevant item logic is implemented) check if catalogue item has children elements if the
        #  `catalogue_category_id` is being updated.
        logger.info("Updating catalogue item with ID: %s in the database", catalogue_item_id)
        self._collection.update_one({"_id": catalogue_item_id}, {"$set": catalogue_item.dict()})
        catalogue_item = self.get(str(catalogue_item_id))
        return catalogue_item

    def list(self, catalogue_category_id: Optional[str]) -> List[CatalogueItemOut]:
        """
        Retrieve all catalogue items from a MongoDB.

        :param catalogue_category_id: The ID of the catalogue category to filter catalogue items by.
        :return: A list of catalogue items, or an empty list if no catalogue items are returned by the database.
        """
        query = {}
        if catalogue_category_id:
            catalogue_category_id = CustomObjectId(catalogue_category_id)
            query["catalogue_category_id"] = catalogue_category_id

        message = "Retrieving all catalogue items from the database"
        if not query:
            logger.info(message)
        else:
            logger.info("%s matching the provided catalogue category ID filter", message)
            logger.debug("Provided catalogue category ID filter: %s", catalogue_category_id)

        catalogue_items = self._collection.find(query)
        return [CatalogueItemOut(**catalogue_item) for catalogue_item in catalogue_items]
