"""
Module for providing a service for managing settings using the `SettingRepo` repository.
"""

import logging
from typing import Annotated

from fastapi import Depends

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.setting import SparesDefinitionPutSchema

logger = logging.getLogger()


class SettingService:
    """
    Service for managing settings.
    """

    def __init__(
        self,
        setting_repository: Annotated[SettingRepo, Depends(SettingRepo)],
        usage_status_repository: Annotated[UsageStatusRepo, Depends(UsageStatusRepo)],
    ) -> None:
        """
        Initialise the `SettingService` with a `SettingRepo` repository.

        :param setting_repository: `SettingRepo` repository to use.
        :param usage_status_repository: `UsageStatusRepo` repository to use
        """
        self._setting_repository = setting_repository
        self._usage_status_repository = usage_status_repository

    def set_spares_definition(self, spares_definition: SparesDefinitionPutSchema) -> SparesDefinitionOut:
        """
        Sets the spares definition to a new value.

        :param spares_definition: The new spares definition.
        :return: The updated spares definition.
        :raises MissingRecordError: If any of the usage statuses specified by the given IDs don't exist.
        """

        # Ensure all the given usage statuses exist
        for usage_status in spares_definition.usage_statuses:
            if not self._usage_status_repository.get(usage_status.id):
                raise MissingRecordError(f"No usage status found with ID: {usage_status.id}")

        return self._setting_repository.upsert(
            SparesDefinitionIn(**spares_definition.model_dump()), SparesDefinitionOut
        )

    def get_spares_definition(self) -> SparesDefinitionOut:
        """
        Retrieves the spares definition.

        :return: Retrieved spares definition or `None` if not found.
        """

        return self._setting_repository.get(SparesDefinitionOut)
