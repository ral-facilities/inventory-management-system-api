"""
Module for providing a repository for managing system types in a MongoDB database.
"""

import logging
from typing import Optional

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
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

    def list(self, session: Optional[ClientSession] = None) -> list[SystemTypeOut]:
        """
        Retrieve system types from a MongoDB database.

        :param session: PyMongo ClientSession to use for database operations.
        :return: List of system types or an empty list if no system types are retrieved.
        """
        logger.info("Retrieving all system types from the database")
        system_types = self._system_types_collection.find(session=session)
        return [SystemTypeOut(**system_type) for system_type in system_types]
