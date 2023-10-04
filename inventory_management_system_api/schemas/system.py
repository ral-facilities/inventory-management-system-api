"""
Module for defining the API schema models for representing Systems
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SystemImportanceType(str, Enum):
    """
    Enumeration for System importance types
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SystemPostRequestSchema(BaseModel):
    """
    Schema model for a System creation request
    """

    name: str = Field(description="Name of the system")
    location: str = Field(description="Location of the system")
    owner: str = Field(description="Owner of the systems")
    importance: SystemImportanceType = Field(description="Importance of the system")
    parent_id: Optional[str] = Field(default=None, description="ID of the parent System (if applicable)")


class SystemGetRequestSchema(SystemPostRequestSchema):
    """
    Schema models for System get request response
    """

    id: str = Field(description="ID of the System")
    code: str = Field(description="Code of the System")
    path: str = Field(description="Path to the System")
    parent_path: str = Field(description="Path to the parent System")
