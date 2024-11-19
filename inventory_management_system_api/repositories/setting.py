"""
Module for providing a repository for managing settings in a MongoDB database.
"""

import logging
from typing import Optional, Type, TypeVar

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.setting import BaseSetting

logger = logging.getLogger()


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

    T = TypeVar("T", bound=BaseSetting)

    def get(self, output_model_type: Type[T], session: ClientSession = None) -> Optional[T]:
        setting = self._settings_collection.find_one({"_id": output_model_type.SETTING_ID}, session=session)
        if setting:
            return output_model_type(**setting)
        return None

    def update(self, setting: BaseSetting, output_model: Type[T], session: ClientSession = None) -> T:

        self._settings_collection.update_one(
            {"_id": setting.SETTING_ID}, {"$set": setting.model_dump(by_alias=True)}, upsert=True, session=session
        )

        # logger.info("HELLO WORLD")
        # logger.info(
        #     list(
        #         self._settings_collection.aggregate(
        #             [
        #                 {"$match": {"_id": setting.SETTING_ID}},
        #                 {"$unwind": "$usage_statuses"},
        #                 {
        #                     "$lookup": {
        #                         "from": "usage_statuses",
        #                         "localField": "usage_statuses.id",
        #                         "foreignField": "_id",
        #                         "as": "statusDetails",
        #                     }
        #                 },
        #                 {"$unwind": "$statusDetails"},
        #                 {"$addFields": {"usage_statuses.value": "$statusDetails.value"}},
        #                 {"$unset": "statusDetails"},
        #                 {
        #                     "$group": {
        #                         "_id": "$_id",
        #                         "usage_statuses": {"$push": "$usage_statuses"},
        #                         "otherFields": {"$first": "$$ROOT"},
        #                     }
        #                 },
        #                 {
        #                     "$replaceRoot": {
        #                         "newRoot": {"$mergeObjects": ["$otherFields", {"usage_statuses": "$usage_statuses"}]}
        #                     }
        #                 },
        #             ]
        #         )
        #     )[0]
        # )

        return self.get(output_model_type=output_model, session=session)
