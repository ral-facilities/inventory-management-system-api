"""
Module for providing a service for managing systems using the `SystemRepo` repository.
"""

from typing import Annotated, Optional

from fastapi import Depends

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import ChildElementsExistError, MissingRecordError
from inventory_management_system_api.core.object_storage_api_client import ObjectStorageAPIClient
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema
from inventory_management_system_api.services import utils


class SystemService:
    """
    Service for managing systems
    """

    def __init__(self, system_repository: Annotated[SystemRepo, Depends(SystemRepo)]) -> None:
        """
        Initialise the `SystemService` with a `SystemRepo` repository

        :param system_repository: `SystemRepo` repository to use
        """
        self._system_repository = system_repository

    def create(self, system: SystemPostSchema) -> SystemOut:
        """
        Create a new system

        :param system: System to be created
        :return: Created system
        """
        parent_id = system.parent_id

        code = utils.generate_code(system.name, "system")
        return self._system_repository.create(
            SystemIn(
                parent_id=parent_id,
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
        :return: The updated system
        """
        stored_system = self.get(system_id)
        if not stored_system:
            raise MissingRecordError(f"No system found with ID: {system_id}")

        update_data = system.model_dump(exclude_unset=True)

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
