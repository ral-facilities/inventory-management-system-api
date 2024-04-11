"""
Module for defining the API schema models for representing Usage statuses
"""

from pydantic import BaseModel, Field


class UsageStatusSchema(BaseModel):
    """
    Schema model for a Usage status get request response
    """

    id: str = Field(description="ID of the Usage status")
    value: str = Field(description="Status of the Usage status")
