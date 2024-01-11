"""
Module for providing a service for managing items using the `ItemRepo`, `CatalogueCategoryRepo`, and `CatalogueItemRepo`
repositories.
"""

import logging
from typing import List, Optional

from fastapi import Depends

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    DatabaseIntegrityError,
    InvalidObjectIdError,
)
from inventory_management_system_api.models.catalogue_item import Property
from inventory_management_system_api.models.item import ItemOut, ItemIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.schemas.catalogue_item import PropertyPostRequestSchema
from inventory_management_system_api.schemas.item import ItemPostRequestSchema
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class ItemService:
    """
    Service for managing items.
    """

    def __init__(
        self,
        item_repository: ItemRepo = Depends(ItemRepo),
        catalogue_category_repository: CatalogueCategoryRepo = Depends(CatalogueCategoryRepo),
        catalogue_item_repository: CatalogueItemRepo = Depends(CatalogueItemRepo),
    ) -> None:
        """
        Initialise the `ItemService` with an `ItemRepo`, `CatalogueCategoryRepo`, and `CatalogueItemRepo` repos.

        :param item_repository: The `ItemRepo` repository to use.
        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        """
        self._item_repository = item_repository
        self._catalogue_category_repository = catalogue_category_repository
        self._catalogue_item_repository = catalogue_item_repository

    def create(self, item: ItemPostRequestSchema) -> ItemOut:
        """
        Create a new item.

        All properties found in the catalogue item will be inherited if not explicitly provided.

        :param item: The item to be created.
        :return: The created item.
        :raises MissingRecordError: If the catalogue item does not exist.
        """
        catalogue_item_id = item.catalogue_item_id
        catalogue_item = self._catalogue_item_repository.get(catalogue_item_id)
        if not catalogue_item:
            raise MissingRecordError(f"No catalogue item found with ID: {catalogue_item_id}")

        try:
            catalogue_category_id = catalogue_item.catalogue_category_id
            catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
            if not catalogue_category:
                raise DatabaseIntegrityError(f"No catalogue category found with ID: {catalogue_category_id}")
        except InvalidObjectIdError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc

        supplied_properties = item.properties if item.properties else []
        missing_supplied_properties = self._find_missing_supplied_properties(
            catalogue_item.properties, supplied_properties
        )
        # Inherit the missing properties from the corresponding catalogue item. Create `PropertyPostRequestSchema`
        # objects for the inherited properties and add them to the `supplied_properties` list before proceeding with
        # processing and validation.
        supplied_properties.extend(
            [PropertyPostRequestSchema(**prop.model_dump()) for prop in missing_supplied_properties]
        )

        defined_properties = catalogue_category.catalogue_item_properties
        properties = utils.process_catalogue_item_properties(defined_properties, supplied_properties)

        return self._item_repository.create(
            ItemIn(
                **{
                    **item.model_dump(),
                    "properties": properties,
                }
            )
        )

    def delete(self, item_id: str) -> None:
        """
        Delete an item by its ID.

        :param item_id: The ID of the item to delete.
        """
        return self._item_repository.delete(item_id)

    def list(self, system_id: Optional[str], catalogue_item_id: Optional[str]) -> List[ItemOut]:
        """
        Get all items

        :param system_id: The ID of the system to filter items by.
        :param catalogue_item_id: The ID of the catalogue item to filter by.
        :return: list of all items
        """
        return self._item_repository.list(system_id, catalogue_item_id)

    def get(self, item_id: str) -> Optional[ItemOut]:
        """
        Retrieve an item by its ID

        :param item_id: The ID of the item to retrieve
        :return: The retrieved item, or `None` if not found
        """

        return self._item_repository.get(item_id)

    def _find_missing_supplied_properties(
        self, catalogue_item_properties: List[Property], supplied_properties: List[PropertyPostRequestSchema]
    ) -> List[Property]:
        """
        Find the properties that have not been supplied. If a property is part of the corresponding catalogue item but
        not part of the supplied properties, it means that it is missing.

        :param catalogue_item_properties: The list of property objects from the catalogue item.
        :param supplied_properties: The list of supplied property objects specific to the item.
        :return: A list of properties that are have not been supplied.
        """
        supplied_property_names = [supplied_property.name for supplied_property in supplied_properties]

        missing_supplied_properties = []
        for catalogue_item_property in catalogue_item_properties:
            if catalogue_item_property.name not in supplied_property_names:
                missing_supplied_properties.append(catalogue_item_property)

        return missing_supplied_properties
