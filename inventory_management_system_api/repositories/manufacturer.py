"""
Module for providing a repository for managing catalogue categories in a MongoDB database.
"""
import logging
from typing import Optional, List

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    DuplicateRecordError,
    ChildrenElementsExistError,
)
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut

logger = logging.getLogger()


class ManufacturerRepo:
    """Repository for managing manufacurer in MongoDb database"""

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """Initialize the ManufacturerRepo with MongoDB database instance"""

        self._database = database
        self._collection: Collection = self._database.manufacturer

    def create(self, manufacturer: ManufacturerIn) -> ManufacturerOut:
        """Create a new manufacturer in MongoDB database"""

        if self._is_duplicate_manufacturer(manufacturer.url):
            raise DuplicateRecordError("Duplicate manufacturer found")

        logger.info("Inserting new manufacturer into database")

        result = self._collection.insert_one(manufacturer.dict())
        manufacturer = self.get(str(result.inserted_id))

        return manufacturer

    def get(self, manufacturer_id: str) -> Optional[ManufacturerOut]:
        """Retrieve a manufacturer from database by its id"""

        manufacturer_id = CustomObjectId(manufacturer_id)
        print(manufacturer_id)
        logger.info("Retrieving manufacturer with ID %s from database", manufacturer_id)
        manufacturer = self._collection.find_one({"_id": manufacturer_id})
        if manufacturer:
            return ManufacturerOut(**manufacturer)
        return None

    def _is_duplicate_manufacturer(self, url: str) -> bool:
        """
        Check if manufacturer with the same url already exists in the manufacturer collection

        :param url: the url of the manufacturer to check for duplicates
        """
        logger.info("Checking for duplicates")
        count = self._collection.count_documents({"url": url})
        return count > 0
