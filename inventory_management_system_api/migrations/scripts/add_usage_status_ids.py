"""
Module providing a migration to add usage statuses, add usage_status_id to items converting and convert their
existing usage_status to a string value
"""

from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database

from inventory_management_system_api.migrations.migration import BaseMigration
from inventory_management_system_api.services import utils

old_usage_statuses = {0: "New", 1: "Used", 2: "In Use", 3: "Scrapped"}


class Migration(BaseMigration):
    """Migration to add usage statuses, add usage_status_id to items converting and convert their
    existing usage_status to a string value"""

    def __init__(self, database: Database):
        self._items_collection: Collection = database.items
        self._usage_status_collection: Collection = database.usage_statuses

    def forward(self, session: ClientSession):
        """Migrates items to have usage_status_id's"""

        # Add in old usage statuses while keeping track of their ids
        usage_statuses = {}
        for old_usage_status, old_usage_status_string in old_usage_statuses.items():
            # Insert and store in dict for looking up old usage status id
            result = self._usage_status_collection.insert_one(
                {
                    "value": old_usage_status_string,
                    "code": utils.generate_code(old_usage_status_string, "usage status"),
                },
                session=session,
            )
            usage_statuses[old_usage_status] = self._usage_status_collection.find_one(
                {"_id": result.inserted_id}, session=session
            )

        items = list(self._items_collection.find(session=session))
        for item in items:
            item["usage_status_id"] = usage_statuses[item["usage_status"]]["_id"]
            item["usage_status"] = usage_statuses[item["usage_status"]]["value"]

            self._items_collection.update_one({"_id": item["_id"]}, {"$set": item}, session=session)

    def backward(self, session: ClientSession):
        """Removes usage_status_id from items to undo the migration"""

        # Reverse the order of usage statuses
        usage_status_lookup = {
            old_usage_status_string: old_usage_status
            for old_usage_status, old_usage_status_string in old_usage_statuses.items()
        }

        items = list(self._items_collection.find(session=session))
        for item in items:
            del item["usage_status_id"]
            item["usage_status"] = usage_status_lookup[item["usage_status"]]

            self._items_collection.update_one({"_id": item["_id"]}, {"$set": item}, session=session)

        # Can't drop the collection during a transaction
        self._usage_status_collection.delete_many({}, session=session)

    def backward_after_transaction(self, session: ClientSession):
        """Drops the usage status collection"""
        # Cant drop inside transaction so do here
        self._usage_status_collection.drop(session=session)
