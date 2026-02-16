"""
Module providing a migration that Adds modified_comment to all entries.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from typing import Collection
from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration


class Migration(BaseMigration):
    """Migration that Adds modified_comment to all entries"""

    description = "Adds modified_comment to all entries"

    def __init__(self, database: Database):
        self._catalouge_categories_collection: Collection = database.catalogue_categories
        self._catalogue_items_collection: Collection = database.catalogue_items
        self._items_collection: Collection = database.items
        self._manufacturers_collection: Collection = database.manufacturers
        self._systems_collection: Collection = database.systems
        self._units_collection: Collection = database.units
        self._usage_statuses_collection: Collection = database.usage_statuses
        
        self._collections = [
            self._catalouge_categories_collection,
            self._catalogue_items_collection,
            self._items_collection,
            self._manufacturers_collection,
            self._systems_collection,
            self._units_collection,
            self._usage_statuses_collection
        ]

    def forward(self, session: ClientSession):
        """Applies database changes."""
        
        
        for collection in self._collections:
            collection.update_many(
                {}, {"$set": {"modified_comment": None}}, session=session
            )

    def backward(self, session: ClientSession):
        """Reverses database changes."""
        
        for collection in self._collections:
            collection.update_many(
                {}, {"$unset": {"modified_comment": ""}}, session=session
            )
