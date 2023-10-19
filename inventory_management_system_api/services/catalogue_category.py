"""
Module for providing a service for managing catalogue categories using the `CatalogueCategoryRepo` repository.
"""
import logging
from typing import List, Optional

from fastapi import Depends

from inventory_management_system_api.core.exceptions import LeafCategoryError, MissingRecordError
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPatchRequestSchema,
    CatalogueCategoryPostRequestSchema,
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
        parent_path = parent_catalogue_category.path if parent_catalogue_category else "/"

        if parent_catalogue_category and parent_catalogue_category.is_leaf:
            raise LeafCategoryError("Cannot add catalogue category to a leaf parent catalogue category")

        code = utils.generate_code(catalogue_category.name, "catalogue category")
        path = utils.generate_path(parent_path, code, "catalogue category")
        return self._catalogue_category_repository.create(
            CatalogueCategoryIn(
                name=catalogue_category.name,
                code=code,
                is_leaf=catalogue_category.is_leaf,
                path=path,
                parent_path=parent_path,
                parent_id=catalogue_category.parent_id,
                catalogue_item_properties=catalogue_category.catalogue_item_properties,
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

    def list(self, path: Optional[str], parent_path: Optional[str]) -> List[CatalogueCategoryOut]:
        """
        Retrieve catalogue categories based on the provided filters.

        :param path: The path to filter catalogue categories by.
        :param parent_path: The parent path to filter catalogue categories by.
        :return: A list of catalogue categories, or an empty list if no catalogue categories are retrieved.
        """
        return self._catalogue_category_repository.list(path, parent_path)

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
        """
        update_data = catalogue_category.dict(exclude_unset=True)

        stored_catalogue_category = self.get(catalogue_category_id)
        if not stored_catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        if "name" in update_data and catalogue_category.name != stored_catalogue_category.name:
            update_data["code"] = utils.generate_code(catalogue_category.name, "catalogue category")
            update_data["path"] = utils.generate_path(
                stored_catalogue_category.parent_path, update_data["code"], "catalogue category"
            )

        if "parent_id" in update_data and catalogue_category.parent_id != stored_catalogue_category.parent_id:
            parent_catalogue_category = self.get(catalogue_category.parent_id) if catalogue_category.parent_id else None
            update_data["parent_path"] = parent_catalogue_category.path if parent_catalogue_category else "/"
            code = update_data["code"] if "code" in update_data else stored_catalogue_category.code
            update_data["path"] = utils.generate_path(update_data["parent_path"], code, "catalogue category")

            if parent_catalogue_category and parent_catalogue_category.is_leaf:
                raise LeafCategoryError("Cannot add catalogue category to a leaf parent catalogue category")

        stored_catalogue_category = stored_catalogue_category.copy(update=update_data)
        return self._catalogue_category_repository.update(
            catalogue_category_id, CatalogueCategoryIn(**stored_catalogue_category.dict())
        )
