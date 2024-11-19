"""
Module for defining the database models for representing settings.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField


class BaseSetting(BaseModel, ABC):
    """
    Base database model for a setting.
    """

    # This ID is a placeholder. Actual value is obtained from the actual inherited setting.
    id: str = Field(default="", validate_default=True, validation_alias="_id", serialization_alias="_id")

    @property
    @staticmethod
    @abstractmethod
    def SETTING_ID() -> str:  # pylint: disable=invalid-name
        """ID of the setting. Ensures this value can be obtained from the class type itself as a static variable."""
        return ""

    @field_validator("id")
    @classmethod
    def id_must_be_setting_id(cls, _) -> str:
        """This validator ensures the ID is replaced by the inherited ID for the setting. Literal[variable]
        is invalid unfortunately."""
        return cls.SETTING_ID


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

    usage_statuses: list[SparesDefinitionUsageStatusOut]


# TODO: Add types?
SETTINGS_MODELS: dict = {"spares_definition": {"in": SparesDefinitionIn, "out": SparesDefinitionOut}}

# class BaseSetting(BaseModel, ABC):
#     """
#     Base database model for a setting.
#     """

#     id: str = Field(default="", validate_default=True, validation_alias="_id", serialization_alias="_id")

#     @property
#     @staticmethod
#     @abstractmethod
#     def setting_id() -> str:
#         """ID of the setting. Ensures this value can be obtained from the class type itself as a static variable."""

#     @field_validator("id")
#     @classmethod
#     def id_must_be_setting_id(cls, v: str) -> str:
#         return cls.setting_id


# class SparesDefinition(BaseSetting):
#     setting_id: str = "spares_definition"


# class BaseSetting(BaseModel):
#     """
#     Base database model for a setting.
#     """

#     SETTING_ID: ClassVar[str]

#     id: str = Field(default="", validate_default=True, validation_alias="_id", serialization_alias="_id")

#     @field_validator("id")
#     @classmethod
#     def id_must_be_setting_id(cls, v: str) -> str:
#         return cls.SETTING_ID


# class SparesDefinition(BaseSetting):
#     SETTING_ID: ClassVar[str] = "spares_definition"


# class BaseSetting(BaseModel):
#     """
#     Base database model for a setting.
#     """

#     # ID used for settings will be hard coded and depends on the setting itself
#     id: str = Field(validation_alias="_id", serialization_alias="_id")


# class SparesDefinition(BaseSetting):
#     """
#     Database model for the spares definition setting.
#     """

#     id: Literal["spares_definition"] = Field(
#         default="spares_definition", validation_alias="_id", serialization_alias="_id"
#     )
