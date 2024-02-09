"""
Module for defining the API schema models for representing Units
"""

from pydantic import BaseModel, Field


class UnitSchema(BaseModel):
    """
    Schema model for a Unit get request response
    """

    id: str = Field(description="ID of the Unit")
    value: str = Field(description="Value of the Unit")
