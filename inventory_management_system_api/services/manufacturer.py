"""
Module for providing a service for managing manufactuer using the `ManufacturerRepo` repository.
"""
import logging
import re

from fastapi import Depends
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut

from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.schemas.manufacturer import ManufacturerPostRequestSchema

logger = logging.getLogger()


class ManufacturerService:
    """Service for managing manufacturers"""

    def __init__(self, manufacturer_repository: ManufacturerRepo = Depends(ManufacturerRepo)) -> None:
        """
        Initialise the manufacturer service with a ManufacturerRepo

        :param manufacturer_repository: The `ManufacturerRepo` repository to use.
        """

        self._manufacturer_repository = manufacturer_repository

    def create(self, manufacturer: ManufacturerPostRequestSchema) -> ManufacturerOut:
        """Create a new manufacturer"""

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
