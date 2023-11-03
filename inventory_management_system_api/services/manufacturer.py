"""
Module for providing a service for managing manufacturers using the `ManufacturerRepo` repository.
"""
import logging

from typing import List, Optional
from fastapi import Depends
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.schemas.manufacturer import (
    ManufacturerPatchRequestSchema,
    ManufacturerPostRequestSchema,
)
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class ManufacturerService:
    """Service for managing manufacturers"""

    def __init__(
        self,
        manufacturer_repository: ManufacturerRepo = Depends(ManufacturerRepo),
    ) -> None:
        """
        Initialise the manufacturer service with a ManufacturerRepo

        :param manufacturer_repository: The `ManufacturerRepo` repository to use.
        """

        self._manufacturer_repository = manufacturer_repository

    def create(self, manufacturer: ManufacturerPostRequestSchema) -> ManufacturerOut:
        """
        Create a new manufacturer.
        :param manufacturer: The manufacturer to be created.
        :return: The created manufacturer.
        """
        code = utils.generate_code(manufacturer.name, "manufacturer")
        return self._manufacturer_repository.create(
            ManufacturerIn(
                name=manufacturer.name,
                code=code,
                url=manufacturer.url,
                address=manufacturer.address,
                telephone=manufacturer.telephone,
            )
        )

    def get(self, manufacturer_id: str) -> Optional[ManufacturerOut]:
        """
        Get manufacturer by its ID.

        :param: manufacturer_id: The ID of the requested manufacturer
        :return: The retrieved manufacturer, or None if not found
        """
        return self._manufacturer_repository.get(manufacturer_id)

    def list(self) -> List[ManufacturerOut]:
        """Get all manufactuers

        :return: list of all manufacturers
        """
        return self._manufacturer_repository.list()

    def update(self, manufacturer_id: str, manufacturer: ManufacturerPatchRequestSchema) -> ManufacturerOut:
        """Update a manufacturer by its ID


        :params: manufacturer_id: The ID of the manufacturer to be updated
        :return: The updated manufacturer
        :raises MissingRecordError: If manufacturer does not exist in database
        """
        update_data = manufacturer.model_dump(exclude_unset=True)

        stored_manufacturer = self.get(manufacturer_id)
        if not stored_manufacturer:
            raise MissingRecordError(f"No manufacturer found with ID {manufacturer_id}")

        if "name" in update_data and update_data["name"] != stored_manufacturer.name:
            update_data["code"] = utils.generate_code(manufacturer.name, "manufacturer")

        stored_manufacturer = stored_manufacturer.copy(
            update={**update_data, "address": stored_manufacturer.address.copy(update=update_data.get("address"))}
        )

        return self._manufacturer_repository.update(manufacturer_id, ManufacturerIn(**stored_manufacturer.model_dump()))

    def delete(self, manufacturer_id: str) -> None:
        """
        Delete a manufacturer by its ID

        :param manufacturer_id: The ID of the manufacturer to delete

        """
        return self._manufacturer_repository.delete(manufacturer_id)
