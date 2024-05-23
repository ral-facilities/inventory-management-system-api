"""
Module for providing a service for managing Units using the `UnitRepo` repository
"""

from typing import Optional
from fastapi import Depends
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.repositories.unit import UnitRepo
from inventory_management_system_api.schemas.unit import UnitPostRequestSchema

from inventory_management_system_api.services import utils


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

    def create(self, unit: UnitPostRequestSchema) -> UnitOut:
        """
        Create a new Unit.

        :param unit: The unit to be created.
        :return: The created unit.
        """
        code = utils.generate_code(unit.value, "unit")
        return self._unit_repository.create(UnitIn(**unit.model_dump(), code=code))

    def get(self, unit_id: str) -> Optional[UnitOut]:
        """
        Get Unit by its ID.

        :param unit_id: The ID of the requested unit
        :return: The retrieved unit, or None if not found
        """
        return self._unit_repository.get(unit_id)

    def list(self) -> list[UnitOut]:
        """
        Retrieve a list of all Units

        :return: List of Units or an empty list if no Units are retrieved
        """
        return self._unit_repository.list()

    def delete(self, unit_id: str) -> None:
        """
        Delete a unit by its ID
        :param usage_status_id: The ID of the unit to delete
        """
        return self._unit_repository.delete(unit_id)
