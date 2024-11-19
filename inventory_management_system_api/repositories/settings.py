"""
Module for providing a repository for managing settings in a MongoDB database.
"""

import logging
from typing import Optional, Type, TypeVar

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.settings import BaseSetting

logger = logging.getLogger()


# TODO: Should this be Settings or Setting?
class SettingsRepo:
    """
    Repository for managing settings in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialize the `SettingsRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._settings_collection: Collection = self._database.settings

    T = TypeVar("T")

    def get(self, setting_id: str, output_model_type: Type[T], session: ClientSession = None) -> Optional[T]:
        setting = self._settings_collection.find_one({"_id": setting_id}, session=session)
        if setting:
            return output_model_type(**setting)
        return None

    def update(self, setting: BaseSetting, output_model: T, session: ClientSession = None) -> T:

        self._settings_collection.update_one(
            {"_id": setting.SETTING_ID}, {"$set": setting.model_dump(by_alias=True)}, upsert=True, session=session
        )
        return self.get(setting_id=setting.SETTING_ID, output_model_type=output_model, session=session)
