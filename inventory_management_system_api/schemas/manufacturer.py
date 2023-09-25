"""
Module for defining the API schema models for representing manufacturers.
"""
from enum import Enum
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, validator, root_validator, Field


class AddressProperty(BaseModel):
    """
    Schema model for address'
    """

    name: str = Field(description="Name of building/company")
    street_name: str = Field(description="House number and street name")
    city: str = Field(description="Name of city")
    county: Optional[str] = Field(description="Name of county")
    post_code: str = Field(description="post code")
    country: str = Field(description="Country")


class ManufacturerPostRequestSchema(BaseModel):
    """Schema model for manufactuer creation request"""

    name: str = Field(description="Name of manufacturer")
    url: str = Field(description="URl of manufacturer")
    address: AddressProperty = Field(description="address of manufacturer")


class ManufacturerSchema(ManufacturerPostRequestSchema):
    """Schema model for manufacturer response"""

    id: str = Field(description="The ID of manufacturer")
