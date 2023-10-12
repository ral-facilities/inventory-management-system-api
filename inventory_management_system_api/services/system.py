"""
Module for providing a service for managing Systems using the `SystemRepo` repository
"""

import logging
from typing import Optional

from fastapi import Depends

from inventory_management_system_api.models.system import SystemIn, SystemOut
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.schemas.system import SystemPostRequestSchema
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

    def create(self, system: SystemPostRequestSchema) -> SystemOut:
        """
        Create a new System

        :param system: System to be created
        :return: Created System
        """
        parent_id = system.parent_id
        parent_system = self.get(parent_id) if parent_id else None
        parent_path = parent_system.path if parent_system else "/"

        code = utils.generate_code(system.name, "system")
        path = utils.generate_path(parent_path, code, "system")
        return self._system_repository.create(
            SystemIn(
                name=system.name,
                location=system.location,
                owner=system.owner,
                importance=system.importance,
                description=system.description,
                code=code,
                path=path,
                parent_path=parent_path,
                parent_id=parent_id,
            )
        )

    def get(self, system_id: str) -> Optional[SystemOut]:
        """
        Retrieve a System by its ID

        :param system_id: ID of the System to retrieve
        :return: Retrieved System or `None` if not found
        """
        return self._system_repository.get(system_id)

    def list(self, path: Optional[str], parent_path: Optional[str]) -> list[SystemOut]:
        """
        Retrieve Systems based on the provided filters

        :param path: Path to filter Systems by
        :param parent_path: Parent path to filter Systems by
        :return: List of System's or an empty list if no Systems are retrieved
        """
        return self._system_repository.list(path, parent_path)
