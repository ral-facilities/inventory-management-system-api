"""
Module for providing a service for managing catalogue categories using the `CatalogueCategoryRepo` repository.
"""

import logging
from typing import Annotated, Any, List, Optional

from fastapi import Depends

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    LeafCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import (
    CatalogueCategoryIn,
    CatalogueCategoryOut,
)
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.unit import UnitRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.catalogue_category import (
    CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS,
    CatalogueCategoryPatchRequestSchema,
    CatalogueCategoryPostRequestPropertySchema,
    CatalogueCategoryPostRequestSchema,
)
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class CatalogueCategoryService:
    """
    Service for managing catalogue categories.
    """

    def __init__(
        self,
        catalogue_category_repository: Annotated[CatalogueCategoryRepo, Depends(CatalogueCategoryRepo)],
        unit_repository: Annotated[UnitRepo, Depends(UnitRepo)],
    ) -> None:
        """
        Initialise the `CatalogueCategoryService` with a `CatalogueCategoryRepo` and `UnitRepo` repository.

        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param unit_repository: The `UnitRepo` repository to use.
        """
        self._catalogue_category_repository = catalogue_category_repository
        self._unit_repository = unit_repository

    def create(self, catalogue_category: CatalogueCategoryPostRequestSchema) -> CatalogueCategoryOut:
        """
        Create a new catalogue category.

        The method checks if the parent catalogue is a leaf catalogue category and raises a `LeafCategoryError` if it
        is.

        :param catalogue_category: The catalogue category to be created.
        :return: The created catalogue category.
        :raises LeafCategoryError: If the parent catalogue category is a leaf catalogue category.
        """
        parent_id = catalogue_category.parent_id
        parent_catalogue_category = self.get(parent_id) if parent_id else None

        if parent_catalogue_category and parent_catalogue_category.is_leaf:
            raise LeafCategoryError("Cannot add catalogue category to a leaf parent catalogue category")

        catalogue_item_properties = []
        if catalogue_category.catalogue_item_properties:
            utils.check_duplicate_catalogue_item_property_names(catalogue_category.catalogue_item_properties)

            catalogue_item_properties = self._add_catalogue_item_property_unit_values(
                catalogue_category.catalogue_item_properties
            )

        code = utils.generate_code(catalogue_category.name, "catalogue category")

        return self._catalogue_category_repository.create(
            CatalogueCategoryIn(
                **{
                    **catalogue_category.model_dump(),
                    "catalogue_item_properties": catalogue_item_properties,
                    "code": code,
                }
            )
        )

    def delete(self, catalogue_category_id: str) -> None:
        """
        Delete a catalogue category by its ID.

        :param catalogue_category_id: The ID of the catalogue category to delete.
        """
        return self._catalogue_category_repository.delete(catalogue_category_id)

    def get(self, catalogue_category_id: str) -> Optional[CatalogueCategoryOut]:
        """
        Retrieve a catalogue category by its ID.

        :param catalogue_category_id: The ID of the catalogue category to retrieve.
        :return: The retrieved catalogue category, or `None` if not found.
        """
        return self._catalogue_category_repository.get(catalogue_category_id)

    def get_breadcrumbs(self, catalogue_category_id: str) -> BreadcrumbsGetSchema:
        """
        Retrieve the breadcrumbs for a specific catalogue category

        :param catalogue_category_id: ID of the system to retrieve breadcrumbs for
        :return: Breadcrumbs
        """
        return self._catalogue_category_repository.get_breadcrumbs(catalogue_category_id)

    def list(self, parent_id: Optional[str]) -> List[CatalogueCategoryOut]:
        """
        Retrieve catalogue categories based on the provided filters.

        :param parent_id: The parent_id to filter catalogue categories by.
        :return: A list of catalogue categories, or an empty list if no catalogue categories are retrieved.
        """
        return self._catalogue_category_repository.list(parent_id)

    def update(
        self, catalogue_category_id: str, catalogue_category: CatalogueCategoryPatchRequestSchema
    ) -> CatalogueCategoryOut:
        """
        Update a catalogue category by its ID.

        The method checks if a catalogue category with such ID exists and raises a `MissingRecordError` if it doesn't
        exist. If a category is attempted to be moved to a leaf parent catalogue category then it checks if the parent
        is a leaf catalogue category and raises a `LeafCategoryError` if it is.

        :param catalogue_category_id: The ID of the catalogue category to update.
        :param catalogue_category: The catalogue category containing the fields that need to be updated.
        :return: The updated catalogue category.
        :raises ChildElementsExistError: If the catalogue category has child elements and attempting to update
                                    either any of the disallowed properties (is_leaf or catalogue_item_properties)
        :raises MissingRecordError: If the catalogue category doesn't exist.
        :raises LeafCategoryError: If the parent catalogue category to which the catalogue category is attempted to be
            moved is a leaf catalogue category.
        """
        update_data = catalogue_category.model_dump(exclude_unset=True)

        stored_catalogue_category = self.get(catalogue_category_id)
        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        # If any of these, need to ensure the category has no child elements
        if any(key in update_data for key in CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS):
            if self._catalogue_category_repository.has_child_elements(CustomObjectId(catalogue_category_id)):
                raise ChildElementsExistError(
                    f"Catalogue category with ID {str(catalogue_category_id)} has child elements and cannot be updated"
                )

        if "name" in update_data and catalogue_category.name != stored_catalogue_category.name:
            update_data["code"] = utils.generate_code(catalogue_category.name, "catalogue category")

        if "parent_id" in update_data and catalogue_category.parent_id != stored_catalogue_category.parent_id:
            parent_catalogue_category = self.get(catalogue_category.parent_id) if catalogue_category.parent_id else None

            if parent_catalogue_category and parent_catalogue_category.is_leaf:
                raise LeafCategoryError("Cannot add catalogue category to a leaf parent catalogue category")

        if catalogue_category.catalogue_item_properties:
            utils.check_duplicate_catalogue_item_property_names(catalogue_category.catalogue_item_properties)

            catalogue_item_properties = self._add_catalogue_item_property_unit_values(
                catalogue_category.catalogue_item_properties
            )
            update_data["catalogue_item_properties"] = catalogue_item_properties

        return self._catalogue_category_repository.update(
            catalogue_category_id, CatalogueCategoryIn(**{**stored_catalogue_category.model_dump(), **update_data})
        )

    def _add_catalogue_item_property_unit_values(
        self,
        catalogue_item_properties: List[CatalogueCategoryPostRequestPropertySchema],
    ) -> List[dict[str, Any]]:
        """
        Adds the unit values to the catalogue item properties based on the provided unit IDs.

        :param catalogue_item_properties: List of catalogue item properties to which unit values will be added.
        :return: List of catalogue item properties with unit values added.
        :raises MissingRecordError: If a unit with the specified ID is not found.
        """
        logger.info("Adding unit values to the catalogue item properties")
        catalogue_item_properties_with_units = []
        for catalogue_item_property in catalogue_item_properties:
            if catalogue_item_property.unit_id is not None:
                unit = self._unit_repository.get(catalogue_item_property.unit_id)
                if not unit:
                    raise MissingRecordError(f"No unit found with ID: {catalogue_item_property.unit_id}")

                # Copy unit value to catalogue item property
                catalogue_item_properties_with_units.append(
                    {**catalogue_item_property.model_dump(), "unit": unit.value}
                )
            else:
                catalogue_item_properties_with_units.append({**catalogue_item_property.model_dump(), "unit": None})
        return catalogue_item_properties_with_units
