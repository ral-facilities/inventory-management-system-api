"""
Module for providing a repository for managing catalogue categories in a MongoDB database.
"""
import logging

from bson import ObjectId
from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import MissingRecordError, DuplicateRecordError
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
    ObjectIdField,
)

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
        :raises DuplicateRecordError: If a duplicate catalogue category is found within the parent catalogue category.
        """
        logger.info("Inserting the new catalogue category into the database")
        parent_id = catalogue_category.parent_id
        if parent_id and not self._collection.find_one({"_id": parent_id}):
            raise MissingRecordError(f"No catalogue category found with id: {parent_id}")

        if self._is_duplicate_catalogue_category(parent_id, catalogue_category.code):
            raise DuplicateRecordError("Duplicate catalogue category found within the parent catalogue category")

        result = self._collection.insert_one(catalogue_category.dict())
        catalogue_category = self._collection.find_one({"_id": ObjectId(result.inserted_id)})
        return CatalogueCategoryOut(**catalogue_category)

    def _is_duplicate_catalogue_category(self, parent_id: ObjectIdField | None, code: str) -> bool:
        """
        Check if a catalogue category with the same code already exists within the parent category.

        :param parent_id: The ID of the parent catalogue category.
        :param code: The code of the catalogue category to check for duplicates.
        :return: `True` if a duplicate catalogue category code is found, `False` otherwise.
        """
        count = self._collection.count_documents({"parent_id": parent_id, "code": code})
        return count > 0
