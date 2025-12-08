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

# Aggregation pipeline for getting the spares definition complete with system type data
SPARES_DEFINITION_GET_AGGREGATION_PIPELINE = [
    {"$match": {"_id": SparesDefinitionOut.SETTING_ID}},
    {
        "$lookup": {
            "from": "system_types",
            "localField": "system_type_ids",
            "foreignField": "_id",
            "as": "system_types",
        }
    },
    {"$project": {"system_types": 1}},
]

# Template type for models inheriting from SettingIn/OutBase so this repo can be used generically for multiple settings
SettingInBaseT = TypeVar("SettingInBaseT", bound=SettingInBase)
SettingOutBaseT = TypeVar("SettingOutBaseT", bound=SettingOutBase)


class SettingRepo:
    """
    Repository for managing settings in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialise the `SettingRepo` with a MongoDB database instance.

        :param database: Database to use.
        """
        self._database = database
        self._settings_collection: Collection = self._database.settings

    def upsert(
        self, setting: SettingInBaseT, out_model_type: Type[SettingOutBaseT], session: Optional[ClientSession] = None
    ) -> SettingOutBaseT:
        """
        Update or insert a setting in a MongoDB database depending on whether it already exists.

        :param setting: Setting containing the fields to be updated. Also contains the ID for lookup.
        :param out_model_type: Output type of the setting's model.
        :param session: PyMongo ClientSession to use for database operations.
        :return: The updated setting.
        """

        logger.info("Assigning setting with ID '%s' in the database", setting.SETTING_ID)
        self._settings_collection.update_one(
            {"_id": setting.SETTING_ID}, {"$set": setting.model_dump()}, upsert=True, session=session
        )
        return self.get(out_model_type, session=session)

    def get(
        self, out_model_type: Type[SettingOutBaseT], session: Optional[ClientSession] = None
    ) -> Optional[SettingOutBaseT]:
        """
        Retrieve a setting from a MongoDB database.

        :param out_model_type: Output type of the setting's model. Also contains the ID for the lookup.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Retrieved setting or `None` if not found.
        """

        setting = None
        logger.info("Retrieving setting with ID '%s' from the database", out_model_type.SETTING_ID)

        # Check for any special cases that are not typical find_one queries
        if out_model_type is SparesDefinitionOut:
            # The spares definition contains a list of system type ids - use an aggregate query here to obtain the
            # actual system type entities instead of just their IDs
            result = self._settings_collection.aggregate(SPARES_DEFINITION_GET_AGGREGATION_PIPELINE, session=session)
            result = list(result)
            if len(result) > 0:
                setting = result[0]
        else:
            setting = self._settings_collection.find_one({"_id": out_model_type.SETTING_ID}, session=session)

        if setting:
            return out_model_type(**setting)
        return None
