"""
Module for providing a repository for managing rules in a MongoDB database.
"""

from typing import Optional

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.rule import RuleOut
from inventory_management_system_api.repositories import utils

# Aggregation pipeline stages for looking up the entities inside rules and inserting them into the retrieved documents
RULES_GET_AGGREGATION_PIPELINE_ENTITY_INSERT_STAGES = [
    # Obtain the system types and usage statuses
    {
        "$lookup": {
            "from": "system_types",
            "localField": "src_system_type_id",
            "foreignField": "_id",
            "as": "src_system_type",
        }
    },
    {
        "$lookup": {
            "from": "system_types",
            "localField": "dst_system_type_id",
            "foreignField": "_id",
            "as": "dst_system_type",
        }
    },
    {
        "$lookup": {
            "from": "usage_statuses",
            "localField": "dst_usage_status_id",
            "foreignField": "_id",
            "as": "dst_usage_status",
        }
    },
    # The above are returned as lists, unwind so they are a single value and ensure that where documents
    # have a value of `null` in the relevant field, the document is still retained
    {"$unwind": {"path": "$src_system_type", "preserveNullAndEmptyArrays": True}},
    {"$unwind": {"path": "$dst_system_type", "preserveNullAndEmptyArrays": True}},
    {"$unwind": {"path": "$dst_usage_status", "preserveNullAndEmptyArrays": True}},
]


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

    def list(
        self,
        src_system_type_id: Optional[str],
        dst_system_type_id: Optional[str],
        session: Optional[ClientSession] = None,
    ) -> list[RuleOut]:
        """
        Retrieve rules from a MongoDB database based on the provided filters.

        :param src_system_type_id: `src_system_type_id` to filter the rules by or `None`.
        :param dst_system_type_id: `dst_system_type_id` to filter the rules by or `None`.
        :param session: PyMongo ClientSession to use for database operations.
        :return: List of rules or an empty list if no rules are retrieved.
        """
        result = self._rules_collection.aggregate(
            [
                # Obtain just those matching the filters
                {
                    "$match": utils.list_query(
                        {"src_system_type_id": src_system_type_id, "dst_system_type_id": dst_system_type_id}, "rules"
                    )
                },
                # Lookup and insert system types and usage statuses
                *RULES_GET_AGGREGATION_PIPELINE_ENTITY_INSERT_STAGES,
            ],
            session=session,
        )
        rules = list(result)
        return [RuleOut(**rule) for rule in rules]
