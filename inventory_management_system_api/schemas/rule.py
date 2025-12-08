"""
Module for defining the API schema models for representing rules.
"""

from typing import Optional

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.system_type import SystemTypeSchema
from inventory_management_system_api.schemas.usage_status import UsageStatusSchema


class RuleSchema(BaseModel):
    """
    Schema model for rule get request responses.
    """

    id: str = Field(description="ID of the rule")
    src_system_type: Optional[SystemTypeSchema] = Field(description="Source system type of the rule")
    dst_system_type: Optional[SystemTypeSchema] = Field(description="Destination system type of the rule")
    dst_usage_status: Optional[UsageStatusSchema] = Field(description="Usage status to be used at the destination")
