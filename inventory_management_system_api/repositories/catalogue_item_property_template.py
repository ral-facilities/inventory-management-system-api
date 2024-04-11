"""
Module for providing a repository for managing catalogue item property templates in a MongoDB database
"""

import logging
from fastapi import Depends
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.models.catalogue_item_property_template import CatalogueItemPropertyTemplateOut

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
