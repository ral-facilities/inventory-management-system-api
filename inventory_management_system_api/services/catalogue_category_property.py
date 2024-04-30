"""
Module for providing a service for managing properties at the catalogue category level that may also require
propagation down through their child catalogue items and items using their respective repositories
"""

import logging

from fastapi import Depends

from inventory_management_system_api.core.database import mongodb_client
from inventory_management_system_api.core.exceptions import InvalidActionError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueItemPropertyIn,
    CatalogueItemPropertyOut,
)
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueItemPropertyPostRequestSchema,
    CatalogueItemPropertySchema,
)
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
        stored_catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        # Must be a leaf catalogue category in order to have properties
        if not stored_catalogue_category.is_leaf:
            raise InvalidActionError("Cannot add a property to a non-leaf catalogue category")

        # Ensure the property is actually valid
        utils.check_duplicate_catalogue_item_property_names(
            stored_catalogue_category.catalogue_item_properties + [catalogue_item_property]
        )

        catalogue_item_property_in = CatalogueItemPropertyIn(**catalogue_item_property.model_dump())

        # New catalogue category data
        catalogue_category_in = CatalogueCategoryIn(**stored_catalogue_category.model_dump())
        catalogue_category_in.catalogue_item_properties.append(catalogue_item_property_in)

        # Run all subsequent edits within a transaction to ensure they will all succeed or fail together
        with mongodb_client.start_session() as session:
            with session.start_transaction():
                # Firstly update the catalogue category
                self._catalogue_category_repository.update(
                    catalogue_category_id, catalogue_category_in, session=session
                )

                # Property to be added catalogue items and items
                property_in = PropertyIn(
                    id=str(catalogue_item_property_in.id),
                    name=catalogue_item_property_in.name,
                    value=catalogue_item_property.default_value,
                    unit=catalogue_item_property.unit,
                )

                # Add property to all catalogue items of the catalogue category
                self._catalogue_item_repository.insert_property_to_all_matching(
                    catalogue_category_id, property_in, session=session
                )

                # Add property to all items of the catalogue items
                # Obtain a list of ids to do this rather than iterate one by one as its faster. Limiting factor
                # would be memory to store these ids and the network bandwidth it takes to send the request to the
                # database but for 10000 items being updated this only takes 4.92 KB
                catalogue_item_ids = self._catalogue_item_repository.list_ids(catalogue_category_id, session=session)
                self._item_repository.insert_property_to_all_in(catalogue_item_ids, property_in, session=session)

        return CatalogueItemPropertyOut(**catalogue_item_property_in.model_dump())
