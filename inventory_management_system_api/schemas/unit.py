"""
Module for defining the API schema models for representing Units
"""

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class UnitPostSchema(BaseModel):
    """
    Schema model for a Unit post request
    """

    value: str = Field(description="Value of the Unit")


class UnitSchema(CreatedModifiedSchemaMixin, UnitPostSchema):
    """
    Schema model for a Unit get request response
    """

    id: str = Field(description="ID of the Unit")
    code: str = Field(description="Code of the Unit")
