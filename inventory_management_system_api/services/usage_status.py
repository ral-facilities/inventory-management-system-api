"""
Module for providing a service for managing Usage statuses using the `UsageStatusRepo` repository
"""

from typing import Annotated

from fastapi import Depends, status

from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.usage_status import UsageStatusPostSchema
from inventory_management_system_api.services import utils


class UsageStatusService:
    """
    Service for managing Usage statuses
    """

    def __init__(self, usage_status_repository: Annotated[UsageStatusRepo, Depends(UsageStatusRepo)]) -> None:
        """
        Initialise the `UsageStatusService` with a `UsageStatusRepo` repository

        :param usage_status_repository: `UsageStatusRepo` repository to use
        """
        self._usage_status_repository = usage_status_repository

    def create(self, usage_status: UsageStatusPostSchema) -> UsageStatusOut:
        """
        Create a new usage status.

        :param usage_status: The usage status to be created.
        :return: The created usage status.
        """
        code = utils.generate_code(usage_status.value, "usage status")
        return self._usage_status_repository.create(UsageStatusIn(**usage_status.model_dump(), code=code))

    def get(self, usage_status_id: str) -> UsageStatusOut:
        """
        Get usage status by its ID.

        :param: usage_status_id: The ID of the requested usage status.
        :return: The retrieved usage status.
        :raises MissingRecordError: If the supplied `usage_status_id` is non-existent.
        :raises InvalidObjectIdError: If the supplied `usage_status_id` is invalid.
        """
        try:
            return self._usage_status_repository.get(usage_status_id)
        except (MissingRecordError, InvalidObjectIdError) as exc:
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.response_detail = "Usage status not found"
            raise exc

    def list(self) -> list[UsageStatusOut]:
        """
        Retrieve a list of all Usage statuses

        :return: List of Usage statuses or an empty list if no Usage statuses are retrieved
        """
        return self._usage_status_repository.list()

    def delete(self, usage_status_id: str) -> None:
        """
        Delete a usage status by its ID

        :param usage_status_id: The ID of the usage status to delete
        :raises MissingRecordError: If the supplied `catalogue_category_id` is non-existent.
        :raises InvalidObjectIdError: If the supplied `catalogue_category_id` is invalid.
        """
        try:
            return self._usage_status_repository.delete(usage_status_id)
        except (MissingRecordError, InvalidObjectIdError) as exc:
            exc.status_code = status.HTTP_404_NOT_FOUND
            exc.response_detail = "Usage status not found"
            raise exc
