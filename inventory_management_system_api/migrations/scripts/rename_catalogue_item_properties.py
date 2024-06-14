"""
Module providing a migration to rename catalogue_item_properties to properties
"""

from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration


class Migration(BaseMigration):
    """Migration to rename catalogue_item_properties to properties"""

    def __init__(self, database: Database):
        self._catalogue_categories_collection: Collection = database.catalogue_categories

    def forward(self, session: ClientSession):
        """Renames catalogue_item_properties to properties"""

        self._catalogue_categories_collection.update_many({}, {"$rename": {"catalogue_item_properties": "properties"}})

    def backward(self, session: ClientSession):
        """Renames properties to catalogue_item_properties"""

        self._catalogue_categories_collection.update_many({}, {"$rename": {"properties": "catalogue_item_properties"}})
