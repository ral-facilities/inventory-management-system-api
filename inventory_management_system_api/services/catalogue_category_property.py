"""
Module for providing a service for managing properties at the catalogue category level that may also require
propagation down through their child catalogue items and items using their respective repositories
"""

import logging
from typing import Optional

from fastapi import Depends

from inventory_management_system_api.core.database import mongodb_client
from inventory_management_system_api.core.exceptions import InvalidActionError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import (
    AllowedValues,
    CatalogueItemPropertyIn,
    CatalogueItemPropertyOut,
)
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.schemas.catalogue_category import (
    AllowedValuesSchema,
    CatalogueCategoryPostRequestPropertySchema,
    CatalogueItemPropertyPatchRequestSchema,
    CatalogueItemPropertyPostRequestSchema,
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
    ) -> CatalogueItemPropertyOut:
        """Create a new property at the catalogue category level

        Property will be propagated down through catalogue items and items when there are children.

        :param catalogue_category_id: ID of the catalogue category to add the property to
        :param catalogue_item_property: Property to add (with additional info on how to perform the migration if
                                        necessary)
        :raises InvalidActionError: If attempting to add a mandatory property without a default_value being specified
                                    or if the catalogue category is not a leaf
        :raises MissingRecordError: If the catalogue category doesn't exist
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

        # Run all subsequent edits within a transaction to ensure they will all succeed or fail together
        with mongodb_client.start_session() as session:
            with session.start_transaction():
                # Firstly update the catalogue category
                catalogue_item_property_out = self._catalogue_category_repository.create_catalogue_item_property(
                    catalogue_category_id, catalogue_item_property_in, session=session
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

        return catalogue_item_property_out

    def _check_valid_allowed_values_update(
        self, existing_allowed_values: Optional[AllowedValues], new_allowed_values: Optional[AllowedValuesSchema]
    ) -> None:
        """Validates a potential change of allowed_values

        :param existing_allowed_values: Existing allowed_values from the catalogue category database model
        :param new_allowed_values: New definition of allowed values to validate
        :raises InvalidActionError:
            - If the existing allowed_values is None and the new allowed_values is not
            - If the existing allowed_values is not None and the new allowed_values is
            - If the type of allowed values is being changed
            - If the type of allowed values is 'list' while modifying the list in any way other than adding extra
              values
        """
        # Prevent adding allowed_values to an existing property
        if existing_allowed_values is None and new_allowed_values is not None:
            raise InvalidActionError("Cannot add allowed_values to an existing catalogue item property")

        # Prevent removing allowed_values from an existing property
        if existing_allowed_values is not None and new_allowed_values is None:
            raise InvalidActionError("Cannot remove allowed_values from an existing catalogue item property")

        # Prevent changing an allowed_values' type
        if existing_allowed_values.type != new_allowed_values.type:
            raise InvalidActionError(
                "Cannot modify a catalogue item properties' allowed_values to have a different type"
            )

        # Ensure that a list type adds to the existing values (order doesn't matter)
        if existing_allowed_values.type == "list":
            for existing_value in existing_allowed_values.values:
                if existing_value not in new_allowed_values.values:
                    raise InvalidActionError(
                        "Cannot modify existing values inside allowed_values of type 'list', you may only add more "
                        "values"
                    )

    def update(
        self,
        catalogue_category_id: str,
        catalogue_item_property_id: str,
        catalogue_item_property: CatalogueItemPropertyPatchRequestSchema,
    ) -> CatalogueItemPropertyOut:
        """
        Update a property at the catalogue category level by its id

        Property changes will be propagated down through the catalogue items and items when required where there are
        children

        :param catalogue_category_id: The ID of the catalogue category to update
        :param catalogue_item_property_id: The ID of the catalogue item property within the category to update
        :param catalogue_item_property: The property values to update
        :raises MissingRecordError: If the catalogue category doesn't exist, or the catalogue item property doesn't
                                    exist within the specified catalogue category
        """

        update_data = catalogue_item_property.model_dump(exclude_unset=True)

        # Obtain the existing catalogue category to validate against
        stored_catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        # Attempt to locate the property
        existing_property_out: Optional[CatalogueItemPropertyOut] = None
        for prop in stored_catalogue_category.catalogue_item_properties:
            if prop.id == catalogue_item_property_id:
                existing_property_out = prop
                break

        if not existing_property_out:
            raise MissingRecordError(f"No catalogue item property found with ID: {catalogue_item_property_id}")

        # Modify the name if necessary and check it doesn't cause a conflict
        updating_name = "name" in update_data and update_data["name"] != existing_property_out.name
        if updating_name:
            existing_property_out.name = update_data["name"]
            utils.check_duplicate_catalogue_item_property_names(stored_catalogue_category.catalogue_item_properties)

        if "allowed_values" in update_data:
            self._check_valid_allowed_values_update(
                existing_property_out.allowed_values, catalogue_item_property.allowed_values
            )

        CatalogueCategoryPostRequestPropertySchema.check_valid_allowed_values(
            catalogue_item_property.allowed_values, existing_property_out.model_dump()
        )

        catalogue_item_property_in = CatalogueItemPropertyIn(**{**existing_property_out.model_dump(), **update_data})

        # Run all subsequent edits within a transaction to ensure they will all succeed or fail together
        with mongodb_client.start_session() as session:
            with session.start_transaction():
                # Firstly update the catalogue category
                catalogue_item_property_out = self._catalogue_category_repository.update_catalogue_item_property(
                    catalogue_category_id, catalogue_item_property_id, catalogue_item_property_in, session=session
                )

                # Avoid propagating changes unless absolutely necessary
                if updating_name:
                    self._catalogue_item_repository.update_names_of_all_properties_with_id(
                        catalogue_item_property_id, catalogue_item_property.name, session=session
                    )
                    self._item_repository.update_names_of_all_properties_with_id(
                        catalogue_item_property_id, catalogue_item_property.name, session=session
                    )

        return catalogue_item_property_out
