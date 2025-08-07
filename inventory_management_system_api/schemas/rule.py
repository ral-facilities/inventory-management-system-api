"""
Module for defining the API schema models for representing rules.
"""

from pydantic import BaseModel, Field


class RuleSchema(BaseModel):
    """
    Schema model for rule get request responses.
    """

    id: str = Field(description="ID of the rule")
    src_system_type_id: str = Field(description="ID of the source system type of the rule")
    dst_system_type_id: str = Field(description="ID of the destination system type of the rule")
    dst_usage_status_id: str = Field(description="ID of the usage status to be used at the destination")
