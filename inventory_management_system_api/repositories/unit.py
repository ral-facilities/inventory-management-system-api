"""
Module for providing a repository for managing Units in a MongoDB database
"""

import logging
from typing import Optional

from fastapi import Depends
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    MissingRecordError,
    PartOfCatalogueCategoryError,
)
from inventory_management_system_api.models.unit import UnitIn, UnitOut

logger = logging.getLogger()


class UnitRepo:
    """
    Repository for managing Units in a MongoDB database
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialise the `UnitRepo` with a MongoDB database instance
        :param database: Database to use
        """
        self._database = database
        self._units_collection: Collection = self._database.units
        self._catalogue_categories_collection: Collection = self._database.catalogue_categories

    def create(self, unit: UnitIn, session: ClientSession = None) -> UnitOut:
        """
        Create a new Unit in a MongoDB database

        :param unit: The unit to be created
        :param session: PyMongo ClientSession to use for database operations
        :return: The created unit
        :raises DuplicateRecordError: If a duplicate unit is found within the collection
        """

        if self._is_duplicate_unit(unit.code, session=session):
            raise DuplicateRecordError("Duplicate unit found")

        logger.info("Inserting new unit into database")

        result = self._units_collection.insert_one(unit.model_dump(), session=session)
        unit = self.get(str(result.inserted_id), session=session)

        return unit

    def list(self, session: ClientSession = None) -> list[UnitOut]:
        """
        Retrieve Units from a MongoDB database

        :param session: PyMongo ClientSession to use for database operations
        :return: List of Units or an empty list if no units are retrieved
        """
        units = self._units_collection.find(session=session)
        return [UnitOut(**unit) for unit in units]

    def get(self, unit_id: str, session: ClientSession = None) -> Optional[UnitOut]:
        """
        Retrieve a Unit by its ID from a MongoDB database.

        :param unit_id: The ID of the unit to retrieve.
        :param session: PyMongo ClientSession to use for database operations
        :return: The retrieved unit, or `None` if not found.
        """
        unit_id = CustomObjectId(unit_id)
        logger.info("Retrieving unit with ID: %s from the database", unit_id)
        unit = self._units_collection.find_one({"_id": unit_id}, session=session)
        if unit:
            return UnitOut(**unit)
        return None

    def delete(self, unit_id: str, session: ClientSession = None) -> None:
        """
        Delete a unit by its ID from MongoDB database.

        Checks if unit is a part of a catalogue category, and does not delete if it is

        :param unit_id: The ID of the unit to delete
        :param session: PyMongo ClientSession to use for database operations
        :raises PartOfCatalogueCategoryError: if unit is part of a catalogue category
        :raises MissingRecordError: if supplied unit ID does not exist in the database
        """
        unit_id = CustomObjectId(unit_id)
        if self._is_unit_in_catalogue_category(str(unit_id), session=session):
            raise PartOfCatalogueCategoryError(f"The unit with ID {str(unit_id)} is a part of a Catalogue category")

        logger.info("Deleting unit with ID %s from the database", unit_id)
        result = self._units_collection.delete_one({"_id": unit_id}, session=session)
        if result.deleted_count == 0:
            raise MissingRecordError(f"No unit found with ID: {str(unit_id)}")

    def _is_duplicate_unit(self, code: str, session: ClientSession = None) -> bool:
        """
        Check if a Unit with the same value already exists in the Units collection

        :param code: The code of the unit to check for duplicates.
        :param session: PyMongo ClientSession to use for database operations
        :return: `True` if a duplicate unit code is found, `False` otherwise
        """
        logger.info("Checking if unit with code '%s' already exists", code)
        return self._units_collection.find_one({"code": code}, session=session) is not None

    def _is_unit_in_catalogue_category(self, unit_id: str, session: ClientSession = None) -> bool:
        """
        Checks if any catalogue categories in the database have a specific unit ID

        :param unit_id: The ID of the unit being looked for
        :param session: PyMongo ClientSession to use for database operations
        :return: `True` if 1 or more catalogue categories have the unit ID, `False` otherwise
        """
        unit_id = CustomObjectId(unit_id)

        # Query for documents where 'unit_id' exists in the nested 'catalogue_item_properties' list
        query = {"catalogue_item_properties.unit_id": unit_id}

        return self._catalogue_categories_collection.find_one(query, session=session) is not None
