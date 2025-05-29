"""
Module for providing a repository for managing Usage statuses in a MongoDB database
"""

import logging
from typing import Optional

from fastapi import status
from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.core.exceptions import DuplicateRecordError, MissingRecordError, PartOfItemError
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut

logger = logging.getLogger()


class UsageStatusRepo:
    """
    Repository for managing Usage statuses in a MongoDB database
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialise the `UsageStatusRepo` with a MongoDB database instance

        :param database: Database to use
        """
        self._database = database
        self._usage_statuses_collection: Collection = self._database.usage_statuses
        self._items_collection: Collection = self._database.items
        self._settings_collection: Collection = self._database.settings

    def create(self, usage_status: UsageStatusIn, session: Optional[ClientSession] = None) -> UsageStatusOut:
        """
        Create a new usage status in MongoDB database

        :param usage_status: The usage status to be created
        :param session: PyMongo ClientSession to use for database operations
        :return: The created usage status
        :raises DuplicateRecordError: If a duplicate usage status is found within collection
        """

        if self._is_duplicate_usage_status(usage_status.code, session=session):
            raise DuplicateRecordError(
                "Duplicate usage status found", response_detail="A usage status with the same value already exists"
            )

        logger.info("Inserting new usage status into database")

        result = self._usage_statuses_collection.insert_one(usage_status.model_dump(), session=session)
        usage_status = self.get(str(result.inserted_id), session=session)

        return usage_status

    def list(self, session: Optional[ClientSession] = None) -> list[UsageStatusOut]:
        """
        Retrieve Usage statuses from a MongoDB database

        :param session: PyMongo ClientSession to use for database operations
        :return: List of Usage statuses or an empty list if no Usage statuses are retrieved
        """
        usage_statuses = self._usage_statuses_collection.find(session=session)
        return [UsageStatusOut(**usage_status) for usage_status in usage_statuses]

    def get(
        self, usage_status_id: str, entity_type_modifier: Optional[str] = None, session: Optional[ClientSession] = None
    ) -> UsageStatusOut:
        """
        Retrieve a usage status by its ID from a MongoDB database.

        :param usage_status_id: The ID of the usage status to retrieve.
        :param entity_type_modifier: String value to put at the start of the entity type used in error messages
                                     e.g. parent if its for a parent system.
        :param session: PyMongo ClientSession to use for database operations
        :return: The retrieved usage status.
        :raises MissingRecordError: If the supplied `usage_status_id` is non-existent.
        """

        entity_type = f"{entity_type_modifier} usage status" if entity_type_modifier else "usage status"
        usage_status_id = CustomObjectId(
            usage_status_id, entity_type=entity_type, not_found_if_invalid=entity_type_modifier is None
        )

        logger.info("Retrieving usage status with ID: %s from the database", usage_status_id)
        usage_status = self._usage_statuses_collection.find_one({"_id": usage_status_id}, session=session)

        if usage_status:
            return UsageStatusOut(**usage_status)
        raise MissingRecordError(
            detail=f"No {entity_type} found with ID: {usage_status_id}",
            response_detail=f"{entity_type.capitalize()} not found",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY if entity_type_modifier is not None else None,
        )

    def delete(self, usage_status_id: str, session: Optional[ClientSession] = None) -> None:
        """
        Delete a usage status by its ID from a MongoDB database.

        Checks if usage status is a part of an item, and does not delete if it is

        :param usage_status_id: The ID of the usage status to delete
        :param session: PyMongo ClientSession to use for database operations
        :raises PartOfItemError: if usage status is a part of a catalogue item
        :raises MissingRecordError: if supplied usage status ID does not exist in the database
        """
        usage_status_id = CustomObjectId(usage_status_id, entity_type="usage status", not_found_if_invalid=True)
        if self._is_usage_status_in_item(usage_status_id, session=session):
            raise PartOfItemError(
                f"The usage status with ID {str(usage_status_id)} is a part of an Item",
                response_detail="The specified usage status is part of an Item",
            )

        logger.info("Deleting usage status with ID %s from the database", usage_status_id)
        result = self._usage_statuses_collection.delete_one({"_id": usage_status_id}, session=session)
        if result.deleted_count == 0:
            raise MissingRecordError(
                f"No usage status found with ID: {str(usage_status_id)}", response_detail="Usage status not found"
            )

    def _is_duplicate_usage_status(
        self, code: str, usage_status_id: Optional[CustomObjectId] = None, session: Optional[ClientSession] = None
    ) -> bool:
        """
        Check if usage status with the same name already exists in the usage statuses collection

        :param code: The code of the usage status to check for duplicates.
        :param usage_status_id: The ID of the usage status to check if the duplicate usage status found is itself.
        :param session: PyMongo ClientSession to use for database operations
        :return: `True` if a duplicate usage status code is found, `False` otherwise
        """
        logger.info("Checking if usage status with code '%s' already exists", code)
        usage_status = self._usage_statuses_collection.find_one(
            {"code": code, "_id": {"$ne": usage_status_id}}, session=session
        )
        return usage_status is not None

    def _is_usage_status_in_item(
        self, usage_status_id: CustomObjectId, session: Optional[ClientSession] = None
    ) -> bool:
        """Checks to see if any of the items in the database have a specific usage status ID.

        :param usage_status_id: The ID of the usage status that is looked for.
        :param session: PyMongo ClientSession to use for database operations.
        :return: `True` if 1 or more items have the usage status ID, `False` otherwise.
        """
        return self._items_collection.find_one({"usage_status_id": usage_status_id}, session=session) is not None
