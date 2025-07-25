"""
Module for providing a service for managing items using the `ItemRepo`, `CatalogueCategoryRepo`, and `CatalogueItemRepo`
repositories.
"""

import logging
from contextlib import contextmanager
from typing import Annotated, Generator, List, Optional

from fastapi import Depends
from pymongo.client_session import ClientSession

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.database import start_session_transaction
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidActionError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.core.object_storage_api_client import ObjectStorageAPIClient
from inventory_management_system_api.models.catalogue_item import PropertyOut
from inventory_management_system_api.models.item import ItemIn, ItemOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.catalogue_item import PropertyPostSchema
from inventory_management_system_api.schemas.item import ItemPatchSchema, ItemPostSchema
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class ItemService:
    """
    Service for managing items.
    """

    # pylint:disable=too-many-arguments
    # pylint:disable=too-many-positional-arguments
    def __init__(
        self,
        item_repository: Annotated[ItemRepo, Depends(ItemRepo)],
        catalogue_category_repository: Annotated[CatalogueCategoryRepo, Depends(CatalogueCategoryRepo)],
        catalogue_item_repository: Annotated[CatalogueItemRepo, Depends(CatalogueItemRepo)],
        system_repository: Annotated[SystemRepo, Depends(SystemRepo)],
        usage_status_repository: Annotated[UsageStatusRepo, Depends(UsageStatusRepo)],
        setting_repository: Annotated[SettingRepo, Depends(SettingRepo)],
    ) -> None:
        """
        Initialise the `ItemService` with an `ItemRepo`, `CatalogueCategoryRepo`,
        `CatalogueItemRepo`, `SystemRepo` and `UsageStatusRepo` repos.

        :param item_repository: The `ItemRepo` repository to use.
        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param system_repository: The `SystemRepo` repository to use.
        :param usage_status_repository: The `UsageStatusRepo` repository to use.
        :param setting_repository: The `SettingRepo` repository to use.
        """
        self._item_repository = item_repository
        self._catalogue_category_repository = catalogue_category_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._system_repository = system_repository
        self._usage_status_repository = usage_status_repository
        self._setting_repository = setting_repository

    def create(self, item: ItemPostSchema) -> ItemOut:
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

        usage_status_id = item.usage_status_id
        usage_status = self._usage_status_repository.get(usage_status_id)
        if not usage_status:
            raise MissingRecordError(f"No usage status found with ID: {usage_status_id}")

        supplied_properties = item.properties if item.properties else []
        # Inherit the missing properties from the corresponding catalogue item
        supplied_properties = self._merge_missing_properties(catalogue_item.properties, supplied_properties)

        defined_properties = catalogue_category.properties
        properties = utils.process_properties(defined_properties, supplied_properties)

        # Update number of spares when creating
        with self._start_transaction_impacting_number_of_spares("creating item", catalogue_item_id) as session:
            return self._item_repository.create(
                ItemIn(**{**item.model_dump(), "properties": properties, "usage_status": usage_status.value}),
                session=session,
            )

    def get(self, item_id: str) -> Optional[ItemOut]:
        """
        Retrieve an item by its ID

        :param item_id: The ID of the item to retrieve
        :return: The retrieved item, or `None` if not found
        """
        return self._item_repository.get(item_id)

    def list(self, system_id: Optional[str], catalogue_item_id: Optional[str]) -> List[ItemOut]:
        """
        Get all items

        :param system_id: The ID of the system to filter items by.
        :param catalogue_item_id: The ID of the catalogue item to filter by.
        :return: list of all items
        """
        return self._item_repository.list(system_id, catalogue_item_id)

    # pylint:disable=too-many-locals
    def update(self, item_id: str, item: ItemPatchSchema) -> ItemOut:
        """
        Update an item by its ID.

        The method checks if the item exists in the database and raises a `MissingRecordError` if it does
        not. If the system ID is being updated, it checks if the system ID with such ID exists and raises
        a `MissingRecordError` if it does not. It raises a `ChildElementsExistError` if a catalogue item
        ID is supplied. When updating properties, existing properties must all be supplied, or they will
        be overwritten by the properties.

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

        moving_system = "system_id" in update_data and item.system_id != stored_item.system_id
        if moving_system:
            moving_system = True
            system = self._system_repository.get(item.system_id)
            if not system:
                raise MissingRecordError(f"No system found with ID: {item.system_id}")
        if "usage_status_id" in update_data and item.usage_status_id != stored_item.usage_status_id:
            usage_status_id = item.usage_status_id
            usage_status = self._usage_status_repository.get(usage_status_id)
            if not usage_status:
                raise MissingRecordError(f"No usage status found with ID: {usage_status_id}")
            update_data["usage_status"] = usage_status.value

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

            defined_properties = catalogue_category.properties

            # Inherit the missing properties from the corresponding catalogue item
            supplied_properties = self._merge_missing_properties(catalogue_item.properties, item.properties)

            update_data["properties"] = utils.process_properties(defined_properties, supplied_properties)

        # Moving system could effect the number of spares of the catalogue item as the type of the system might be
        # different
        if moving_system:
            # Can't currently move items, so just use the stored catalogue item
            with self._start_transaction_impacting_number_of_spares(
                "updating item", stored_item.catalogue_item_id
            ) as session:
                return self._item_repository.update(
                    item_id, ItemIn(**{**stored_item.model_dump(), **update_data}), session=session
                )

        return self._item_repository.update(item_id, ItemIn(**{**stored_item.model_dump(), **update_data}))

    # pylint:enable=too-many-locals

    def delete(self, item_id: str, access_token: Optional[str] = None) -> None:
        """
        Delete an item by its ID.

        :param item_id: The ID of the item to delete.
        :param access_token: The JWT access token to use for auth with the Object Storage API if object storage enabled.
        :raises MissingRecordError: If the item doesn't exist.
        """
        item = self.get(item_id)
        if item is None:
            raise MissingRecordError(f"No item found with ID: {str(item_id)}")

        # First, attempt to delete any attachments and/or images that might be associated with this item.
        if config.object_storage.enabled:
            ObjectStorageAPIClient.delete_attachments(item_id, access_token)
            ObjectStorageAPIClient.delete_images(item_id, access_token)

        # Deleting could effect the number of spares of the catalogue item if this one is currently a spare
        with self._start_transaction_impacting_number_of_spares("deleting item", item.catalogue_item_id) as session:
            return self._item_repository.delete(item_id, session=session)

    def _merge_missing_properties(
        self, properties: List[PropertyOut], supplied_properties: List[PropertyPostSchema]
    ) -> List[PropertyPostSchema]:
        """
        Merges the properties defined in a catalogue item with those that should be overridden for an item in
        the order they are defined in the catalogue item.

        :param properties: The list of property objects from the catalogue item.
        :param supplied_properties: The list of supplied property objects specific to the item.
        :return: A merged list of properties for the item
        """
        supplied_properties_dict = {
            supplied_property.id: supplied_property for supplied_property in supplied_properties
        }
        merged_properties: List[PropertyPostSchema] = []

        # Use the order of properties from the catalogue item, and append either the supplied property or
        # the catalogue item one where it is not found
        for prop in properties:
            supplied_property = supplied_properties_dict.get(prop.id)
            if supplied_property is not None:
                merged_properties.append(supplied_property)
            else:
                merged_properties.append(PropertyPostSchema(**prop.model_dump()))
        return merged_properties

    @contextmanager
    def _start_transaction_impacting_number_of_spares(
        self, action_description: str, catalogue_item_id: str
    ) -> Generator[Optional[ClientSession], None, None]:
        """
        Handles recalculation of the `number_of_spares` of a catalogue item for updates that will impact it but only
        when there is a spares defintion is set.

        Starts a MongoDB session and transaction, then write locks the catalogue item before yielding to allow an
        update to take place using the returned session. Once any tasks using the session context have finished it will
        finish by recalculating the number of spares for the catalogue item before finishing the transaction. This write
        lock prevents similar actions from occuring during the update to prevent an incorrect update e.g. if another
        item was added between counting the documents and then updating the number of spares field it would cause a
        miscount. It also ensures any action executed using the session will either fail or succeed with the spares
        update.

        :param action_description: Description of what the contents of the transaction is doing so it can be used in
                                   any logging or raise errors.
        :param catalogue_item_id: ID of the effected catalogue item which will need its `number_of_spares` field
                                  updating.
        """

        # Firstly obtain the spares defintion, to figure out if it is defined or not
        spares_definition = self._setting_repository.get(SparesDefinitionOut)

        if spares_definition is None:
            # No session/transaction is needed as there is no spares update to perform
            yield None
        else:
            with start_session_transaction(action_description) as session:
                # Write lock the catalogue item to prevent any other updates from occuring during the rest of the
                # transaction
                self._catalogue_item_repository.update_number_of_spares(catalogue_item_id, None, session=session)

                # Allow any other updates to occur using the same session
                yield session

                # Obtain and update the number of spares
                logger.info("Updating the number of spares of the catalogue item with ID %s", catalogue_item_id)
                number_of_spares = self._item_repository.count_in_catalogue_item_with_system_type_one_of(
                    catalogue_item_id, spares_definition.system_type_ids, session=session
                )
                self._catalogue_item_repository.update_number_of_spares(
                    catalogue_item_id, number_of_spares, session=session
                )
