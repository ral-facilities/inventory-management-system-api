"""
Module for providing a repository for managing settings in a MongoDB database.
"""

import logging
from typing import Optional, Type, TypeVar

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.setting import SettingInBase, SettingOutBase, SparesDefinitionOut

logger = logging.getLogger()

# Template types for models inheriting from SettingIn/OutBase so this repo can be used generically for multiple settings
SettingInBaseT = TypeVar("SettingInBaseT", bound=SettingInBase)
SettingOutBaseT = TypeVar("SettingOutBaseT", bound=SettingOutBase)


# Aggregation pipeline for getting the spares definition complete with usage status data
SPARES_DEFINITION_GET_AGGREGATION_PIPELINE: list = [
    # Only perform this on the relevant document
    {"$match": {"_id": SparesDefinitionOut.SETTING_ID}},
    # Deconstruct the usage statuses so can go through them one by one
    {"$unwind": "$usage_statuses"},
    # Find and store actual usage status data as 'statusDetails'
    {
        "$lookup": {
            "from": "usage_statuses",
            "localField": "usage_statuses.id",
            "foreignField": "_id",
            "as": "statusDetails",
        }
    },
    {"$unwind": "$statusDetails"},
    # Merge the two sets of documents together
    {"$addFields": {"usage_statuses": {"$mergeObjects": ["$usage_statuses", "$statusDetails"]}}},
    # Remove the temporary 'statusDetails' field as no longer needed
    {"$unset": "statusDetails"},
    # Reconstruct the original document by merging with the original fields
    {
        "$group": {
            "_id": "$_id",
            "usage_statuses": {"$push": "$usage_statuses"},
            "otherFields": {"$first": "$$ROOT"},
        }
    },
    {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$otherFields", {"usage_statuses": "$usage_statuses"}]}}},
]


class SettingRepo:
    """
    Repository for managing settings in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialize the `SettingRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._settings_collection: Collection = self._database.settings

    def upsert(
        self, setting: SettingInBaseT, out_model_type: Type[SettingOutBaseT], session: ClientSession = None
    ) -> SettingOutBaseT:
        """
        Update or insert a setting in a MongoDB database depending on whether it already exists.

        :param setting: Setting containing the fields to be updated. Also contains the ID for lookup.
        :param out_model_type: The output type of the setting's model.
        :param session: PyMongo ClientSession to use for database operations.
        :return: The updated setting.
        """

        logger.info("Assigning setting with ID: %s in the database", setting.SETTING_ID)
        self._settings_collection.update_one(
            {"_id": setting.SETTING_ID}, {"$set": setting.model_dump(by_alias=True)}, upsert=True, session=session
        )

        return self.get(out_model_type=out_model_type, session=session)

    def get(self, out_model_type: Type[SettingOutBaseT], session: ClientSession = None) -> Optional[SettingOutBaseT]:
        """
        Retrieve a setting from a MongoDB database.

        :param out_model_type: The output type of the setting's model. Also contains the ID for lookup.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Retrieved setting or `None` if not found.
        """

        # First obtain the setting document
        setting = self._settings_collection.find_one({"_id": out_model_type.SETTING_ID}, session=session)

        # Now ensure the setting is actually assigned and doesn't just have a write `_lock` and `_id` fields
        if setting is None or (len(setting.keys()) == 2 and "_lock" in setting):
            return None

        if out_model_type is SparesDefinitionOut:
            # The spares definition contains a list of usage statuses - use an aggregate query here to obtain
            # the actual usage status entities instead of just their stored ID

            setting = list(
                self._settings_collection.aggregate(SPARES_DEFINITION_GET_AGGREGATION_PIPELINE, session=session)
            )[0]

        return out_model_type(**setting)

    def write_lock(self, out_model_type: Type[SettingOutBaseT], session: ClientSession) -> None:
        """
        Updates a field `_lock` inside a setting in the database to lock the document from further updates in other
        transactions.

        Will add the setting document if it doesn't already exist. To ensure it can still be locked if it hasn't
        ever been assigned a value before. (The get handles this case ensuring it still returns `None`.)

        :param out_model_type: The output type of the setting's model. Also contains the ID for lookup.
        :param session: PyMongo ClientSession to use for database operations.
        """
        self._settings_collection.update_one(
            {"_id": out_model_type.SETTING_ID}, {"$set": {"_lock": None}}, upsert=True, session=session
        )
