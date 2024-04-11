"""
Module for providing a repository for managing Usage statuses in a MongoDB database
"""

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.usage_status import UsageStatusOut


class UsageStatusRepo:
    """
    Repository for managing Usage statuses in a MongoDB database
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialise the `UsageStatusRepo` with a MongoDB database instance

        :param database: Database to use
        """
        self._database = database
        self._usage_statuses_collection: Collection = self._database.usage_statuses

    def list(self) -> list[UsageStatusOut]:
        """
        Retrieve Usage statuses from a MongoDB database

        :return: List of Usage statuses or an empty list if no Usage statuses are retrieved
        """
        usage_statuses = self._usage_statuses_collection.find()
        return [UsageStatusOut(**usage_status) for usage_status in usage_statuses]
