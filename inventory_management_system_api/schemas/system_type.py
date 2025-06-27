"""
Module for defining the API schema models for representing system types.
"""

from pydantic import BaseModel, Field


class SystemTypeSchema(BaseModel):
    """
    Schema model for system type get request response.
    """

    id: str = Field(description="ID of the system type")
    value: str = Field(description="Value of the system type")
