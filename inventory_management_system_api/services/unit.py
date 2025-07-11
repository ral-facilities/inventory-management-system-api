"""
Module for providing a service for managing Units using the `UnitRepo` repository
"""

from typing import Annotated

from fastapi import Depends, status

from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.unit import UnitIn, UnitOut
from inventory_management_system_api.repositories.unit import UnitRepo
from inventory_management_system_api.schemas.unit import UnitPostSchema
from inventory_management_system_api.services import utils


class UnitService:
    """
    Service for managing Units
    """

    def __init__(self, unit_repository: Annotated[UnitRepo, Depends(UnitRepo)]) -> None:
        """
        Initialise the `UnitService` with a `UnitRepo` repository

        :param unit_repository: `UnitRepo` repository to use
        """
        self._unit_repository = unit_repository

    def create(self, unit: UnitPostSchema) -> UnitOut:
        """
        Create a new Unit.

        :param unit: The unit to be created.
        :return: The created unit.
        """
        code = utils.generate_code(unit.value, "unit")
        return self._unit_repository.create(UnitIn(**unit.model_dump(), code=code))

    def get(self, unit_id: str) -> UnitOut:
        """
        Get Unit by its ID.

        :param unit_id: The ID of the requested unit.
        :return: The retrieved unit.
        :raises MissingRecordError: If the supplied `unit_id` is non-existent.
        :raises InvalidObjectIdError: If the supplied `unit_id` is invalid.
        """
        try:
            return self._unit_repository.get(unit_id)
        except (MissingRecordError, InvalidObjectIdError) as exc:
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.response_detail = "Unit not found"
            raise exc

    def list(self) -> list[UnitOut]:
        """
        Retrieve a list of all Units

        :return: List of Units or an empty list if no Units are retrieved
        """
        return self._unit_repository.list()

    def delete(self, unit_id: str) -> None:
        """
        Delete a unit by its ID

        :param unit_id: The ID of the unit to delete
        :raises MissingRecordError: If the supplied `unit_id` is non-existent.
        :raises InvalidObjectIdError: If the supplied `unit_id` is invalid.
        """
        try:
            return self._unit_repository.delete(unit_id)
        except (MissingRecordError, InvalidObjectIdError) as exc:
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.response_detail = "Unit not found"
            raise exc
