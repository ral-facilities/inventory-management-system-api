"""
Module for providing a service for managing items using the `ItemRepo` repository.
"""

import logging

from fastapi import Depends

from inventory_management_system_api.repositories.item import ItemRepo

logger = logging.getLogger()


class ItemService:
    """
    Service for managing items.
    """

    def __init__(self, item_repository: ItemRepo = Depends(ItemRepo)) -> None:
        """
        Initialise the `ItemService` with an `ItemRepo` repo.

        :param item_repository: The `ItemRepo` repository to use."""
        self._item_repository = item_repository
