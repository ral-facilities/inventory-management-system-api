"""
Module for defining the database models for representing settings.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField


class SettingOutBase(BaseModel, ABC):
    """
    Base output database model for a setting.
    """

    @property
    @staticmethod
    @abstractmethod
    def SETTING_ID() -> str:  # pylint: disable=invalid-name
        """ID of the setting. Ensures this calue can be obtained from the classs type itself as a static variable."""

    id: StringObjectIdField = Field(alias="_id")


class SparesDefinitionOut(SettingOutBase):
    """
    Output database model for the spares defintion.
    """

    SETTING_ID: ClassVar[str] = "spares_definition"

    system_type_ids: list[StringObjectIdField]
