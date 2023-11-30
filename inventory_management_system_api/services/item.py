"""
Module for providing a service for managing items using the `ItemRepo`, `CatalogueCategoryRepo`, and `CatalogueItemRepo`
repositories.
"""

import logging
from typing import List

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

        supplied_properties = item.catalogue_item_override_properties if item.catalogue_item_override_properties else []
        non_overriden_properties = self._get_non_overriden_catalogue_item_properties(
            catalogue_item.properties, supplied_properties
        )
        # Use the properties from the catalogue item for those that have not been overriden
        supplied_properties.extend(
            [PropertyPostRequestSchema(**prop.model_dump()) for prop in non_overriden_properties]
        )

        defined_properties = catalogue_category.catalogue_item_properties
        override_properties = utils.process_catalogue_item_properties(defined_properties, supplied_properties)

        return self._item_repository.create(
            ItemIn(
                **{
                    **item.model_dump(),
                    "catalogue_item_override_properties": override_properties,
                }
            )
        )

    def _get_non_overriden_catalogue_item_properties(
        self, catalogue_item_properties: List[Property], supplied_properties: List[PropertyPostRequestSchema]
    ) -> List[Property]:
        """
        Get the properties from the catalogue item that have not been overriden. If a catalogue item property is not
        part of the supplied properties it means that it has not been overriden.

        :param catalogue_item_properties: The list of property objects from the catalogue item.
        :param supplied_properties: The list of supplied catalogue item override property objects.
        :return: A list of non overriden catalogue item properties.
        """
        supplied_property_names = [supplied_property.name for supplied_property in supplied_properties]

        non_overriden_properties = []
        for catalogue_item_property in catalogue_item_properties:
            if catalogue_item_property.name not in supplied_property_names:
                non_overriden_properties.append(catalogue_item_property)

        return non_overriden_properties
