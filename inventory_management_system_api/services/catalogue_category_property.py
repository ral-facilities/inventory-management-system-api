"""
Module for providing a service for managing properties at the catalogue category level that may also require
propagation down through their child catalogue items and items using their respective repositories
"""

from typing import Annotated, Optional

from fastapi import Depends

from inventory_management_system_api.core.database import start_session_transaction
from inventory_management_system_api.core.exceptions import InvalidActionError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import (
    AllowedValues,
    CatalogueCategoryPropertyIn,
    CatalogueCategoryPropertyOut,
)
from inventory_management_system_api.models.catalogue_item import PropertyIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.unit import UnitRepo
from inventory_management_system_api.schemas.catalogue_category import (
    AllowedValuesSchema,
    CatalogueCategoryPostPropertySchema,
    CatalogueCategoryPropertyPatchSchema,
    CatalogueCategoryPropertyPostSchema,
)
from inventory_management_system_api.services import utils


class CatalogueCategoryPropertyService:
    """
    Service for managing properties at the catalogue category level downwards
    """

    def __init__(
        self,
        catalogue_category_repository: Annotated[CatalogueCategoryRepo, Depends(CatalogueCategoryRepo)],
        catalogue_item_repository: Annotated[CatalogueItemRepo, Depends(CatalogueItemRepo)],
        item_repository: Annotated[ItemRepo, Depends(ItemRepo)],
        unit_repository: Annotated[UnitRepo, Depends(UnitRepo)],
    ):
        """
        Initialise the `PropertyService` with a `CatalogueCategoryRepo`, `CatalogueItemRepo`,
        `ItemRepo` and `UnitRepo` repos.

        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param item_repository: The `ItemRepo` repository to use.
        :param unit_repository: The `UnitRepo` repository to use.
        """
        self._catalogue_category_repository = catalogue_category_repository
        self._catalogue_item_repository = catalogue_item_repository
        self._item_repository = item_repository
        self._unit_repository = unit_repository

    def create(
        self,
        catalogue_category_id: str,
        catalogue_category_property: CatalogueCategoryPropertyPostSchema,
    ) -> CatalogueCategoryPropertyOut:
        """Create a new property at the catalogue category level

        Property will be propagated down through catalogue items and items when there are children.

        :param catalogue_category_id: ID of the catalogue category to add the property to
        :param catalogue_category_property: Property to add (with additional info on how to perform the migration if
                                        necessary)
        :raises InvalidActionError: If attempting to add a mandatory property without a default_value being specified
                                    or if the catalogue category is not a leaf
        :raises MissingRecordError: If the catalogue category doesn't exist
        :return: The created property as defined at the catalogue category level
        """

        # Mandatory properties must have a default value that is not None as they would need to be
        # populated down the subtree
        if catalogue_category_property.mandatory and catalogue_category_property.default_value is None:
            raise InvalidActionError("Cannot add a mandatory property without a default value")

        # Obtain the existing catalogue category to validate against
        stored_catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        # Must be a leaf catalogue category in order to have properties
        if not stored_catalogue_category.is_leaf:
            raise InvalidActionError("Cannot add a property to a non-leaf catalogue category")

        # Ensure the property is actually valid
        utils.check_duplicate_property_names(stored_catalogue_category.properties + [catalogue_category_property])

        unit_value = None
        if catalogue_category_property.unit_id is not None:
            # Obtain the specified unit value if a unit ID is given
            unit = self._unit_repository.get(catalogue_category_property.unit_id)
            if not unit:
                raise MissingRecordError(f"No unit found with ID: {catalogue_category_property.unit_id}")
            unit_value = unit.value

        catalogue_category_property_in = CatalogueCategoryPropertyIn(
            **{**catalogue_category_property.model_dump(), "unit": unit_value}
        )

        # Run all subsequent edits within a transaction to ensure they will all succeed or fail together
        with start_session_transaction("adding property") as session:
            # Firstly update the catalogue category
            catalogue_category_property_out = self._catalogue_category_repository.create_property(
                catalogue_category_id, catalogue_category_property_in, session=session
            )

            property_in = PropertyIn(
                id=str(catalogue_category_property_in.id),
                name=catalogue_category_property_in.name,
                value=catalogue_category_property.default_value,
                unit=unit_value,
                unit_id=catalogue_category_property.unit_id,
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

        return catalogue_category_property_out

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
        # Ignore checks if both existing and new allowed_values is None
        # (as there is no change)
        if existing_allowed_values is None and new_allowed_values is None:
            return

        # Prevent adding allowed_values to an existing property
        if existing_allowed_values is None and new_allowed_values is not None:
            raise InvalidActionError("Cannot add allowed_values to an existing property")

        # Prevent removing allowed_values from an existing property
        if existing_allowed_values is not None and new_allowed_values is None:
            raise InvalidActionError("Cannot remove allowed_values from an existing property")

        # Prevent changing an allowed_values' type
        if existing_allowed_values.type != new_allowed_values.type:
            raise InvalidActionError("Cannot modify a properties' allowed_values to have a different type")

        # Ensure that a list type adds to the existing values (order doesn't matter)
        if existing_allowed_values.type == "list":
            for existing_value in existing_allowed_values.values:
                if existing_value not in new_allowed_values.values:
                    raise InvalidActionError(
                        "Cannot modify existing values inside allowed_values of type 'list', you may only add more "
                        "values"
                    )

    # pylint:disable=too-many-locals
    def update(
        self,
        catalogue_category_id: str,
        catalogue_category_property_id: str,
        catalogue_category_property: CatalogueCategoryPropertyPatchSchema,
        is_authorised: bool,
    ) -> CatalogueCategoryPropertyOut:
        """
        Update a property at the catalogue category level by its id

        Property changes will be propagated down through the catalogue items and items when required where there are
        children

        :param catalogue_category_id: The ID of the catalogue category to update
        :param catalogue_category_property_id: The ID of the property within the category to update
        :param catalogue_category_property: The property values to update
        :param is_authorised: Whether or not the user is authorised to update a property's unit
        :raises MissingRecordError: If the catalogue category doesn't exist, or the property doesn't
                                    exist within the specified catalogue category
        """

        update_data = catalogue_category_property.model_dump(exclude_unset=True)

        # Obtain the existing catalogue category to validate against
        stored_catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        # Attempt to locate the property
        existing_property_out: Optional[CatalogueCategoryPropertyOut] = None
        for prop in stored_catalogue_category.properties:
            if prop.id == catalogue_category_property_id:
                existing_property_out = prop
                break

        if not existing_property_out:
            raise MissingRecordError(f"No property found with ID: {catalogue_category_property_id}")

        # Modify the name if necessary and check it doesn't cause a conflict
        updating_name = "name" in update_data and update_data["name"] != existing_property_out.name
        if updating_name:
            existing_property_out.name = update_data["name"]
            utils.check_duplicate_property_names(stored_catalogue_category.properties)

        if "allowed_values" in update_data:
            self._check_valid_allowed_values_update(
                existing_property_out.allowed_values, catalogue_category_property.allowed_values
            )

        # units of properties may only be updated by authorised users
        updating_unit = "unit_id" in update_data and update_data["unit_id"] != existing_property_out.unit_id
        if updating_unit:
            if not is_authorised:
                raise InvalidActionError("You are not able to change the unit of a property")
            unit_id = update_data["unit_id"]

            if not unit_id:
                update_data["unit"] = None
            else:
                unit = self._unit_repository.get(unit_id)
                if not unit:
                    raise MissingRecordError(f"No unit found with ID: {unit_id}")
                update_data["unit"] = unit.value

        CatalogueCategoryPostPropertySchema.check_valid_allowed_values(
            catalogue_category_property.allowed_values, existing_property_out.model_dump()
        )

        property_in = CatalogueCategoryPropertyIn(**{**existing_property_out.model_dump(), **update_data})

        # Run all subsequent edits within a transaction to ensure they will all succeed or fail together
        with start_session_transaction("updating property") as session:
            # Firstly update the catalogue category
            property_out = self._catalogue_category_repository.update_property(
                catalogue_category_id, catalogue_category_property_id, property_in, session=session
            )

            # Avoid propagating changes unless absolutely necessary
            if updating_name or (updating_unit and is_authorised):
                unit_data = (
                    {"unit_id": catalogue_category_property.unit_id, "unit": update_data.get("unit")}
                    if updating_unit
                    else None
                )

                self._catalogue_item_repository.update_names_and_units_of_all_properties_with_id(
                    catalogue_category_property_id,
                    catalogue_category_property.name,
                    unit_data,
                    session=session,
                )
                self._item_repository.update_names_and_units_of_all_properties_with_id(
                    catalogue_category_property_id,
                    catalogue_category_property.name,
                    unit_data,
                    session=session,
                )

        return property_out
