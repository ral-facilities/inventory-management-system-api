"""
Module for providing a repository for managing Usage statuses in a MongoDB database
"""

import logging
from typing import Optional

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import DuplicateRecordError
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut

logger = logging.getLogger()


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

    def create(self, usage_status: UsageStatusIn) -> UsageStatusOut:
        """
        Create a new usage status in MongoDB database

        :param usage_status: The usage status to be created
        :return: The created usage status
        :raises DuplicateRecordError: If a duplicate usage status is found within collection
        """

        if self._is_duplicate_usage_status(usage_status.code):
            raise DuplicateRecordError("Duplicate usage status found")

        logger.info("Inserting new usage status into database")

        result = self._usage_statuses_collection.insert_one(usage_status.model_dump())
        usage_status = self.get(str(result.inserted_id))

        return usage_status

    def list(self) -> list[UsageStatusOut]:
        """
        Retrieve Usage statuses from a MongoDB database

        :return: List of Usage statuses or an empty list if no Usage statuses are retrieved
        """
        usage_statuses = self._usage_statuses_collection.find()
        return [UsageStatusOut(**usage_status) for usage_status in usage_statuses]

    def get(self, usage_status_id: str) -> Optional[UsageStatusOut]:
        """
        Retrieve a usage status by its ID from a MongoDB database.

        :param usage_status_id: The ID of the usage status to retrieve.
        :return: The retrieved usage status, or `None` if not found.
        """
        usage_status_id = CustomObjectId(usage_status_id)
        logger.info(
            "Retrieving usage status with ID: %s from the database",
            usage_status_id,
        )
        usage_status = self._usage_statuses_collection.find_one({"_id": usage_status_id})
        if usage_status:
            return UsageStatusOut(**usage_status)
        return None

    def _is_duplicate_usage_status(self, code: str) -> bool:
        """
        Check if usage status with the same name already exists in the usage statuses collection

        :param code: The code of the usage status to check for duplicates.
        :return `True` if duplicate usage status, `False` otherwise
        """
        logger.info("Checking if usage status with code '%s' already exists", code)
        return self._usage_statuses_collection.find_one({"code": code}) is not None
