"""
Module for providing a service for managing settings using the `SettingRepo` repository.
"""

import logging
from typing import Annotated

from fastapi import Depends

from inventory_management_system_api.core.database import start_session_transaction
from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.setting import SparesDefinitionIn, SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.setting import SparesDefinitionPutSchema
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class SettingService:
    """
    Service for managing settings.
    """

    def __init__(
        self,
        setting_repository: Annotated[SettingRepo, Depends(SettingRepo)],
        catalogue_item_repository: Annotated[CatalogueItemRepo, Depends(CatalogueItemRepo)],
        item_repository: Annotated[ItemRepo, Depends(ItemRepo)],
        usage_status_repository: Annotated[UsageStatusRepo, Depends(UsageStatusRepo)],
    ) -> None:
        """
        Initialise the `SettingService` with a `SettingRepo` repository.

        :param setting_repository: `SettingRepo` repository to use.
        :param catalogue_item_repository: `CatalogueItemRepo` repository to use.
        :param item_repository: `ItemRepo` repository to use.
        :param usage_status_repository: `UsageStatusRepo` repository to use.
        """
        self._setting_repository = setting_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._item_repository = item_repository
        self._usage_status_repository = usage_status_repository

    def update_spares_definition(self, spares_definition: SparesDefinitionPutSchema) -> SparesDefinitionOut:
        """
        Updates the spares definition to a new value.

        :param spares_definition: The new spares definition.
        :return: The updated spares definition.
        :raises MissingRecordError: If any of the usage statuses specified by the given IDs don't exist.
        """

        # Ensure all the given usage statuses exist
        for usage_status in spares_definition.usage_statuses:
            if not self._usage_status_repository.get(usage_status.id):
                raise MissingRecordError(f"No usage status found with ID: {usage_status.id}")

        # Need all updates to the number of spares to succeed or fail together with assigning the new definition
        # Also need to be able to write lock the catalogue item documents in the process to prevent further changes
        # while recalculating
        with start_session_transaction("updating spares definition") as session:
            # Update spares definition first to ensure write locked to prevent further updates while calculating below
            new_spares_definition = self._setting_repository.upsert(
                SparesDefinitionIn(**spares_definition.model_dump()), SparesDefinitionOut, session=session
            )

            # TODO: Update tests to reflect new order here

            # Write lock for spares definition document to prevent any more catalogue items being created
            self._setting_repository.write_lock(SparesDefinitionOut, session)

            # Write lock all catalogue items to prevent any other spares calculations from happening
            utils.prepare_for_number_of_spares_recalculation(None, self._catalogue_item_repository, session)

            # Obtain a list of all catalogue item ids that will need to be recalculated
            catalogue_item_ids = self._catalogue_item_repository.list_ids()

            # Usage status id that constitute a spare in the new definition (obtain it now to save processing
            # repeatedly)
            usage_status_ids = utils.get_usage_status_ids_from_spares_definition(new_spares_definition)

            # Recalculate for each catalogue item
            logger.info("Updating the number of spares for all catalogue items")
            for catalogue_item_id in catalogue_item_ids:
                utils.perform_number_of_spares_recalculation(
                    catalogue_item_id, usage_status_ids, self._catalogue_item_repository, self._item_repository, session
                )

        return new_spares_definition
