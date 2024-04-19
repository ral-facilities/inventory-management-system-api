"""
Module for providing a service for managing Units using the `UnitRepo` repository
"""

from typing import Optional
from fastapi import Depends
from inventory_management_system_api.models.units import UnitIn, UnitOut
from inventory_management_system_api.repositories.unit import UnitRepo
from inventory_management_system_api.schemas.unit import UnitPostRequestSchema

from inventory_management_system_api.services import utils


class UnitService:
    """
    Service for managing units
    """

    def __init__(self, unit_repository: UnitRepo = Depends(UnitRepo)) -> None:
        """
        Initialise the `UnitService` with a `UnitRepo` repository
        :param unit_repository: `UnitRepo` repository to use
        """
        self._unit_repository = unit_repository

    def create(self, unit: UnitPostRequestSchema) -> UnitOut:
        """
        Create a new unit.
        :param  unit: The unit to be created.
        :return: The created unit.
        """
        code = utils.generate_code(unit.value, "unit")
        return self._unit_repository.create(UnitIn(**unit.model_dump(), code=code))

    def get(self, unit_id: str) -> Optional[UnitOut]:
        """
        Get unit by its ID.
        :param: unit_id: The ID of the requested unit
        :return: The retrieved unit, or None if not found
        """
        return self._unit_repository.get(unit_id)

    def list(self) -> list[UnitOut]:
        """
        Retrieve a list of all units
        :return: List of units or an empty list if no units are retrieved
        """
        return self._unit_repository.list()
