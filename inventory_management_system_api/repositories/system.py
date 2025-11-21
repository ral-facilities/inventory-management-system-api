"""
Module for providing a repository for managing systems in a MongoDB database.
"""

import logging
from typing import Optional

from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.core.exceptions import DuplicateRecordError, InvalidActionError, MissingRecordError
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories import utils
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema

logger = logging.getLogger()


class SystemRepo:
    """
    Repository for managing systems in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialise the `SystemRepo` with a MongoDB database instance.

        :param database: Database to use.
        """
        self._database = database
        self._systems_collection: Collection = self._database.systems
        self._items_collection: Collection = self._database.items

    def create(self, system: SystemIn, session: Optional[ClientSession] = None) -> SystemOut:
        """
        Create a new system in a MongoDB database.

        If a parent system is specified by `parent_id`, it checks if that exists in the database and raises a
        `MissingRecordError` if it doesn't exist.

        :param system: System to be created.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Created system.
        :raises MissingRecordError: If the parent system specified by `parent_id` doesn't exist.
        :raises DuplicateRecordError: If a duplicate system is found within the parent system.
        """
        parent_id = str(system.parent_id) if system.parent_id else None
        if parent_id and not self.get(parent_id, session=session):
            raise MissingRecordError(f"No parent system found with ID '{parent_id}'")

        logger.info("Inserting the new system into the database")
        try:
            result = self._systems_collection.insert_one(system.model_dump(), session=session)
        except DuplicateKeyError as exc:
            raise DuplicateRecordError("Duplicate system found within the parent system") from exc

        return self.get(str(result.inserted_id), session=session)

    def get(self, system_id: str, session: Optional[ClientSession] = None) -> Optional[SystemOut]:
        """
        Retrieve a system by its ID from a MongoDB database.

        :param system_id: ID of the system to retrieve.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Retrieved system or `None` if not found.
        """
        system_id = CustomObjectId(system_id)
        logger.info("Retrieving system with ID '%s' from the database", system_id)
        system = self._systems_collection.find_one({"_id": system_id}, session=session)
        if system:
            return SystemOut(**system)
        return None

    def get_breadcrumbs(self, system_id: str, session: Optional[ClientSession] = None) -> BreadcrumbsGetSchema:
        """
        Retrieve the breadcrumbs for a specific system.

        :param system_id: ID of the system to retrieve breadcrumbs for.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Breadcrumbs.
        """
        logger.info("Querying breadcrumbs for system with id '%s'", system_id)
        return utils.compute_breadcrumbs(
            list(
                self._systems_collection.aggregate(
                    utils.create_breadcrumbs_aggregation_pipeline(entity_id=system_id, collection_name="systems"),
                    session=session,
                )
            ),
            entity_id=system_id,
            collection_name="systems",
        )

    def list(self, parent_id: Optional[str], session: Optional[ClientSession] = None) -> list[SystemOut]:
        """
        Retrieve systems from a MongoDB database based on the provided filters.

        :param parent_id: ID of the parent system to query by, or `None`.
        :param session: PyMongo ClientSession to use for database operations.
        :return: List of systems or an empty list if no systems are retrieved.
        """
        query = utils.list_query({"parent_id": parent_id}, "systems")

        systems = self._systems_collection.find(query, session=session)
        return [SystemOut(**system) for system in systems]

    def update(self, system_id: str, system: SystemIn, session: Optional[ClientSession] = None) -> SystemOut:
        """
        Update a system by its ID in a MongoDB database.

        :param system_id: ID of the system to update.
        :param system: System containing the update data.
        :param session: PyMongo ClientSession to use for database operations.
        :return: The updated system.
        :raises MissingRecordError: If the parent system specified by `parent_id` doesn't exist.
        :raises DuplicateRecordError: If a duplicate system is found within the parent system.
        :raises InvalidActionError: If attempting to change the `parent_id` to one of its own child system ids.
        """
        system_id = CustomObjectId(system_id)

        parent_id = str(system.parent_id) if system.parent_id else None
        if parent_id and not self.get(parent_id, session=session):
            raise MissingRecordError(f"No parent system found with ID '{parent_id}'")

        stored_system = self.get(str(system_id), session=session)
        moving_system = parent_id != stored_system.parent_id

        # Prevent a system from being moved to one of its own children
        if moving_system:
            if parent_id is not None and not utils.is_valid_move_result(
                list(
                    self._systems_collection.aggregate(
                        utils.create_move_check_aggregation_pipeline(
                            entity_id=str(system_id), destination_id=parent_id, collection_name="systems"
                        ),
                        session=session,
                    )
                )
            ):
                raise InvalidActionError("Cannot move a system to one of its own children")

        logger.info("Updating system with ID '%s' in the database", system_id)
        try:
            self._systems_collection.update_one({"_id": system_id}, {"$set": system.model_dump()}, session=session)
        except DuplicateKeyError as exc:
            raise DuplicateRecordError("Duplicate system found within the parent system") from exc

        return self.get(str(system_id), session=session)

    def delete(self, system_id: str, session: Optional[ClientSession] = None) -> None:
        """
        Delete a system by its ID from a MongoDB database.

        The method checks if the system has any child and raises a `ChildElementsExistError` if it does.

        :param system_id: ID of the system to delete.
        :param session: PyMongo ClientSession to use for database operations.
        :raises ChildElementsExistError: If the system has child elements.
        :raises MissingRecordError: If the system doesn't exist.
        """
        logger.info("Deleting system with ID '%s' from the database", system_id)
        result = self._systems_collection.delete_one({"_id": CustomObjectId(system_id)}, session=session)
        if result.deleted_count == 0:
            raise MissingRecordError(f"No system found with ID '{system_id}'")

    def has_child_elements(self, system_id: str, session: Optional[ClientSession] = None) -> bool:
        """
        Check if a system has any child system's or any Item's based on its ID.

        :param system_id: ID of the system to check.
        :param session: PyMongo ClientSession to use for database operations.
        :return: `True` if the system has child elements, `False` otherwise.
        """
        logger.info("Checking if system with ID '%s' has child elements", system_id)
        system_id = CustomObjectId(system_id)
        return (
            self._systems_collection.find_one({"parent_id": system_id}, session=session) is not None
            or self._items_collection.find_one({"system_id": system_id}, session=session) is not None
        )

    def write_lock(self, system_id: str, session: ClientSession) -> None:
        """Write locks a system document given its ID by setting a value in the document to itself.

        :param system_id: ID of the system document to write lock.
        :param session: PyMongo ClientSession to use for database operations.
        """
        logger.info("Write locking system with ID '%s'", system_id)
        system = self.get(system_id, session=session)
        self._systems_collection.update_one(
            {"_id": CustomObjectId(system_id)}, {"$set": {"importance": system.importance}}, session=session
        )
