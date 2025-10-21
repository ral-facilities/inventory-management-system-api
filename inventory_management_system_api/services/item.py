"""
Module for providing a service for managing items using the `ItemRepo`, `CatalogueCategoryRepo`, and `CatalogueItemRepo`
repositories.
"""

import logging
import random
import time
from contextlib import contextmanager
from typing import Annotated, Generator, List, Optional

from fastapi import Depends
from pymongo.client_session import ClientSession

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import start_session_transaction
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidActionError,
    InvalidObjectIdError,
    MissingRecordError,
    WriteConflictError,
)
from inventory_management_system_api.core.object_storage_api_client import ObjectStorageAPIClient
from inventory_management_system_api.models.catalogue_item import PropertyOut
from inventory_management_system_api.models.item import ItemIn, ItemOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.rule import RuleRepo
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
    # pylint:disable=too-many-locals
    def __init__(
        self,
        item_repository: Annotated[ItemRepo, Depends(ItemRepo)],
        catalogue_category_repository: Annotated[CatalogueCategoryRepo, Depends(CatalogueCategoryRepo)],
        catalogue_item_repository: Annotated[CatalogueItemRepo, Depends(CatalogueItemRepo)],
        system_repository: Annotated[SystemRepo, Depends(SystemRepo)],
        usage_status_repository: Annotated[UsageStatusRepo, Depends(UsageStatusRepo)],
        rule_repository: Annotated[RuleRepo, Depends(RuleRepo)],
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
        :param rule_repository: The `RuleRepo` repository to use.
        :param setting_repository: The `SettingRepo` repository to use.
        """
        self._item_repository = item_repository
        self._catalogue_category_repository = catalogue_category_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._system_repository = system_repository
        self._usage_status_repository = usage_status_repository
        self._rule_repository = rule_repository
        self._setting_repository = setting_repository

    def create(self, item: ItemPostSchema, is_authorised: bool) -> ItemOut:
        """
        Create a new item.

        All properties found in the catalogue item will be inherited if not explicitly provided.

        :param item: The item to be created.
        :return: The created item.
        :raises MissingRecordError: If the catalogue item does not exist.
        :raises MissingRecordError: If the system does not exist.
        :raises MissingRecordError: If the usage status does not exist.
        :raises DatabaseIntegrityError: If the catalogue category of the catalogue item doesn't exist.
        :raises InvalidActionError: If creating an item in a system with a usage status for which a creation rule does
            not exist.
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

        system_id = item.system_id
        system = self._system_repository.get(system_id)
        if not system:
            raise MissingRecordError(f"No system found with ID: {system_id}")

        usage_status_id = item.usage_status_id
        usage_status = self._usage_status_repository.get(usage_status_id)
        if not usage_status:
            raise MissingRecordError(f"No usage status found with ID: {usage_status_id}")

        # Bypass rule check if authorised
        if not is_authorised:
            if not self._rule_repository.check_exists(
                src_system_type_id=None,
                dst_system_type_id=system.type_id,
                dst_usage_status_id=usage_status_id,
            ):
                raise InvalidActionError(
                    "No rule found for creating items in the specified system with the specified usage status"
                )

        supplied_properties = item.properties if item.properties else []
        # Inherit the missing properties from the corresponding catalogue item
        supplied_properties = self._merge_missing_properties(catalogue_item.properties, supplied_properties)

        defined_properties = catalogue_category.properties
        properties = utils.process_properties(defined_properties, supplied_properties)

        # Update number of spares when creating
        with self._start_transaction_impacting_number_of_spares(
            "creating item", catalogue_item_id, item.system_id
        ) as session:
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

    def update(self, item_id: str, item: ItemPatchSchema, is_authorised: bool) -> ItemOut:
        """
        Update an item by its ID.

        When updating properties, existing properties must all be supplied, or they will be overwritten by the
        properties.

        :param item_id: The ID of the item to update.
        :param item: The item containing the fields that need to be updated.
        :raises MissingRecordError: If the item doesn't exist.
        :raises InvalidActionError: If attempting to change the catalogue item of the item.
        :return: The updated item.
        """
        update_data = item.model_dump(exclude_unset=True)

        stored_item = self.get(item_id)
        if not stored_item:
            raise MissingRecordError(f"No item found with ID: {item_id}")

        if "catalogue_item_id" in update_data and item.catalogue_item_id != stored_item.catalogue_item_id:
            raise InvalidActionError("Cannot change the catalogue item the item belongs to")

        moving_system = "system_id" in update_data and item.system_id != stored_item.system_id

        self._handle_system_and_usage_status_id_update(item, stored_item, update_data, moving_system, is_authorised)
        if "properties" in update_data:
            self._handle_properties_update(item, stored_item, update_data)

        # Moving system could effect the number of spares of the catalogue item as the type of the system might be
        # different
        if moving_system:
            # Can't currently move items, so we can just write lock the stored catalogue item as opposed to checking
            # the update data.
            with self._start_transaction_impacting_number_of_spares(
                "updating item", stored_item.catalogue_item_id, dest_system_id=item.system_id
            ) as session:
                return self._item_repository.update(
                    item_id, ItemIn(**{**stored_item.model_dump(), **update_data}), session=session
                )

        return self._item_repository.update(item_id, ItemIn(**{**stored_item.model_dump(), **update_data}))

    def delete(self, item_id: str, is_authorised: bool, access_token: Optional[str] = None) -> None:
        """
        Delete an item by its ID.

        :param item_id: The ID of the item to delete.
        :param access_token: The JWT access token to use for auth with the Object Storage API if object storage enabled.
        :raises MissingRecordError: If the item doesn't exist.
        :raises DatabaseIntegrityError: If the system in which the item is currently located doesn't exist.
        :raises InvalidActionError: If deleting an item from the current system but a deletion rule does not exist.
        """
        item = self.get(item_id)
        if item is None:
            raise MissingRecordError(f"No item found with ID: {item_id}")

        try:
            system_id = item.system_id
            system = self._system_repository.get(system_id)
            if not system:
                raise DatabaseIntegrityError(f"No system found with ID: {system_id}")
        except InvalidObjectIdError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc

        # Bypass rule check if authorised
        if not is_authorised:
            if not self._rule_repository.check_exists(
                src_system_type_id=system.type_id,
                dst_system_type_id=None,
                dst_usage_status_id=None,
            ):
                raise InvalidActionError("No rule found for deleting items from the current system")

        # First, attempt to delete any attachments and/or images that might be associated with this item.
        if config.object_storage.enabled:
            ObjectStorageAPIClient.delete_attachments(item_id, access_token)
            ObjectStorageAPIClient.delete_images(item_id, access_token)

        # Deleting could effect the number of spares of the catalogue item if this one is currently a spare
        with self._start_transaction_impacting_number_of_spares("deleting item", item.catalogue_item_id) as session:
            return self._item_repository.delete(item_id, session=session)

    def _handle_system_and_usage_status_id_update(
        self, item: ItemPatchSchema, stored_item: ItemOut, update_data: dict, moving_system: bool, is_authorised: bool
    ) -> None:
        """
        Handle an update request that could modify the `system_id` or `usage_status_id` of the item.

        Also inserts the new usage status value into `update_data` when updating the `usage_status_id`.

        :param item: Item containing the fields to be updated.
        :param stored_item: Current stored item from the database.
        :param update_data: Dictionary containing the update data.
        :raises InvalidActionError: If attempting to change the usage status without also moving the item between
                                    systems.
        :raises MissingRecordError: If the usage status doesn't exist.
        :raises MissingRecordError: If the system doesn't exist.
        :raises InvalidActionError: If moving the item between systems of different type and the moving rule doesn't
                                    exist.
        :raises InvalidActionError: If moving the item between systems of the same type and trying to change the usage
                                    status.
        """

        updating_usage_status = "usage_status_id" in update_data and item.usage_status_id != stored_item.usage_status_id

        usage_status_id = stored_item.usage_status_id
        if updating_usage_status:
            if not moving_system and not is_authorised:
                raise InvalidActionError(
                    "Cannot change usage status without moving between systems according to a defined rule"
                )

            usage_status_id = item.usage_status_id
            usage_status = self._usage_status_repository.get(usage_status_id)
            if not usage_status:
                raise MissingRecordError(f"No usage status found with ID: {usage_status_id}")
            update_data["usage_status"] = usage_status.value

        if moving_system:
            system = self._system_repository.get(item.system_id)
            if not system:
                raise MissingRecordError(f"No system found with ID: {item.system_id}")

            current_system = self._system_repository.get(stored_item.system_id)

            # Bypass rule check if authorised
            if current_system.type_id != system.type_id and not is_authorised:
                # System type is changing - Ensure the moving operation is allowed by a rule
                if not self._rule_repository.check_exists(
                    src_system_type_id=current_system.type_id,
                    dst_system_type_id=system.type_id,
                    dst_usage_status_id=usage_status_id,
                ):
                    raise InvalidActionError(
                        "No rule found for moving between the given system's types with the same final usage status"
                    )
            elif updating_usage_status and not is_authorised:
                # When system type is not changing - Ensure the usage status is unchanged
                raise InvalidActionError(
                    "Cannot change usage status of an item when moving between two systems of the same type"
                )

    def _handle_properties_update(self, item: ItemPatchSchema, stored_item: ItemOut, update_data: dict) -> None:
        """
        Handle an update request that modifies the `properties` of the item.

        Also inserts the new properties value into `update_data` when updating the `properties`.

        :param item: Item containing the fields to be updated.
        :param stored_item: Current stored item from the database.
        :param update_data: Dictionary containing the update data.
        :raises DatabaseIntegrityError: If the catalogue category of the catalogue item doesn't exist.
        """

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
        self, action_description: str, catalogue_item_id: str, dest_system_id: Optional[str] = None
    ) -> Generator[Optional[ClientSession], None, None]:
        """
        Handles recalculation of the `number_of_spares` field of a catalogue item for updates that will impact it but
        only when there is a spares definition is set.

        When necessary, starts a MongoDB session and transaction, then write locks the catalogue item before yielding to
        allow an update to take place using the returned session. Once any tasks using the session context have finished
        it will finish by recalculating the number of spares for the catalogue item before finishing the transaction.
        This write lock prevents similar actions from occurring during the update to prevent an incorrect update e.g. if
        another item was added between counting the documents and then updating the `number_of_spares` field it would
        cause a miscount. It also ensures any action executed using the session will either fail or succeed with the
        spares update.

        :param action_description: Description of what the contents of the transaction is doing so it can be used in
                                   any logging or raise errors.
        :param catalogue_item_id: ID of the effected catalogue item which will need its `number_of_spares` field
                                  updating.
        :param dest_system_id: ID of the system being put in/moved to (if applicable). Will be write locked to prevent
                               editing of system type after counting spares to avoid miscounts.
        """

        # Use ObjectIDs from here on to avoid unnecessary conversions particularly for when we set the spares definition
        catalogue_item_id = CustomObjectId(catalogue_item_id)

        # Firstly obtain the spares definition to figure out if it is defined or not
        spares_definition = self._setting_repository.get(SparesDefinitionOut)

        if spares_definition is None:
            # No session/transaction is needed as there is no spares update to perform
            yield None
        else:
            # Particularly when creating multiple items within the same catalogue item in quick succession, multiple
            # conflicting requests can occur. To reduce the chances we retry such requests so that the default 5ms
            # transaction timeout is less of an issue.
            start_time = time.time()
            retry = True
            while retry:
                try:
                    with start_session_transaction(action_description) as session:
                        # Write lock the catalogue item to prevent any other updates from occurring during the rest of
                        # the transaction
                        self._catalogue_item_repository.update_number_of_spares(
                            catalogue_item_id, None, session=session
                        )

                        # Write lock the destination system
                        # This will prevent the case where a system has no items currently, allowing the system type to
                        # be modified after the count but before the update finishes and instead force conflicts with
                        # system type modifications.
                        if dest_system_id:
                            self._system_repository.write_lock(dest_system_id, session)

                        # Allow any other updates to occur using the same session
                        yield session

                        # Obtain and update the number of spares
                        logger.info("Updating the number of spares of the catalogue item with ID %s", catalogue_item_id)
                        number_of_spares = self._item_repository.count_in_catalogue_item_with_system_type_one_of(
                            catalogue_item_id,
                            [CustomObjectId(system_type.id) for system_type in spares_definition.system_types],
                            session=session,
                        )
                        self._catalogue_item_repository.update_number_of_spares(
                            catalogue_item_id, number_of_spares, session=session
                        )
                        retry = False
                except WriteConflictError as exc:
                    # Keep retrying, but only if we have been retrying for less than 5 seconds so we dont let the
                    # request take too long and leave potential for it to block other requests if the threadpool is full
                    if time.time() - start_time > 5:
                        raise exc
                    # Wait some random time as there is no point in retrying immediately if we are already write
                    # locked. Between 10ms and 50ms.
                    time.sleep(random.uniform(0.01, 0.05))
