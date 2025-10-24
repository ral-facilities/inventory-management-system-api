"""
Module for providing a service for managing settings using the `SettingRepo` repository.
"""

import logging
from typing import Annotated, Callable, Iterable, Optional

from fastapi import Depends

from inventory_management_system_api.core.database import start_session_transaction
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system_type import SystemTypeRepo

logger = logging.getLogger()


class SettingService:
    """
    Service for managing settings.
    """

    def __init__(
        self,
        setting_repository: Annotated[SettingRepo, Depends(SettingRepo)],
        system_type_repository: Annotated[SystemTypeRepo, Depends(SystemTypeRepo)],
        catalogue_item_repository: Annotated[CatalogueItemRepo, Depends(CatalogueItemRepo)],
        item_repository: Annotated[ItemRepo, Depends(ItemRepo)],
    ) -> None:
        """
        Initialise the `SettingService` with `SettingRepo`, `SystemTypeRepo`, `CatalogueItemRepo` and `ItemRepo` repos.

        :param setting_repository: `SettingRepo` repository to use.
        :param system_type_repository: `SystemTypeRepo` repository to use.
        :param catalogue_item_repository: `CatalogueItemRepo` repository to use.
        :param item_repository: `ItemRepo` repository to use.
        """
        self._setting_repository = setting_repository
        self._system_type_repository = system_type_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._item_repository = item_repository

    def set_spares_definition(
        self, spares_definition: SparesDefinitionIn, tracker: Optional[Callable[[Iterable], Iterable]] = None
    ) -> SparesDefinitionOut:
        """
        Sets the spares definition to a new value.

        No write locks are used on the catalogue items, it is assumed that the system should be in a state where users
        are not able to access the API and no requests are currently in progress.

        :param spares_definition: New spares definition.
        :param tracker: Tracker function to use for tracking progress e.g. Rich's track function.
        :return: Updated spares definition.
        :raises MissingRecordError: If any of the system types specified by the given IDs don't exist.
        """

        # Ensure all the given system types exist
        for system_type_id in spares_definition.system_type_ids:
            if not self._system_type_repository.get(str(system_type_id)):
                raise MissingRecordError(f"No system type found with ID '{system_type_id}'")

        # Need all updates to the number of spares to succeed or fail together with assigning the new definition
        with start_session_transaction("setting spares definition") as session:
            # Update the spares definition (being done first means two assignments at the same time would conflict
            # early)
            new_spares_definition = self._setting_repository.upsert(
                spares_definition, SparesDefinitionOut, session=session
            )

            # Obtain a list of all catalogue item ids (all will need a recount)
            catalogue_item_ids = self._catalogue_item_repository.list_ids()

            # Recalculate the number of spares for each catalogue item
            logger.info("Updating the number of spares for all catalogue items")
            for catalogue_item_id in catalogue_item_ids if tracker is None else tracker(catalogue_item_ids):
                number_of_spares = self._item_repository.count_in_catalogue_item_with_system_type_one_of(
                    catalogue_item_id,
                    spares_definition.system_type_ids,
                    session=session,
                )
                self._catalogue_item_repository.update_number_of_spares(
                    catalogue_item_id, number_of_spares, session=session
                )

            return new_spares_definition

    def get_spares_definition(self) -> Optional[SparesDefinitionOut]:
        """
        Retrieve the spares definition setting.

        :return: Retrieved spares definition or `None` if not found.
        """
        return self._setting_repository.get(SparesDefinitionOut)
