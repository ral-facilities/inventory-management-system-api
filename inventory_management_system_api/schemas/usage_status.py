"""
Module for defining the API schema models for representing Usage statuses
"""

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class UsageStatusPostSchema(BaseModel):
    """
    Schema model for a Usage status post request
    """

    value: str = Field(description="Value of the Usage status")


class UsageStatusSchema(CreatedModifiedSchemaMixin, UsageStatusPostSchema):
    """
    Schema model for a Usage status get request response
    """

    id: str = Field(description="ID of the Usage status")

    code: str = Field(description="Code of the Usage status")
