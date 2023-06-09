"""
Module for providing a repository for managing catalogue categories in a MongoDB database.
"""
import logging

from pymongo.collection import Collection

from inventory_management_system_api.core.database import db

logger = logging.getLogger()


class CatalogueCategoryRepo:
    """
    Repository for managing catalogue categories in a MongoDB database.
    """

    @property
    def _collection(self) -> Collection:
        return db.catalogue_categories
