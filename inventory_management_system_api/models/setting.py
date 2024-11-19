"""
Module for defining the database models for representing settings.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.usage_status import UsageStatusOut


class BaseSetting(BaseModel, ABC):
    """
    Base database model for a setting.
    """

    @property
    @staticmethod
    @abstractmethod
    def SETTING_ID() -> str:  # pylint: disable=invalid-name
        """ID of the setting. Ensures this value can be obtained from the class type itself as a static variable."""
        return ""


class SparesDefinitionUsageStatusIn(BaseModel):
    """
    Input database model for a usage status in a spares definition.
    """

    id: CustomObjectIdField


class SparesDefinitionUsageStatusOut(BaseModel):
    """
    Output database model for a usage status in a spares definition.
    """

    id: StringObjectIdField


class SparesDefinitionIn(BaseSetting):
    """
    Input database model for a spares definition.
    """

    SETTING_ID: ClassVar[str] = "spares_definition"

    usage_statuses: list[SparesDefinitionUsageStatusIn]


class SparesDefinitionOut(SparesDefinitionIn):
    """
    Output database model for a spares definition.
    """

    usage_statuses: list[UsageStatusOut]
