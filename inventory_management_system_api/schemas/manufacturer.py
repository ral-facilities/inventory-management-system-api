"""
Module for defining the API schema models for representing manufacturers.
"""

from pydantic import BaseModel, Field


class ManufacturerPostRequestSchema(BaseModel):
    """Schema model for manufactuer creation request"""

    name: str = Field(description="Name of manufacturer")
    url: str = Field(description="URL of manufacturer")
    address: str = Field(description="Address of manufacturer")


class ManufacturerSchema(ManufacturerPostRequestSchema):
    """Schema model for manufacturer response"""

    id: str = Field(description="The ID of manufacturer")
    code: str = Field(description="The code of the manufacturer")
