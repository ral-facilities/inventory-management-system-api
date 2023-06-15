"""
Module for providing a repository for managing catalogue categories in a MongoDB database.
"""
import logging

from bson import ObjectId
from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut

logger = logging.getLogger()


class CatalogueCategoryRepo:
    """
    Repository for managing catalogue categories in a MongoDB database.
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialize the `CatalogueCategoryRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._collection: Collection = self._database.catalogue_categories

    def create(self, catalogue_category: CatalogueCategoryIn) -> CatalogueCategoryOut:
        """
        Create a new catalogue category in a MongoDB database.

        If a parent catalogue category is specified by `parent_id`, the method checks if that exists
        in the database and raises a `MissingRecordError` if it doesn't exist.

        :param catalogue_category: The catalogue category to be created.
        :return: The created catalogue category.
        :raises MissingRecordError: If the parent catalogue category specified by `parent_id` doesn't exist.
        """
        logger.info("Inserting the new catalogue category into the database")
        parent_id = catalogue_category.parent_id
        if parent_id and not self._collection.find_one({"_id": parent_id}):
            raise MissingRecordError(f"No catalogue category found with id: {parent_id}")

        result = self._collection.insert_one(catalogue_category.dict())
        catalogue_category = self._collection.find_one({"_id": ObjectId(result.inserted_id)})
        catalogue_category["id"] = catalogue_category.pop("_id")
        return CatalogueCategoryOut(**catalogue_category)
