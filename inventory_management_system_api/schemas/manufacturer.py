"""
Module for defining the API schema models for representing manufacturers.
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class Address(BaseModel):
    """Schema for address type"""

    building_number: int = Field(description="House/Building number of manufacturer")
    street_name: str = Field(description="Street name of manufacturer")
    town: Optional[str] = Field(default=None, description="Town of manufacturer")
    county: Optional[str] = Field(default=None, description="County of manufacturer")
    country: Optional[str] = Field(default=None, description="Country of the manufacturer")
    postCode: str = Field(description="Post Code/Zip of manufacturer")


class ManufacturerPostRequestSchema(BaseModel):
    """Schema model for manufactuer creation request"""

    name: str = Field(description="Name of manufacturer")
    url: Optional[HttpUrl] = Field(default=None, description="URL of manufacturer")
    address: Address = Field(description="Address of manufacturer")
    telephone: Optional[str] = Field(default=None, description="Phone number of manufacturer")


class ManufacturerSchema(ManufacturerPostRequestSchema):
    """Schema model for manufacturer response"""

    id: str = Field(description="The ID of manufacturer")
    code: str = Field(description="The code of the manufacturer")


class ManufacturerPatchRequstSchema(BaseModel):
    """Schema model for editing a manufacturer"""

    name: Optional[str]
    url: Optional[HttpUrl]
    address: Optional[Address]
    telephone: Optional[str]
