"""
Module for providing a service for managing Systems using the `SystemRepo` repository
"""

import logging
from typing import Optional

from fastapi import Depends

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.system import SystemPatchSchema, SystemPostSchema
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class SystemService:
    """
    Service for managing Systems
    """

    def __init__(self, system_repository: SystemRepo = Depends(SystemRepo)) -> None:
        """
        Initialise the `SystemService` with a `SystemRepo` repository

        :param system_repository: `SystemRepo` repository to use
        """
        self._system_repository = system_repository

    def create(self, system: SystemPostSchema) -> SystemOut:
        """
        Create a new System

        :param system: System to be created
        :return: Created System
        """
        parent_id = system.parent_id

        code = utils.generate_code(system.name, "system")
        return self._system_repository.create(
            SystemIn(
                parent_id=parent_id,
                description=system.description,
                name=system.name,
                location=system.location,
                owner=system.owner,
                importance=system.importance,
                code=code,
            )
        )

    def get(self, system_id: str) -> Optional[SystemOut]:
        """
        Retrieve a System by its ID

        :param system_id: ID of the System to retrieve
        :return: Retrieved System or `None` if not found
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
        Retrieve Systems based on the provided filters

        :param parent_id: parent_id to filter Systems by
        :return: List of System's or an empty list if no Systems are retrieved
        """
        return self._system_repository.list(parent_id)

    def update(self, system_id: Optional[str], system: SystemPatchSchema) -> SystemOut:
        """
        Update a System by its ID

        :param system_id: ID of the System to updated
        :param system: System containing the fields to be updated
        :raises MissingRecordError: When the System with the given ID doesn't exist
        """
        stored_system = self.get(system_id)
        if not stored_system:
            raise MissingRecordError(f"No System found with ID: {system_id}")

        update_data = system.model_dump(exclude_unset=True)

        if "name" in update_data and system.name != stored_system.name:
            update_data["code"] = utils.generate_code(system.name, "system")

        return self._system_repository.update(system_id, SystemIn(**{**stored_system.model_dump(), **update_data}))

    def delete(self, system_id: str) -> None:
        """
        Delete a System by its ID

        :param system_id: ID of the System to delete
        """
        return self._system_repository.delete(system_id)
