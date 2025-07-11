"""
Module for providing a service for managing manufacturers using the `ManufacturerRepo` repository.
"""

import logging
from typing import Annotated, List

from fastapi import Depends, status

from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.schemas.manufacturer import ManufacturerPatchSchema, ManufacturerPostSchema
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class ManufacturerService:
    """Service for managing manufacturers."""

    def __init__(
        self,
        manufacturer_repository: Annotated[ManufacturerRepo, Depends(ManufacturerRepo)],
    ) -> None:
        """
        Initialise the `ManufacturerService` with a `ManufacturerRepo` repository.

        :param manufacturer_repository: The `ManufacturerRepo` repository to use.
        """
        self._manufacturer_repository = manufacturer_repository

    def create(self, manufacturer: ManufacturerPostSchema) -> ManufacturerOut:
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

    def get(self, manufacturer_id: str) -> ManufacturerOut:
        """
        Retrieve a manufacturer by its ID.

        :param manufacturer_id: The ID of the manufacturer to retrieve.
        :return: The retrieved manufacturer.
        """
        try:
            return self._manufacturer_repository.get(manufacturer_id)
        except (MissingRecordError, InvalidObjectIdError) as exc:
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.response_detail = "Manufacturer not found"
            raise exc

    def list(self) -> List[ManufacturerOut]:
        """
        Retrieve all manufacturers.

        :return: List of manufacturers, or empty list if no manufacturers.
        """
        return self._manufacturer_repository.list()

    def update(self, manufacturer_id: str, manufacturer: ManufacturerPatchSchema) -> ManufacturerOut:
        """
        Update a manufacturer by its ID.

        :params: manufacturer_id: The ID of the manufacturer to be updated.
        :raises MissingRecordError: If the manufacturer with the given ID does not exist.
        :return: The updated manufacturer.
        """
        stored_manufacturer = self.get(manufacturer_id)

        update_data = manufacturer.model_dump(exclude_unset=True)

        if "name" in update_data and manufacturer.name != stored_manufacturer.name:
            update_data["code"] = utils.generate_code(manufacturer.name, "manufacturer")

        stored_manufacturer = stored_manufacturer.model_copy(
            update={**update_data, "address": stored_manufacturer.address.model_copy(update=update_data.get("address"))}
        )

        return self._manufacturer_repository.update(manufacturer_id, ManufacturerIn(**stored_manufacturer.model_dump()))

    def delete(self, manufacturer_id: str) -> None:
        """
        Delete a manufacturer by its ID.

        :param manufacturer_id: The ID of the manufacturer to delete.
        :raises MissingRecordError: If the supplied `manufacturer_id` is non-existent.
        :raises InvalidObjectIdError: If the supplied `manufacturer_id` is invalid.
        """
        try:
            return self._manufacturer_repository.delete(manufacturer_id)
        except (MissingRecordError, InvalidObjectIdError) as exc:
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.response_detail = "Manufacturer not found"
            raise exc
