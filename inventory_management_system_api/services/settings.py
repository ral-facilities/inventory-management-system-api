"""
Module for providing a service for managing settings using the `SettingsRepo` repository.
"""

import logging
from typing import Annotated

from fastapi import Depends

from inventory_management_system_api.models.settings import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.settings import SettingsRepo
from inventory_management_system_api.schemas.settings import SparesDefinitionPutSchema

logger = logging.getLogger()


class SettingsService:
    """
    Service for managing settings.
    """

    def __init__(self, settings_repository: Annotated[SettingsRepo, Depends(SettingsRepo)]) -> None:
        """
        Initialise the `SettingsService` with a `SettingsRepo` repository.

        :param settings_repository: `SettingsRepo` repository to use.
        """
        self._settings_repository = settings_repository

    # TODO: Comment
    def update_spares_definition(self, spares_definition: SparesDefinitionPutSchema) -> SparesDefinitionOut:
        return self._settings_repository.update(
            SparesDefinitionIn(**spares_definition.model_dump()), SparesDefinitionOut
        )
