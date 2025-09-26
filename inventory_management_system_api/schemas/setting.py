"""
Module for defining the API schema models for representing settings.
"""

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.system_type import SystemTypeSchema


class SparesDefinitionSchema(BaseModel):
    """
    Schema model for a Setting get request response.
    """

    system_types: list[SystemTypeSchema] = Field(description="List of system types for spares definition")
