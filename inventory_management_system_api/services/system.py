"""
Module for providing a service for managing systems using the `SystemRepo` repository.
"""

from typing import Annotated, Optional

from fastapi import Depends

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidActionError,
    MissingRecordError,
)
from inventory_management_system_api.core.object_storage_api_client import ObjectStorageAPIClient
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema
from inventory_management_system_api.services import utils


class SystemService:
    """
    Service for managing systems.
    """

    def __init__(
        self,
        system_repository: Annotated[SystemRepo, Depends(SystemRepo)],
        system_type_repository: Annotated[SystemTypeRepo, Depends(SystemTypeRepo)],
    ) -> None:
        """
        Initialise the `SystemService` with a `SystemRepo` repository.

        :param system_repository: `SystemRepo` repository to use.
        :param system_type_repository: `SystemTypeRepo` repository to use.
        """
        self._system_repository = system_repository
        self._system_type_repository = system_type_repository

    def create(self, system: SystemPostSchema) -> SystemOut:
        """
        Create a new system

        :param system: System to be created
        :return: Created system
        :raises MissingRecordError: If the system type specified by `type_id` doesn't exist.
        :raises MissingRecordError: If the parent system specified by `parent_id` doesn't exist.
        :raises InvalidActionError: If the system being created has a different `type_id` to its parent.
        """

        if not self._system_type_repository.get(system.type_id):
            raise MissingRecordError(f"No system type found with ID: {system.type_id}")

        # If there is a parent, must use the same type as it
        if system.parent_id is not None:
            parent_system = self._system_repository.get(system.parent_id)
            if not parent_system:
                raise MissingRecordError(f"No parent system found with ID: {system.parent_id}")
            if system.type_id != parent_system.type_id:
                raise InvalidActionError("Cannot use a different type_id to the parent system")

        # Create the system
        code = utils.generate_code(system.name, "system")
        return self._system_repository.create(
            SystemIn(
                parent_id=system.parent_id,
                name=system.name,
                type_id=system.type_id,
                description=system.description,
                location=system.location,
                owner=system.owner,
                importance=system.importance,
                code=code,
            )
        )

    def get(self, system_id: str) -> Optional[SystemOut]:
        """
        Retrieve a system by its ID

        :param system_id: ID of the system to retrieve
        :return: Retrieved system or `None` if not found
        """
        return self._system_repository.get(system_id)

    def get_breadcrumbs(self, system_id: str) -> BreadcrumbsGetSchema:
        """
        Retrieve the breadcrumbs for a specific system

        :param system_id: ID of the system to retrieve breadcrumbs for
        :return: Breadcrumbs
        """
        return self._system_repository.get_breadcrumbs(system_id)

    def list(self, parent_id: Optional[str]) -> list[SystemOut]:
        """
        Retrieve systems based on the provided filters

        :param parent_id: `parent_id` to filter systems by
        :return: List of systems or an empty list if no systems are retrieved
        """
        return self._system_repository.list(parent_id)

    def update(self, system_id: str, system: SystemPatchSchema) -> SystemOut:
        """
        Update a system by its ID

        :param system_id: ID of the system to updated
        :param system: System containing the fields to be updated
        :raises MissingRecordError: When the system with the given ID doesn't exist
        :raises MissingRecordError: If the parent system specified by `parent_id` doesn't exist.
        :raises MissingRecordError: If the system type specified by `type_id` doesn't exist.
        :raises InvalidActionError: When attempting to change the system type while the system has child elements.
        :raises InvalidActionError: When attempting to change the parent of the system to one with a different type
                                    without also changing the type to match.
        :return: The updated system
        """
        stored_system = self.get(system_id)
        if not stored_system:
            raise MissingRecordError(f"No system found with ID: {system_id}")

        update_data = system.model_dump(exclude_unset=True)

        self._validate_type_and_parent_update(system_id, system, stored_system, update_data)

        if "name" in update_data and system.name != stored_system.name:
            update_data["code"] = utils.generate_code(system.name, "system")

        return self._system_repository.update(system_id, SystemIn(**{**stored_system.model_dump(), **update_data}))

    def delete(self, system_id: str, access_token: Optional[str] = None) -> None:
        """
        Delete a system by its ID

        :param system_id: ID of the system to delete
        :param access_token: The JWT access token to use for auth with the Object Storage API if object storage enabled.
        """
        if self._system_repository.has_child_elements(system_id):
            raise ChildElementsExistError(f"System with ID {system_id} has child elements and cannot be deleted")

        # First, attempt to delete any attachments and/or images that might be associated with this system.
        if config.object_storage.enabled:
            ObjectStorageAPIClient.delete_attachments(system_id, access_token)
            ObjectStorageAPIClient.delete_images(system_id, access_token)

        self._system_repository.delete(system_id)

    def _validate_type_and_parent_update(
        self, system_id: str, system: SystemPatchSchema, stored_system: SystemOut, update_data: dict
    ) -> None:
        """
        Validate an update request that could modify the `type_id` or `parent_id` of the system.

        :param system_id: ID of the system to updated
        :param system: System containing the fields to be updated
        :param stored_system: Current stored system from the database.
        :param update_data: Dictionary containing the update data.
        :raises MissingRecordError: If the parent system specified by `parent_id` doesn't exist.
        :raises MissingRecordError: If the system type specified by `type_id` doesn't exist.
        :raises InvalidActionError: When attempting to change the system type while the system has child elements.
        :raises InvalidActionError: When attempting to change the parent of the system to one with a different type
                                    without also changing the type to match.
        """

        type_id_changing = "type_id" in update_data and system.type_id != stored_system.type_id
        parent_id_changing = "parent_id" in update_data and system.parent_id != stored_system.parent_id

        if type_id_changing or parent_id_changing:
            # Find the current/new type_id (For verifying with the parent at the end)
            type_id = stored_system.type_id
            if type_id_changing:
                # Type is being updated, so use the new value and ensure it is valid
                type_id = system.type_id

                if self._system_repository.has_child_elements(system_id):
                    raise InvalidActionError("Cannot change the type of a system when it has children")

                if not self._system_type_repository.get(type_id):
                    raise MissingRecordError(f"No system type found with ID: {type_id}")

            # Find the current/new parent (For verifying it with the type at the end)
            parent_system = None
            if parent_id_changing:
                # Parent is being updated, so use the new parent and ensure it is valid
                if system.parent_id is not None:
                    parent_system = self._system_repository.get(system.parent_id)
                    if not parent_system:
                        raise MissingRecordError(f"No parent system found with ID: {system.parent_id}")
            elif stored_system.parent_id is not None:
                # Parent is not being updated but are updating the type so obtain the current parent
                parent_system = self._system_repository.get(stored_system.parent_id)

            # If there is a new/current parent, ensure the new/current type_id is the same as it
            if parent_system is not None and type_id != parent_system.type_id:
                raise InvalidActionError(
                    "Cannot move a system into one with a different type"
                    if parent_id_changing
                    else "Cannot update the system's type to be different to its parent"
                )
