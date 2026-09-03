"""
Module providing a migration that fixes any incorrect property IDs that were reintroduced by the equation related
fields migration.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration


class Migration(BaseMigration):
    """Migration that fixes any incorrect property IDs that were reintroduced by the equation related fields
    migration"""

    description = "Fixes any incorrect property ids that were reintroduced by the equation related fields migration"

    def __init__(self, database: Database):
        self._catalogue_categories_collection: Collection = database.catalogue_categories
        self._catalogue_items_collection: Collection = database.catalogue_items
        self._items_collection: Collection = database.items

    def forward(self, session: ClientSession):
        """Applies database changes."""

        # Find those using id instead of _id
        update_filter = {"properties.id": {"$exists": True}}
        # Property IDs are nested in an array so can't just use $rename
        update = [
            {
                "$set": {
                    "properties": {
                        "$map": {
                            "input": "$properties",
                            "as": "property",
                            "in": {"$mergeObjects": ["$$property", {"_id": "$$property.id"}]},
                        }
                    }
                }
            },
            {"$unset": "properties.id"},
        ]

        self._catalogue_categories_collection.update_many(update_filter, update, session=session)
        self._catalogue_items_collection.update_many(update_filter, update, session=session)
        self._items_collection.update_many(update_filter, update, session=session)

    def backward(self, session: ClientSession):
        """Reverses database changes."""
