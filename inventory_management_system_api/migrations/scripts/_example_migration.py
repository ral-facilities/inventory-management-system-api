"""
Module providing an example migration that does nothing
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=duplicate-code

import logging
from typing import Collection

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration

logger = logging.getLogger()


class Migration(BaseMigration):
    """Example migration that does nothing"""

    description = "Example migration that does nothing"

    def __init__(self, database: Database):
        """Obtain any collections required for the migration here e.g."""

        self._units_collection: Collection = database.units

    def forward(self, session: ClientSession):
        """This function should actually perform the migration

        All database functions should be given the session in order to ensure all updates are done within a transaction
        """

        # Perform any database updates here

        # Example: for renaming a field
        # self._units_collection.update_many(
        #     {}, {"$rename": {"value": "renamed_value"}}, session=session
        # )

        # Example: for adding a field
        # self._units_collection.update_many(
        #     {}, {"$set": {"new_field": "default_value"}}, session=session
        # )

        logger.info("example_migration forward migration (that does nothing)")

    def backward(self, session: ClientSession):
        """This function should reverse the migration

        All database functions should be given the session in order to ensure all updates are done within a transaction
        """

        # Perform any database updates here

        # Example: for renaming a field
        # self._units_collection.update_many(
        #     {}, {"$rename": {"renamed_value": "value"}}, session=session
        # )

        # Example: for adding a field
        # self._units_collection.update_many(
        #     {}, {"$unset": {"new_field": ""}}, session=session
        # )

        logger.info("example_migration backward migration (that does nothing)")
