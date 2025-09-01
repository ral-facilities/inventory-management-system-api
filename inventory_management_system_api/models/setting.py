"""
Module for defining the database models for representing settings.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.system_type import SystemTypeOut


class SettingOutBase(BaseModel):
    """
    Base output database model for a setting.
    """

    SETTING_ID: ClassVar[str]

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)


class SparesDefinitionOut(SettingOutBase):
    """
    Output database model for the spares definition.
    """

    SETTING_ID: ClassVar[str] = "spares_definition"

    system_types: list[SystemTypeOut]
