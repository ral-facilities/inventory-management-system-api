"""
Module for providing a service for managing Usage statuses using the `UsageStatusRepo` repository
"""

from fastapi import Depends
from inventory_management_system_api.models.usage_status import UsageStatusOut
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo


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

    def list(self) -> list[UsageStatusOut]:
        """
        Retrieve a list of all Usage statuses

        :return: List of Usage statuses or an empty list if no Usage statuses are retrieved
        """
        return self._usage_status_repository.list()
