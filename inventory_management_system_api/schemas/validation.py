"""
Module for defining the API schema models for representing validation outcomes.
"""

from typing import Any

from pydantic import BaseModel, Field


class ValidationErrorSchema(BaseModel):
    """Schema model for a validation error."""

    type: str = Field(description="Type of error")
    location: list[str | int] = Field(
        description="Location of the error. List containing dictionary keys of the submitted data, or array indexes as "
        "appropriate.",
        validation_alias="loc",
    )
    message: str = Field(description="Message of the error", validation_alias="msg")
    input: Any = Field(description="Specific input the error was caused by")


class ValidationSchema(BaseModel):
    """Schema model for a validation response."""

    errors: list[ValidationErrorSchema]
