"""
Module for providing a service for managing manufacturers using the `ManufacturerRepo` repository.
"""
import logging
import re

from typing import List, Optional
from fastapi import Depends
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.schemas.manufacturer import (
    ManufacturerPatchRequstSchema,
    ManufacturerPostRequestSchema,
)

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
        code = self._generate_code(manufacturer.name)
        return self._manufacturer_repository.create(
            ManufacturerIn(name=manufacturer.name, code=code, url=manufacturer.url, address=manufacturer.address)
        )

    def _generate_code(self, name: str) -> str:
        """
        Generate code for manufacturer based on its name, used to check for duplicate manufacturers

        The code is generated by changing name to lowercase and replacing spaces hypens,
        and removing trailing/preceding spaces

        :param name: The name of the manufacturer
        :return: The generated code for the manufacturer
        """
        name = name.lower().strip()
        return re.sub(r"\s", "-", name)

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

    def update(self, manufacturer_id: str, manufacturer: ManufacturerPatchRequstSchema) -> ManufacturerOut:
        """Update a category by its ID


        :params: manufactuer_id: The ID of the manufacturer to be updates
        :return: The updates manufacturer
        :raises MissingRecordError: If manufacturer does not exist in database
        """
        updated_data = manufacturer.model_dump()

        stored_manufacturer = self.get(manufacturer_id)
        if not stored_manufacturer:
            raise MissingRecordError(f"No manufacturer found with ID {manufacturer_id}")

        stored_manufacturer.name = updated_data["name"]
        stored_manufacturer.code = self._generate_code(stored_manufacturer.name)
        stored_manufacturer.url = updated_data["url"]
        stored_manufacturer.address = updated_data["address"]

        logger.info(stored_manufacturer.address)
        return self._manufacturer_repository.update(manufacturer_id, ManufacturerIn(**stored_manufacturer.model_dump()))

    def delete(self, manufacturer_id: str) -> None:
        """
        Delete a manufacturer by its ID

        :param manufacturer_id: The ID of the manufacturer to delete

        """
        return self._manufacturer_repository.delete(manufacturer_id)
