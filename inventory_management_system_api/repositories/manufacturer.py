"""
Module for providing a repository for managing manufacturers in a MongoDB database.
"""
import logging
from typing import Optional

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import DuplicateRecordError

from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut

logger = logging.getLogger()


class ManufacturerRepo:
    """Repository for managing manufacturer in MongoDb database"""

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """Initialize the `ManufacturerRepo` with MongoDB database instance

        :param database: The database to use.
        """

        self._database = database
        self._collection: Collection = self._database.manufacturer

    def create(self, manufacturer: ManufacturerIn) -> ManufacturerOut:
        """
        Create a new manufacturer in MongoDB database

        :param manufacturer: The manufacturer to be created
        :return: The created manufacturer
        :raises DuplicateRecordError: If a duplicate manufacturer is found within collection
        """

        if self._is_duplicate_manufacturer(manufacturer.code):
            raise DuplicateRecordError("Duplicate manufacturer found")

        logger.info("Inserting new manufacturer into database")

        result = self._collection.insert_one(manufacturer.dict())
        manufacturer = self.get(str(result.inserted_id))

        return manufacturer

    def get(self, manufacturer_id: str) -> Optional[ManufacturerOut]:
        """Retrieve a manufacturer from database by its id


        :param manufacturer_id: The ID of the manufacturer
        :return: The retrieved manufacturer, or `None` if not found
        """

        manufacturer_id = CustomObjectId(manufacturer_id)

        logger.info("Retrieving manufacturer with ID %s from database", manufacturer_id)
        manufacturer = self._collection.find_one({"_id": manufacturer_id})
        if manufacturer:
            return ManufacturerOut(**manufacturer)
        return None

    def _is_duplicate_manufacturer(self, code: str) -> bool:
        """
        Check if manufacturer with the same url already exists in the manufacturer collection

        :param code: The code of the manufacturer to check for duplicates.
        :return `True` if duplicate manufacturer, `False` otherwise
        """
        logger.info("Checking if manufacturer with code '%s' already exists", code)
        count = self._collection.count_documents({"code": code})
        return count > 0
