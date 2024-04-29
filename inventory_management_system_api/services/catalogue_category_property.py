"""
Module for providing a service for managing properties at the catalogue category level that may also require
propagation down through their child catalogue items and items using their respective repositories
"""

import logging
from fastapi import Depends

from inventory_management_system_api.core.exceptions import InvalidActionError
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueItemPropertyPostRequestSchema,
    CatalogueItemPropertySchema,
)
from inventory_management_system_api.core.database import mongodb_client
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class CatalogueCategoryPropertyService:
    """
    Service for managing properties at the catalogue category level downwards
    """

    def __init__(
        self,
        catalogue_category_repository: CatalogueCategoryRepo = Depends(CatalogueCategoryRepo),
        catalogue_item_repository: CatalogueItemRepo = Depends(CatalogueItemRepo),
        item_repository: ItemRepo = Depends(ItemRepo),
    ):
        """
        Initialise the `PropertyService` with a `CatalogueCategoryRepo`, `CatalogueItemRepo` and `ItemRepo` repos.

        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param item_repository: The `ItemRepo` repository to use.
        """
        self._catalogue_category_repository = catalogue_category_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._item_repository = item_repository

    def create(
        self,
        catalogue_category_id: str,
        catalogue_item_property: CatalogueItemPropertyPostRequestSchema,
    ) -> CatalogueItemPropertySchema:
        """Create a new property at the catalogue category level

        Property will be propagated down through catalogue items and items when there are children.

        :param catalogue_category_id: ID of the catalogue category to add the property to
        :catalogue_item_property: Property to add (with additional info on how to perform the migration if necessary)
        :raises InvalidActionError: If attempting to add a mandatory property without a default_value being specified
        :return: The created catalogue item property as defined at the catalogue category level
        """

        # Mandatory properties must have a default value that is not None as they would need to be
        # populated down the subtree
        if catalogue_item_property.mandatory and catalogue_item_property.default_value is None:
            raise InvalidActionError("Cannot add a mandatory property without a default value")

        # Obtain the existing catalogue category to validate against
        catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)

        # Ensure the property is actually valid
        utils.check_duplicate_catalogue_item_property_names(
            catalogue_category.catalogue_item_properties + [catalogue_item_property]
        )

        # Run all subsequent edits within a transaction to ensure they will all succeed or fail together
        with mongodb_client.start_session() as session:
            with session.start_transaction():
                pass
