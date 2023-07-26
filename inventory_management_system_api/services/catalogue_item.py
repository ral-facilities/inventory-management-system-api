"""
Module for providing a service for managing catalogue items using the `CatalogueItemRepo` and `CatalogueItemRepo`
repositories.
"""
import logging

from fastapi import Depends

from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo

logger = logging.getLogger()


class CatalogueItemService:
    """
    Service for managing catalogue items.
    """

    def __init__(self, catalogue_item_repository: CatalogueItemRepo = Depends(CatalogueItemRepo)) -> None:
        """
        Initialise the `CatalogueItemService` with a `CatalogueItemRepo` repo.

        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        """
        self._catalogue_item_repository = catalogue_item_repository
