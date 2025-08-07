"""
Module for providing a repository for managing rules in a MongoDB database.
"""

from typing import Optional

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.rule import RuleOut


class RuleRepo:
    """
    Repository for managing rules in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialise the `RulesRepo` with a MongoDB database instance.

        :param database: Database to use.
        """
        self._database = database
        self._rules_collection: Collection = self._database.rules

    def list(self, session: Optional[ClientSession] = None) -> list[RuleOut]:
        """
        Retrieve rules from a MongoDB database based on the provided filters.

        :param session: PyMongo ClientSession to use for database operations.
        :return: List of rules or an empty list if no rules are retrieved.
        """
        rules = self._rules_collection.find({}, session=session)
        return [RuleOut(**rule) for rule in rules]
