"""
Module for providing a service for managing catalogue categories using the `CatalogueCategoryRepo` repository.
"""
import logging
from typing import List, Optional

from fastapi import Depends

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    ChildrenElementsExistError,
    DuplicatePropertyName,
    LeafCategoryError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.catalogue_category import (
    CATALOGUE_CATEGORY_WITH_CHILDREN_NON_EDITABLE_FIELDS,
    CatalogueCategoryPatchRequestSchema,
    CatalogueCategoryPostRequestSchema,
    CatalogueItemPropertySchema,
)
from inventory_management_system_api.services import utils


logger = logging.getLogger()


class CatalogueCategoryService:
    """
    Service for managing catalogue categories.
    """

    def __init__(self, catalogue_category_repository: CatalogueCategoryRepo = Depends(CatalogueCategoryRepo)) -> None:
        """
        Initialise the `CatalogueCategoryService` with a `CatalogueCategoryRepo` repository.

        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        """
        self._catalogue_category_repository = catalogue_category_repository

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

        self.check_duplicate_property_names(
            catalogue_category.catalogue_item_properties if catalogue_category.catalogue_item_properties else [], "post"
        )

        code = utils.generate_code(catalogue_category.name, "catalogue category")
        return self._catalogue_category_repository.create(
            CatalogueCategoryIn(**catalogue_category.model_dump(), code=code)
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
        :raises MissingRecordError: If the catalogue category doesn't exist.
        :raises LeafCategoryError: If the parent catalogue category to which the catalogue category is attempted to be
            moved is a leaf catalogue category.
        :raises ChildrenElementsExistError: If the catalogue category has child elements and attempting to update
                                    either any of the disallowed properties (is_leaf or catalogue_item_properties)
        """
        update_data = catalogue_category.model_dump(exclude_unset=True)

        stored_catalogue_category = self.get(catalogue_category_id)

        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        if "name" in update_data and catalogue_category.name != stored_catalogue_category.name:
            update_data["code"] = utils.generate_code(catalogue_category.name, "catalogue category")

        if "parent_id" in update_data and catalogue_category.parent_id != stored_catalogue_category.parent_id:
            parent_catalogue_category = self.get(catalogue_category.parent_id) if catalogue_category.parent_id else None

            if parent_catalogue_category and parent_catalogue_category.is_leaf:
                raise LeafCategoryError("Cannot add catalogue category to a leaf parent catalogue category")

        if (
            "catalogue_item_properties" in update_data
            and catalogue_category.catalogue_item_properties != stored_catalogue_category.catalogue_item_properties
        ):
            self.check_duplicate_property_names(update_data["catalogue_item_properties"], "patch")

        # If any of these, need to ensure the category has no children
        if any(key in update_data for key in CATALOGUE_CATEGORY_WITH_CHILDREN_NON_EDITABLE_FIELDS):
            if self._catalogue_category_repository.has_child_elements(CustomObjectId(catalogue_category_id)):
                raise ChildrenElementsExistError(
                    f"Catalogue category with ID {str(catalogue_category_id)} has child elements and cannot be updated"
                )

        return self._catalogue_category_repository.update(
            catalogue_category_id, CatalogueCategoryIn(**{**stored_catalogue_category.model_dump(), **update_data})
        )

    def check_duplicate_property_names(self, properties: List[CatalogueItemPropertySchema], request: str):
        """
        Go through all the properties to check for any duplicate property names

        :param properties: The supplied properties when creating or editing a catalogue category
        :param request: Which request is being processed as the list of properties supplied have
                        different types/format
        :return: Returns true if any duplicate property names have been found
        """

        logger.info("Checking for duplicate property names")

        list_of_names = []

        if request == "post":
            for dictionary in properties:
                list_of_names.append(dictionary.name)

        if request == "patch":
            for dictionary in properties:
                for key, value in dictionary.items():
                    if key == "name":
                        list_of_names.append(value)

        unique_names = set()

        for name in list_of_names:
            if name.lower() in unique_names:
                raise DuplicatePropertyName(
                    f"Cannot have duplicate catalogue item property name: {name}"
                )
            unique_names.add(name.lower())
