"""
Module for defining the database models for representing settings.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.system_type import SystemTypeOut


class SettingInBase(BaseModel):
    """
    Base input database model for a setting.
    """

    SETTING_ID: ClassVar[str]


class SettingOutBase(SettingInBase):
    """
    Base output database model for a setting.
    """

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)


class SparesDefinitionBase(SettingInBase):
    """Base database model for the spares definition."""

    SETTING_ID: ClassVar[str] = "spares_definition"


class SparesDefinitionIn(SparesDefinitionBase):
    """
    Input database model for the spares definition.
    """

    system_type_ids: list[CustomObjectIdField]


class SparesDefinitionOut(SparesDefinitionBase, SettingOutBase):
    """
    Output database model for the spares definition.
    """

    system_types: list[SystemTypeOut]
