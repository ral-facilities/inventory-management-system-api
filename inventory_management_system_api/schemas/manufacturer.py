"""
Module for defining the API schema models for representing manufacturers.
"""
from enum import Enum
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, validator, root_validator, Field


class ManufacturerPostRequestSchema(BaseModel):
    """Schema model for manufactuer creation request"""

    name: str = Field(description="Name of manufacturer")
    url: str = Field(description="URl of manufacturer")
    address: str = Field(description="address of manufacturer")


class ManufacturerSchema(ManufacturerPostRequestSchema):
    """Schema model for manufacturer response"""

    id: str = Field(description="The ID of manufacturer")
