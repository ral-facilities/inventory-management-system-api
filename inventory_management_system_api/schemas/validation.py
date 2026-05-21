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


class ValidationResultSchema(BaseModel):
    """Schema model for a single result in a bulk validation response."""

    index: int = Field(description="Index of the result, corresponding to the inputted list data.")
    warnings: list[ValidationErrorSchema] = Field(description="List of validation warnings for the specific entity.")
    errors: list[ValidationErrorSchema] = Field(description="List of validation errors for the specific entity.")


class BulkValidationResultSchema(BaseModel):
    """Schema model for the result of a bulk validation request."""

    results: list[ValidationResultSchema] = Field(description="List of validation results for the entities.")
