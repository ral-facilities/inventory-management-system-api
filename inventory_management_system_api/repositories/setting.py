"""
Module for providing a repository for managing settings in a MongoDB database.
"""

import logging
from typing import Optional, Type, TypeVar

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.setting import BaseSetting, SparesDefinitionOut

logger = logging.getLogger()

# Template type for models inheriting from BaseSetting so this repo can be used generically for multiple settings
TBaseSetting = TypeVar("TBaseSetting", bound=BaseSetting)


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

    def get(self, output_model_type: Type[TBaseSetting], session: ClientSession = None) -> Optional[TBaseSetting]:
        """
        Retrieve a setting from a MongoDB database.

        :param output_model_type: The output type of the setting's model. Also contains the ID for lookup.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Retrieved setting or `None` if not found.
        """

        if output_model_type is SparesDefinitionOut:
            # The spares definition contains a list of usage statuses - use an aggregate query here to obtain
            # the actual usage status entities instead of just their stored ID

            result = list(
                self._settings_collection.aggregate(
                    [
                        # Only perform this on the relevant document
                        {"$match": {"_id": output_model_type.SETTING_ID}},
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
                        {
                            "$replaceRoot": {
                                "newRoot": {"$mergeObjects": ["$otherFields", {"usage_statuses": "$usage_statuses"}]}
                            }
                        },
                    ]
                )
            )
            setting = result[0] if len(result) > 0 else None
        else:
            setting = self._settings_collection.find_one({"_id": output_model_type.SETTING_ID}, session=session)

        if setting:
            return output_model_type(**setting)
        return None

    def upsert(
        self, setting: BaseSetting, output_model_type: Type[TBaseSetting], session: ClientSession = None
    ) -> TBaseSetting:
        """
        Assign a setting a MongoDB database. Will either update or insert the setting depending on whether it
        already exists.

        :param setting: Setting to update. Also contains the ID for lookup.
        :param output_model_type: The output type of the setting's model.
        :param session: PyMongo ClientSession to use for database operations.
        :return: The updated setting.
        """

        logger.info("Assigning setting with ID: %s in the database", setting.SETTING_ID)
        self._settings_collection.update_one(
            {"_id": setting.SETTING_ID}, {"$set": setting.model_dump(by_alias=True)}, upsert=True, session=session
        )

        return self.get(output_model_type=output_model_type, session=session)
