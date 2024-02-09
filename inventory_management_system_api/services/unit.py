"""
Module for providing a service for managing Units using the `UnitRepo` repository
"""

from fastapi import Depends
from inventory_management_system_api.models.units import UnitOut
from inventory_management_system_api.repositories.unit import UnitRepo


class UnitService:
    """
    Service for managing Units
    """

    def __init__(self, unit_repository: UnitRepo = Depends(UnitRepo)) -> None:
        """
        Initialise the `UnitService` with a `UnitRepo` repository

        :param unit_repository: `UnitRepo` repository to use
        """
        self._unit_repository = unit_repository

    def list(self) -> list[UnitOut]:
        """
        Retrieve a list of all Units

        :return: List of Units or an empty list if no Units are retrieved
        """
        return self._unit_repository.list()
