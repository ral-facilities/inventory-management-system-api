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
from inventory_management_system_api.core.exceptions import ChildElementsExistError, MissingRecordError
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
        self._catalogue_items_collection: Collection = self._database.catalogue_items
        self._items_collection: Collection = self._database.items

    def create(self, catalogue_item: CatalogueItemIn) -> CatalogueItemOut:
        """
        Create a new catalogue item in a MongoDB database.

        :param catalogue_item: The catalogue item to be created.
        :return: The created catalogue item.
        """
        logger.info("Inserting the new catalogue item into the database")
        result = self._catalogue_items_collection.insert_one(catalogue_item.model_dump(by_alias=True))
        catalogue_item = self.get(str(result.inserted_id))
        return catalogue_item

    def delete(self, catalogue_item_id: str) -> None:
        """
        Delete a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to delete.
        :raises MissingRecordError: If the catalogue item doesn't exist.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)
        if self.has_child_elements(catalogue_item_id):
            raise ChildElementsExistError(
                f"Catalogue item with ID {str(catalogue_item_id)} has child elements and cannot be deleted"
            )

        logger.info("Deleting catalogue item with ID: %s from the database", catalogue_item_id)
        result = self._catalogue_items_collection.delete_one({"_id": catalogue_item_id})
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
        catalogue_item = self._catalogue_items_collection.find_one({"_id": catalogue_item_id})
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

        logger.info("Updating catalogue item with ID: %s in the database", catalogue_item_id)
        self._catalogue_items_collection.update_one(
            {"_id": catalogue_item_id}, {"$set": catalogue_item.model_dump(by_alias=True)}
        )
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

        catalogue_items = self._catalogue_items_collection.find(query)
        return [CatalogueItemOut(**catalogue_item) for catalogue_item in catalogue_items]

    def has_child_elements(self, catalogue_item_id: CustomObjectId) -> bool:
        """
        Check if a catalogue item has child elements based on its ID.

        Child elements in this case means whether a catalogue item has child items

        :param catalogue_item_id: The ID of the catalogue item to check
        :return: True if the catalogue item has child elements, False otherwise.
        """
        logger.info("Checking if catalogue item with ID '%s' has child elements", catalogue_item_id)
        item = self._items_collection.find_one({"catalogue_item_id": catalogue_item_id})
        return item is not None
