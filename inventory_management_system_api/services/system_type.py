"""
Module for providing a service for managing systems using the `SystemRepo` repository.
"""

from typing import Annotated

from fastapi import Depends

from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.repositories.system_type import SystemTypeRepo


class SystemTypeService:
    """
    Service for managing system types.
    """

    def __init__(self, system_type_repository: Annotated[SystemTypeRepo, Depends(SystemTypeRepo)]) -> None:
        """
        Initialise the `SystemTypeService` with a `SystemTypeRepo` repository.

        :param system_type_repository: `SystemTypeRepo` repository to use.
        """
        self._system_type_repository = system_type_repository

    def list(self) -> list[SystemTypeOut]:
        """
        Retrieve system types.

        :return: List of system types or an empty list if no system types are retrieved.
        """
        return self._system_type_repository.list()
