"""
Module for providing a service for managing Usage statuses using the `UsageStatusRepo` repository
"""

from typing import Optional
from fastapi import Depends
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.usage_status import UsageStatusPostRequestSchema

from inventory_management_system_api.services import utils


class UsageStatusService:
    """
    Service for managing Usage statuses
    """

    def __init__(self, usage_status_repository: UsageStatusRepo = Depends(UsageStatusRepo)) -> None:
        """
        Initialise the `UsageStatusService` with a `UsageStatusRepo` repository

        :param usage_status_repository: `UsageStatusRepo` repository to use
        """
        self._usage_status_repository = usage_status_repository

    def create(self, usage_status: UsageStatusPostRequestSchema) -> UsageStatusOut:
        """
        Create a new usage status.
        :param  usage_status: The usage status to be created.
        :return: The created usage status.
        """
        code = utils.generate_code(usage_status.value, "usage status")
        return self._usage_status_repository.create(UsageStatusIn(**usage_status.model_dump(), code=code))

    def get(self, usage_status_id: str) -> Optional[UsageStatusOut]:
        """
        Get usage status by its ID.
        :param: usage_status_id: The ID of the requested usage status
        :return: The retrieved usage status, or None if not found
        """
        return self._usage_status_repository.get(usage_status_id)

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
        """
        return self._usage_status_repository.delete(usage_status_id)
