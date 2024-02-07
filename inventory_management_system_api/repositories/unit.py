"""
Module for providing a repository for managing Units in a MongoDB database
"""

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.units import UnitOut


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

    def list(self) -> list[UnitOut]:
        """
        Retrieve Units from a MongoDB database

        :return: List of Units or an empty list if no Units are retrieved
        """
        units = self._units_collection.find({})
        return [UnitOut(**unit) for unit in units]
