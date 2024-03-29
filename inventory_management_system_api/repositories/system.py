"""
Module for providing a repository for managing Systems in a MongoDB database
"""

import logging
from typing import Optional

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DuplicateRecordError,
    InvalidActionError,
    MissingRecordError,
)
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories import utils
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema

logger = logging.getLogger()


class SystemRepo:
    """
    Repository for managing Systems in a MongoDB database
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialise the `SystemRepo` with a MongoDB database instance

        :param database: Database to use
        """
        self._database = database
        self._systems_collection: Collection = self._database.systems
        self._items_collection: Collection = self._database.items

    def create(self, system: SystemIn) -> SystemOut:
        """
        Create a new System in a MongoDB database

        If a parent system is specified by `parent_id`, then checks if that exists in the database and raises a
        `MissingRecordError` if it doesn't exist. It also checks if a duplicate System is found within the parent
        System and raises a `DuplicateRecordError` if it is.

        :param system: System to be created
        :return: Created System
        :raises MissingRecordError: If the parent System specified by `parent_id` doesn't exist
        :raises DuplicateRecordError: If a duplicate System is found within the parent System
        """
        parent_id = str(system.parent_id) if system.parent_id else None
        if parent_id and not self.get(parent_id):
            raise MissingRecordError(f"No parent System found with ID: {parent_id}")

        if self._is_duplicate_system(parent_id, system.code):
            raise DuplicateRecordError("Duplicate System found within the parent System")

        logger.info("Inserting the new System into the database")
        result = self._systems_collection.insert_one(system.model_dump())
        system = self.get(str(result.inserted_id))
        return system

    def get(self, system_id: str) -> Optional[SystemOut]:
        """
        Retrieve a System by its ID from a MongoDB database

        :param system_id: ID of the System to retrieve
        :return: Retrieved System or `None` if not found
        """
        system_id = CustomObjectId(system_id)
        logger.info("Retrieving system with ID: %s from the database", system_id)
        system = self._systems_collection.find_one({"_id": system_id})
        if system:
            return SystemOut(**system)
        return None

    def get_breadcrumbs(self, system_id: str) -> BreadcrumbsGetSchema:
        """
        Retrieve the breadcrumbs for a specific system

        :param system_id: ID of the system to retrieve breadcrumbs for
        :return: Breadcrumbs
        """
        logger.info("Querying breadcrumbs for system with id '%s'", system_id)
        return utils.compute_breadcrumbs(
            list(
                self._systems_collection.aggregate(
                    utils.create_breadcrumbs_aggregation_pipeline(entity_id=system_id, collection_name="systems")
                )
            ),
            entity_id=system_id,
            collection_name="systems",
        )

    def list(self, parent_id: Optional[str]) -> list[SystemOut]:
        """
        Retrieve Systems from a MongoDB database based on the provided filters

        :param parent_id: parent_id to filter Systems by
        :return: List of Systems or an empty list if no Systems are retrieved
        """
        query = utils.list_query(parent_id, "systems")

        systems = self._systems_collection.find(query)
        return [SystemOut(**system) for system in systems]

    def update(self, system_id: str, system: SystemIn) -> SystemOut:
        """Update a system by its ID in a MongoDB database

        :param system_id: ID of the System to update
        :param system: System containing the update data
        :return: The updated System
        :raises MissingRecordError: If the parent System specified by `parent_id` doesn't exist
        :raises DuplicateRecordError: If a duplicate System is found within the parent System
        :raises InvalidActionError: If attempting to change the `parent_id` to one of its own child system ids
        """
        system_id = CustomObjectId(system_id)

        parent_id = str(system.parent_id) if system.parent_id else None
        if parent_id and not self.get(parent_id):
            raise MissingRecordError(f"No parent System found with ID: {parent_id}")

        stored_system = self.get(str(system_id))
        moving_system = parent_id != stored_system.parent_id
        if (system.name != stored_system.name or moving_system) and self._is_duplicate_system(parent_id, system.code):
            raise DuplicateRecordError("Duplicate System found within the parent System")

        # Prevent a system from being moved to one of its own children
        if moving_system:
            if parent_id is not None and not utils.is_valid_move_result(
                list(
                    self._systems_collection.aggregate(
                        utils.create_move_check_aggregation_pipeline(
                            entity_id=str(system_id), destination_id=parent_id, collection_name="systems"
                        )
                    )
                )
            ):
                raise InvalidActionError("Cannot move a system to one of its own children")

        logger.info("Updating system with ID: %s in the database", system_id)
        self._systems_collection.update_one({"_id": system_id}, {"$set": system.model_dump()})

        return self.get(str(system_id))

    def delete(self, system_id: str) -> None:
        """
        Delete a System by its ID from a MongoDB database

        The method checks if the system has any child and raises a `ChildElementsExistError` if it does

        :param system_id: ID of the System to delete
        :raises ChildElementsExistError: If the System has child elements
        :raises MissingRecordError: If the System doesn't exist
        """
        system_id = CustomObjectId(system_id)
        if self._has_child_elements(system_id):
            raise ChildElementsExistError(f"System with ID {str(system_id)} has child elements and cannot be deleted")

        logger.info("Deleting system with ID: %s from the database", system_id)
        result = self._systems_collection.delete_one({"_id": system_id})
        if result.deleted_count == 0:
            raise MissingRecordError(f"No System found with ID: {str(system_id)}")

    def _is_duplicate_system(self, parent_id: Optional[str], code: str) -> bool:
        """
        Check if a System with the same code already exists within the parent System

        :param parent_id: ID of the parent System which can also be `None`
        :param code: Code of the System to check for duplicates
        :return: `True` if a duplicate System code is found under the given parent, `False` otherwise
        """
        logger.info("Checking if System with code '%s' already exists within the parent System", code)
        if parent_id:
            parent_id = CustomObjectId(parent_id)

        return self._systems_collection.find_one({"parent_id": parent_id, "code": code}) is not None

    def _has_child_elements(self, system_id: CustomObjectId) -> bool:
        """
        Check if a System has any child System's or any Item's based on its ID

        :param system_id: ID of the System to check
        :return: True if the System has child elements, False otherwise
        """
        logger.info("Checking if system with ID '%s' has child elements", str(system_id))

        return (
            self._systems_collection.find_one({"parent_id": system_id}) is not None
            or self._items_collection.find_one({"system_id": system_id}) is not None
        )
