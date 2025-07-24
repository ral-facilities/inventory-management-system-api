"""
Module for providing a repository for managing settings in a MongoDB database.
"""

from typing import Optional, Type, TypeVar

from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.models.setting import SettingOutBase

# Template type for models inheriting from SettingOutBase so this repo can be used generically for multiple settings
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

    def get(
        self, out_model_type: Type[SettingOutBaseT], session: Optional[ClientSession] = None
    ) -> Optional[SettingOutBaseT]:
        """
        Retrive a setting from a MongoDB database.

        :param out_model_type: Output type of the setting's model. Also contains the ID for the lookup.
        :param session: PyMongo ClientSession to use for database operations.
        :return: Retireved setting or `None` if not found.
        """

        setting = self._settings_collection.find_one({"_id": out_model_type.SETTING_ID}, session=session)
        if setting:
            return out_model_type(**setting)
        return None
