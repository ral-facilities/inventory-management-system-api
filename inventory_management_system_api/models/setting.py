"""
Module for defining the database models for representing settings.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.system_type import SystemTypeOut


class SettingOutBase(BaseModel, ABC):
    """
    Base output database model for a setting.
    """

    @property
    @staticmethod
    @abstractmethod
    def SETTING_ID() -> str:  # pylint: disable=invalid-name
        """ID of the setting. Ensures this value can be obtained from the class type itself as a static variable."""

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)


class SparesDefinitionOut(SettingOutBase):
    """
    Output database model for the spares definition.
    """

    SETTING_ID: ClassVar[str] = "spares_definition"

    system_types: list[SystemTypeOut]
