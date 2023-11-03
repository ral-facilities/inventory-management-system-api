"""
Module for providing a repository for managing manufacturers in a MongoDB database.
"""
import logging
from typing import Optional, List

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    MissingRecordError,
    PartOfCatalogueItemError,
)

from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut

logger = logging.getLogger()


class ManufacturerRepo:
    """Repository for managing manufacturer in MongoDb database"""

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """Initialize the `ManufacturerRepo` with MongoDB database instance

        :param database: The database to use.
        """

        self._database = database
        self._manufacturers_collection: Collection = self._database.manufacturers
        self._catalogue_item_collection: Collection = self._database.catalogue_items

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

        result = self._manufacturers_collection.insert_one(manufacturer.model_dump())
        manufacturer = self.get(str(result.inserted_id))

        return manufacturer

    def get(self, manufacturer_id: str) -> Optional[ManufacturerOut]:
        """Retrieve a manufacturer from database by its id


        :param manufacturer_id: The ID of the manufacturer
        :return: The retrieved manufacturer, or `None` if not found
        """

        manufacturer_id = CustomObjectId(manufacturer_id)

        logger.info("Retrieving manufacturer with ID %s from database", manufacturer_id)
        manufacturer = self._manufacturers_collection.find_one({"_id": manufacturer_id})
        if manufacturer:
            return ManufacturerOut(**manufacturer)
        return None

    def list(self) -> List[ManufacturerOut]:
        """Get all manufacturers from database

        :return: List of manufacturers, or empty list if no manufacturers
        """

        logger.info("Getting all manufacturers from database")

        manufacturers = self._manufacturers_collection.find()

        return [ManufacturerOut(**manufacturer) for manufacturer in manufacturers]

    def update(self, manufacturer_id: str, manufacturer: ManufacturerIn) -> ManufacturerOut:
        """Update manufacturer by its ID in database

        :param: manufacturer_id: The id of the manufacturer to be updated
        :param: manufacturer: The manufacturer with the update data

        :raises: DuplicateRecordError: if changed manufacturer name is a duplicate name

        :returns: the updated manufacturer
        """
        manufacturer_id = CustomObjectId(manufacturer_id)

        stored_manufacturer = self.get(str(manufacturer_id))
        if stored_manufacturer.name != manufacturer.name:
            if self._is_duplicate_manufacturer(manufacturer.code):
                raise DuplicateRecordError("Duplicate manufacturer found")

        logger.info("Updating manufacturer with ID %s", manufacturer_id)
        self._manufacturers_collection.update_one({"_id": manufacturer_id}, {"$set": manufacturer.model_dump()})

        manufacturer = self.get(str(manufacturer_id))
        return manufacturer

    def delete(self, manufacturer_id: str) -> None:
        """
        Delete a manufacturer by its ID from MongoDB database.
        Checks if manufactuer is a part of an item, and does not delete if it is

        :param manufacturer_id: The ID of the manufacturer to delete
        :raises PartOfCatalogueItemError: if manufacturer is a part of a catalogue item
        :raises MissingRecordError: if supplied manufacturer ID does not exist in the database
        """
        manufacturer_id = CustomObjectId(manufacturer_id)
        if self._is_manufacturer_in_catalogue_item(str(manufacturer_id)):
            raise PartOfCatalogueItemError(
                f"The manufacturer with id {str(manufacturer_id)} is a part of a Catalogue Item"
            )

        logger.info("Deleting manufacturer with ID %s from the database", manufacturer_id)
        result = self._manufacturers_collection.delete_one({"_id": manufacturer_id})
        if result.deleted_count == 0:
            raise MissingRecordError(f"No manufacturer found with ID: {str(manufacturer_id)}")

    def _is_duplicate_manufacturer(self, code: str) -> bool:
        """
        Check if manufacturer with the same name already exists in the manufacturer collection

        :param code: The code of the manufacturer to check for duplicates.
        :return `True` if duplicate manufacturer, `False` otherwise
        """
        logger.info("Checking if manufacturer with code '%s' already exists", code)
        count = self._manufacturers_collection.count_documents({"code": code})
        return count > 0

    def _is_manufacturer_in_catalogue_item(self, manufacturer_id: str) -> bool:
        """Checks to see if any of the documents in the database have a specific manufactuer id

        :param manufacturer_id: The ID of the manufacturer that is looked for
        :return: Returns True if 1 or more documents have the manufacturer ID, false if none do
        """
        manufacturer_id = CustomObjectId(manufacturer_id)
        count = self._catalogue_item_collection.count_documents({"manufacturer_id": manufacturer_id})
        return count > 0
