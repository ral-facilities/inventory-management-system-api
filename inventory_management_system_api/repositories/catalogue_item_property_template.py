"""
Module for providing a repository for managing catalogue item property templates in a MongoDB database
"""

import logging
from typing import Optional
from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.core.exceptions import DuplicateRecordError
from inventory_management_system_api.models.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateIn,
    CatalogueItemPropertyTemplateOut,
)
from inventory_management_system_api.core.custom_object_id import CustomObjectId

logger = logging.getLogger()


class CatalogueItemPropertyTemplateRepo:
    """
    Repository for managing catalogue item property templates in a MongoDB database
    """

    def __init__(self, database: Database = Depends(get_database)) -> None:
        """
        Initialise the `CatalogueItemPropertyTemplateRepo` with a MongoDB database instance
        :param database: Database to use
        """
        self._database = database
        self._catalogue_item_property_templates_collection: Collection = (
            self._database.catalogue_item_property_templates
        )

    def create(
        self, catalogue_item_property_template: CatalogueItemPropertyTemplateIn
    ) -> CatalogueItemPropertyTemplateOut:
        """
        Create a new catalogue item property template in MongoDB database

        :param catalogue_item_property_template: The catalogue item property template to be created
        :return: The created catalogue item property template
        :raises DuplicateRecordError: If a duplicate catalogue item property template is found within collection
        """

        if self._is_duplicate_catalogue_item_property_template(catalogue_item_property_template.code):
            raise DuplicateRecordError("Duplicate catalogue item property template found")

        logger.info("Inserting new catalogue item property template into database")

        result = self._catalogue_item_property_templates_collection.insert_one(
            catalogue_item_property_template.model_dump()
        )
        catalogue_item_property_template = self.get(str(result.inserted_id))

        return catalogue_item_property_template

    def list(self) -> list[CatalogueItemPropertyTemplateOut]:
        """
        Retrieve catalogue item property templates from a MongoDB database
        :return: List of catalogue item property templates or an empty list if no catalogue item property
                 templates are retrieved.
        """
        catalogue_item_property_templates = self._catalogue_item_property_templates_collection.find()
        return [
            CatalogueItemPropertyTemplateOut(**catalogue_item_property_template)
            for catalogue_item_property_template in catalogue_item_property_templates
        ]

    def get(self, catalogue_item_property_template_id: str) -> Optional[CatalogueItemPropertyTemplateOut]:
        """
        Retrieve a catalogue item property template by its ID from a MongoDB database.

        :param catalogue_item_property_template_id: The ID of the catalogue item property template to retrieve.
        :return: The retrieved catalogue item property template, or `None` if not found.
        """
        catalogue_item_property_template_id = CustomObjectId(catalogue_item_property_template_id)
        logger.info(
            "Retrieving catalogue item property template with ID: %s from the database",
            catalogue_item_property_template_id,
        )
        catalogue_item_property_template = self._catalogue_item_property_templates_collection.find_one(
            {"_id": catalogue_item_property_template_id}
        )
        if catalogue_item_property_template:
            return CatalogueItemPropertyTemplateOut(**catalogue_item_property_template)
        return None

    def _is_duplicate_catalogue_item_property_template(self, code: str) -> bool:
        """
        Check if catalogue item property template with the same name already exists in the catalogue
        item property template collection

        :param code: The code of the catalogue item property template to check for duplicates.
        :return `True` if duplicate catalogue item property template, `False` otherwise
        """
        logger.info("Checking if catalogue item property template with code '%s' already exists", code)
        return self._catalogue_item_property_templates_collection.find_one({"code": code}) is not None
