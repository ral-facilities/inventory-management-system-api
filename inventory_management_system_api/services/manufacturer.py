"""
Module for providing a service for managing manufactuer using the `ManufacturerRepo` repository.
"""
import logging

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

        return self._manufacturer_repository.create(
            ManufacturerIn(name=manufacturer.name, url=manufacturer.url, address=manufacturer.address)
        )
