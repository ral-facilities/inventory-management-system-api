"""
Module for providing a repository for managing catalogue categories in a MongoDB database.
"""

import logging
from typing import List, Optional

from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    DuplicateRecordError,
    InvalidActionError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.repositories import utils
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema

logger = logging.getLogger()


class CatalogueCategoryRepo:
    """
    Repository for managing catalogue categories in a MongoDB database.
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialize the `CatalogueCategoryRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._catalogue_categories_collection: Collection = self._database.catalogue_categories
        self._catalogue_items_collection: Collection = self._database.catalogue_items

    def create(self, catalogue_category: CatalogueCategoryIn) -> CatalogueCategoryOut:
        """
        Create a new catalogue category in a MongoDB database.

        If a parent catalogue category is specified by `parent_id`, the method checks if that exists
        in the database and raises a `MissingRecordError` if it doesn't exist. It also checks if a duplicate catalogue
        category is found within the parent catalogue category and raises a `DuplicateRecordError` if it is.

        :param catalogue_category: The catalogue category to be created.
        :return: The created catalogue category.
        :raises MissingRecordError: If the parent catalogue category specified by `parent_id` doesn't exist.
        :raises DuplicateRecordError: If a duplicate catalogue category is found within the parent catalogue category.
        """
        parent_id = str(catalogue_category.parent_id) if catalogue_category.parent_id else None
        if parent_id and not self.get(parent_id):
            raise MissingRecordError(f"No parent catalogue category found with ID: {parent_id}")

        if self._is_duplicate_catalogue_category(parent_id, catalogue_category.code):
            raise DuplicateRecordError("Duplicate catalogue category found within the parent catalogue category")

        logger.info("Inserting the new catalogue category into the database")
        result = self._catalogue_categories_collection.insert_one(catalogue_category.model_dump())
        catalogue_category = self.get(str(result.inserted_id))
        return catalogue_category

    def delete(self, catalogue_category_id: str) -> None:
        """
        Delete a catalogue category by its ID from a MongoDB database.

        The method checks if the catalogue category has child elements and raises a `ChildElementsExistError` if it
        does.

        :param catalogue_category_id: The ID of the catalogue category to delete.
        :raises ChildElementsExistError: If the catalogue category has child elements.
        :raises MissingRecordError: If the catalogue category doesn't exist.
        """
        catalogue_category_id = CustomObjectId(catalogue_category_id)
        if self.has_child_elements(catalogue_category_id):
            raise ChildElementsExistError(
                f"Catalogue category with ID {str(catalogue_category_id)} has child elements and cannot be deleted"
            )

        logger.info("Deleting catalogue category with ID: %s from the database", catalogue_category_id)
        result = self._catalogue_categories_collection.delete_one({"_id": catalogue_category_id})
        if result.deleted_count == 0:
            raise MissingRecordError(f"No catalogue category found with ID: {str(catalogue_category_id)}")

    def get(self, catalogue_category_id: str) -> Optional[CatalogueCategoryOut]:
        """
        Retrieve a catalogue category by its ID from a MongoDB database.

        :param catalogue_category_id: The ID of the catalogue category to retrieve.
        :return: The retrieved catalogue category, or `None` if not found.
        """
        catalogue_category_id = CustomObjectId(catalogue_category_id)
        logger.info("Retrieving catalogue category with ID: %s from the database", catalogue_category_id)
        catalogue_category = self._catalogue_categories_collection.find_one({"_id": catalogue_category_id})
        if catalogue_category:
            return CatalogueCategoryOut(**catalogue_category)
        return None

    def get_breadcrumbs(self, catalogue_category_id: str) -> BreadcrumbsGetSchema:
        """
        Retrieve the breadcrumbs for a specific catalogue category

        :param catalogue_category_id: ID of the catalogue category to retrieve breadcrumbs for
        :return: Breadcrumbs
        """
        logger.info("Querying breadcrumbs for catalogue category with id '%s'", catalogue_category_id)
        return utils.compute_breadcrumbs(
            list(
                self._catalogue_categories_collection.aggregate(
                    utils.create_breadcrumbs_aggregation_pipeline(
                        entity_id=catalogue_category_id, collection_name="catalogue_categories"
                    )
                )
            ),
            entity_id=catalogue_category_id,
            collection_name="catalogue_categories",
        )

    def update(self, catalogue_category_id: str, catalogue_category: CatalogueCategoryIn) -> CatalogueCategoryOut:
        """
        Update a catalogue category by its ID in a MongoDB database.

        The method checks if the catalogue category has child elements and raises a `ChildElementsExistError` if it
        does. If a parent catalogue category is specified by `parent_id`, the method checks if that exists in the
        database and raises a `MissingRecordError` if it doesn't exist. It also checks if a duplicate catalogue category
        is found within the parent catalogue category and raises a `DuplicateRecordError` if it is.

        :param catalogue_category_id: The ID of the catalogue category to update.
        :param catalogue_category: The catalogue category containing the update data.
        :return: The updated catalogue category.
        :raises MissingRecordError: If the parent catalogue category specified by `parent_id` doesn't exist.
        :raises DuplicateRecordError: If a duplicate catalogue category is found within the parent catalogue category.
        :raises InvalidActionError: If attempting to change the `parent_id` to one of its own child catalogue category
                                    ids.
        """
        catalogue_category_id = CustomObjectId(catalogue_category_id)

        parent_id = str(catalogue_category.parent_id) if catalogue_category.parent_id else None
        if parent_id and not self.get(parent_id):
            raise MissingRecordError(f"No parent catalogue category found with ID: {parent_id}")

        stored_catalogue_category = self.get(str(catalogue_category_id))
        moving_catalogue_category = parent_id != stored_catalogue_category.parent_id
        if (
            catalogue_category.name != stored_catalogue_category.name or moving_catalogue_category
        ) and self._is_duplicate_catalogue_category(parent_id, catalogue_category.code):
            raise DuplicateRecordError("Duplicate catalogue category found within the parent catalogue category")

        # Prevent a catalogue category from being moved to one of its own children
        if moving_catalogue_category:
            if parent_id is not None and not utils.is_valid_move_result(
                list(
                    self._catalogue_categories_collection.aggregate(
                        utils.create_move_check_aggregation_pipeline(
                            entity_id=str(catalogue_category_id),
                            destination_id=parent_id,
                            collection_name="catalogue_categories",
                        )
                    )
                )
            ):
                raise InvalidActionError("Cannot move a catalogue category to one of its own children")

        logger.info("Updating catalogue category with ID: %s in the database", catalogue_category_id)
        self._catalogue_categories_collection.update_one(
            {"_id": catalogue_category_id}, {"$set": catalogue_category.model_dump()}
        )
        catalogue_category = self.get(str(catalogue_category_id))
        return catalogue_category

    def list(self, parent_id: Optional[str]) -> List[CatalogueCategoryOut]:
        """
        Retrieve catalogue categories from a MongoDB database based on the provided filters.

        :param parent_id: The parent_id to filter catalogue categories by.
        :return: A list of catalogue categories, or an empty list if no catalogue categories are returned by the
                 database.
        """
        query = utils.list_query(parent_id, "catalogue categories")

        catalogue_categories = self._catalogue_categories_collection.find(query)
        return [CatalogueCategoryOut(**catalogue_category) for catalogue_category in catalogue_categories]

    def _is_duplicate_catalogue_category(self, parent_id: Optional[str], code: str) -> bool:
        """
        Check if a catalogue category with the same code already exists within the parent category.

        :param parent_id: The ID of the parent catalogue category which can also be `None`.
        :param code: The code of the catalogue category to check for duplicates.
        :return: `True` if a duplicate catalogue category code is found, `False` otherwise.
        """
        logger.info("Checking if catalogue category with code '%s' already exists within the parent category", code)
        if parent_id:
            parent_id = CustomObjectId(parent_id)

        return self._catalogue_categories_collection.find_one({"parent_id": parent_id, "code": code}) is not None

    def has_child_elements(self, catalogue_category_id: CustomObjectId) -> bool:
        """
        Check if a catalogue category has child elements based on its ID.

        Child elements in this case means whether a catalogue category has child catalogue categories or catalogue
        items.

        :param catalogue_category_id: The ID of the catalogue category to check.
        :return: True if the catalogue category has child elements, False otherwise.
        """
        logger.info("Checking if catalogue category with ID '%s' has children elements", catalogue_category_id)

        return (
            self._catalogue_categories_collection.find_one({"parent_id": catalogue_category_id}) is not None
            or self._catalogue_items_collection.find_one({"catalogue_category_id": catalogue_category_id}) is not None
        )
