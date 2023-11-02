"""
Module for defining the API schema models for representing manufacturers.
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class AddressSchema(BaseModel):
    """Schema for address type"""

    address_line: str = Field(description="The address line of the manufacturer")
    town: Optional[str] = Field(default=None, description="Town of manufacturer")
    county: Optional[str] = Field(default=None, description="County of manufacturer")
    country: str = Field(description="Country of the manufacturer")
    postcode: str = Field(description="Post Code/Zip of manufacturer")


class AddressPatchRequestSchema(AddressSchema):
    """Schema used for editting address, so that it allows to edit individual fields"""

    address_line: Optional[str] = Field(default=None, description="The address line of the manufacturer")
    postcode: Optional[str] = Field(default=None, description="Post Code/Zip of manufacturer")
    country: Optional[str] = Field(description="Country of the manufacturer")


class ManufacturerPostRequestSchema(BaseModel):
    """Schema model for manufactuer creation request"""

    name: str = Field(description="Name of manufacturer")
    url: Optional[HttpUrl] = Field(default=None, description="URL of manufacturer")
    address: AddressSchema = Field(description="Address of manufacturer")
    telephone: Optional[str] = Field(default=None, description="Phone number of manufacturer")


class ManufacturerSchema(ManufacturerPostRequestSchema):
    """Schema model for manufacturer response"""

    id: str = Field(description="The ID of manufacturer")
    code: str = Field(description="The code of the manufacturer")


class ManufacturerPatchRequestSchema(ManufacturerPostRequestSchema):
    """Schema model for editing a manufacturer"""

    name: Optional[str]
    address: Optional[AddressPatchRequestSchema]
