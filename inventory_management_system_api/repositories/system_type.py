"""
Module for providing a repository for managing system types in a MongoDB database.
"""

import logging
from typing import Optional

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.system_type import SystemTypeOut

logger = logging.getLogger()


class SystemTypeRepo:
    """
    Repository for managing system types in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialise the `SystemTypeRepo` with a MongoDB database instance.

        :param database: Database to use.
        """
        self._database = database
        self._system_types_collection: Collection = self._database.system_types

    def get(self, system_type_id: str, session: Optional[ClientSession] = None) -> Optional[SystemTypeOut]:
        """
        Retrieve a system type by its ID from a MongoDB database.

        :param system_type_id: ID of the system type to retrieve.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Retrieved system type or None if not found.
        :raises MissingRecordError: If the supplied `system_type_id` is non-existent.
        """
        system_type_id = CustomObjectId(system_type_id)

        logger.info("Retrieving system type with ID: %s from the database", system_type_id)
        system_type = self._system_types_collection.find_one({"_id": system_type_id}, session=session)

        if system_type:
            return SystemTypeOut(**system_type)
        return None

    def list(self, session: Optional[ClientSession] = None) -> list[SystemTypeOut]:
        """
        Retrieve system types from a MongoDB database.

        :param session: PyMongo ClientSession to use for database operations.
        :return: List of system types or an empty list if no system types are retrieved.
        """
        logger.info("Retrieving all system types from the database")
        system_types = self._system_types_collection.find(session=session)
        return [SystemTypeOut(**system_type) for system_type in system_types]
