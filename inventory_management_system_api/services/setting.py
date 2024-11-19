"""
Module for providing a service for managing settings using the `SettingRepo` repository.
"""

import logging
from typing import Annotated

from fastapi import Depends

from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.schemas.setting import SparesDefinitionPutSchema

logger = logging.getLogger()


class SettingService:
    """
    Service for managing settings.
    """

    def __init__(self, setting_repository: Annotated[SettingRepo, Depends(SettingRepo)]) -> None:
        """
        Initialise the `SettingService` with a `SettingRepo` repository.

        :param setting_repository: `SettingRepo` repository to use.
        """
        self._setting_repository = setting_repository

    # TODO: Comment
    def update_spares_definition(self, spares_definition: SparesDefinitionPutSchema) -> SparesDefinitionOut:
        # TODO: Ensure the given usage statuses exist
        return self._setting_repository.update(
            SparesDefinitionIn(**spares_definition.model_dump()), SparesDefinitionOut
        )
