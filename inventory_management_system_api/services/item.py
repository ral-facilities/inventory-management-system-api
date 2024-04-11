"""
Module for providing a service for managing items using the `ItemRepo`, `CatalogueCategoryRepo`, and `CatalogueItemRepo`
repositories.
"""

import logging
from typing import List, Optional

from fastapi import Depends

from inventory_management_system_api.core.exceptions import (
    InvalidActionError,
    MissingRecordError,
    DatabaseIntegrityError,
    InvalidObjectIdError,
)
from inventory_management_system_api.models.catalogue_item import Property
from inventory_management_system_api.models.item import ItemOut, ItemIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.catalogue_item import PropertyPostRequestSchema
from inventory_management_system_api.schemas.item import ItemPatchRequestSchema, ItemPostRequestSchema
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
        system_repository: SystemRepo = Depends(SystemRepo),
        usage_status_repository: UsageStatusRepo = Depends(UsageStatusRepo),
        # pylint: disable=too-many-arguments
    ) -> None:
        """
        Initialise the `ItemService` with an `ItemRepo`, `CatalogueCategoryRepo`,
        `CatalogueItemRepo`, `SystemRepo` and `UsageStatusRepo` repos.

        :param item_repository: The `ItemRepo` repository to use.
        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param system_repository: The `SystemRepo` repository to use.
        :param usage_status_repository: The `UsageStatusRepo` repository to use.
        """
        self._item_repository = item_repository
        self._catalogue_category_repository = catalogue_category_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._system_repository = system_repository
        self._usage_status_repository = usage_status_repository

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

        usage_statuses = [usage_status.value for usage_status in self._usage_status_repository.list()]
        if item.usage_status not in usage_statuses:
            raise MissingRecordError(f"No usage status found with name: {item.usage_status}")

        supplied_properties = item.properties if item.properties else []
        # Inherit the missing properties from the corresponding catalogue item
        supplied_properties = self._merge_missing_properties(catalogue_item.properties, supplied_properties)

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

    def update(self, item_id: str, item: ItemPatchRequestSchema) -> ItemOut:
        """
        Update an item by its ID.

        The method checks if the item exists in the database and raises a `MissingRecordError` if it does
        not. If the system ID is being updated, it checks if the system ID with such ID exists and raises
        a `MissingRecordError` if it does not. It raises a `ChildElementsExistError` if a catalogue item
        ID is supplied. When updatimg properties, existing properties must all be supplied, or they will
        be overwritten by the catalogue item properties.

        :param item_id: The ID of the item to update.
        :param item: The item containing the fields that need to be updated.
        :return: The updated item.
        """
        update_data = item.model_dump(exclude_unset=True)

        stored_item = self.get(item_id)
        if not stored_item:
            raise MissingRecordError(f"No item found with ID: {item_id}")

        if "catalogue_item_id" in update_data and item.catalogue_item_id != stored_item.catalogue_item_id:
            raise InvalidActionError("Cannot change the catalogue item the item belongs to")

        if "system_id" in update_data and item.system_id != stored_item.system_id:
            system = self._system_repository.get(item.system_id)
            if not system:
                raise MissingRecordError(f"No system found with ID: {item.system_id}")
        if "usage_status" in update_data and item.usage_status != stored_item.usage_status:
            usage_statuses = [usage_status.value for usage_status in self._usage_status_repository.list()]
            if item.usage_status not in usage_statuses:
                raise MissingRecordError(f"No usage status found with name: {item.usage_status}")

        # If catalogue item ID not supplied then it will be fetched, and its parent catalogue category.
        # the defined (at a catalogue category level) and supplied properties will be used to find
        # missing supplied properties. They will then be processed and validated.

        if "properties" in update_data:
            catalogue_item = self._catalogue_item_repository.get(stored_item.catalogue_item_id)

            try:
                catalogue_category_id = catalogue_item.catalogue_category_id
                catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
                if not catalogue_category:
                    raise DatabaseIntegrityError(f"No catalogue category found with ID: {catalogue_category_id}")
            except InvalidObjectIdError as exc:
                raise DatabaseIntegrityError(str(exc)) from exc

            defined_properties = catalogue_category.catalogue_item_properties

            # Inherit the missing properties from the corresponding catalogue item
            supplied_properties = self._merge_missing_properties(catalogue_item.properties, item.properties)

            update_data["properties"] = utils.process_catalogue_item_properties(defined_properties, supplied_properties)

        return self._item_repository.update(item_id, ItemIn(**{**stored_item.model_dump(), **update_data}))

    def _merge_missing_properties(
        self, catalogue_item_properties: List[Property], supplied_properties: List[PropertyPostRequestSchema]
    ) -> List[PropertyPostRequestSchema]:
        """
        Merges the properties defined in a catalogue item with those that should be overriden for an item in
        the order they are defined in the catalogue item.

        :param catalogue_item_properties: The list of property objects from the catalogue item.
        :param supplied_properties: The list of supplied property objects specific to the item.
        :return: A merged list of properties for the item
        """
        supplied_properties_dict = {
            supplied_property.name: supplied_property for supplied_property in supplied_properties
        }
        properties: List[PropertyPostRequestSchema] = []

        # Use the order of properties from the catalogue item, and append either the supplied property or
        # the catalogue item one where it is not found
        for catalogue_item_property in catalogue_item_properties:
            supplied_property = supplied_properties_dict.get(catalogue_item_property.name)
            if supplied_property is not None:
                properties.append(supplied_property)
            else:
                properties.append(PropertyPostRequestSchema(**catalogue_item_property.model_dump()))
        return properties
