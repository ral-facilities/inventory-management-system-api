"""
Module for defining the API schema models for representing settings.
"""

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.system_type import SystemTypeSchema


class SparesDefinitionSchema(BaseModel):
    """
    Schema model for a spares definition get request response.
    """

    system_types: list[SystemTypeSchema] = Field(
        description="List of system types that define which systems contain items that are considered spares."
    )


class InUseDefinitionSchema(BaseModel):
    """
    Schema model for an in use definition get request response.
    """

    system_types: list[SystemTypeSchema] = Field(
        description="List of system types that define which systems contain items that are in use."
    )
