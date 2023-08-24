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
from inventory_management_system_api.core.exceptions import DuplicateRecordError
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

        The method checks if a duplicate catalogue item is found within the catalogue category.

        :param catalogue_item: The catalogue item to be created.
        :return: The created catalogue item.
        :raises DuplicateRecordError: If a duplicate catalogue item is found within the catalogue category.
        """
        if self._is_duplicate_catalogue_item(str(catalogue_item.catalogue_category_id), catalogue_item.name):
            raise DuplicateRecordError("Duplicate catalogue item found within the catalogue category")

        logger.info("Inserting the new catalogue item into the database")
        result = self._collection.insert_one(catalogue_item.dict())
        catalogue_item = self.get(str(result.inserted_id))
        return catalogue_item

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

    def list(self, catalogue_category_id: str) -> List[CatalogueItemOut]:
        """
        Retrieve all catalogue items from a MongoDB.

        :param catalogue_category_id: The ID of the catalogue category to filter catalogue items by.
        :return: A list of catalogue items, or an empty list if no catalogue items are returned by the database.
        """

        catalogue_category_id = CustomObjectId(catalogue_category_id)
        query = {"catalogue_category_id": catalogue_category_id}
        logger.info("Retrieving catalogue items with Catalogue Category ID: %s", catalogue_category_id)

        catalogue_items = self._collection.find(query)
        return [CatalogueItemOut(**catalogue_item) for catalogue_item in catalogue_items]

    def _is_duplicate_catalogue_item(self, catalogue_category_id: str, name: str) -> bool:
        """
        Check if a catalogue item with the same name already exists within the catalogue category.

        :param catalogue_category_id: The ID of the catalogue category to check for duplicates in.
        :return: `True` if a duplicate catalogue item is found, `False` otherwise.
        """
        logger.info("Checking if catalogue item with name '%s' already exists within the category", name)
        catalogue_category_id = CustomObjectId(catalogue_category_id)
        count = self._collection.count_documents({"catalogue_category_id": catalogue_category_id, "name": name})
        return count > 0
