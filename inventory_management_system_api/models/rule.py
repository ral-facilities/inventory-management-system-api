"""
Module for defining the database models for representing rules.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.system_type import SystemTypeOut
from inventory_management_system_api.models.usage_status import UsageStatusOut


class RuleOut(BaseModel):
    """
    Output database model for a rule.
    """

    id: StringObjectIdField = Field(alias="_id")
    # We set these default values to None, as when they are not found in the MongoDB aggregate query, they wont be
    # set and this saves us from making the query more complex
    src_system_type: Optional[SystemTypeOut] = None
    dst_system_type: Optional[SystemTypeOut] = None
    dst_usage_status: Optional[UsageStatusOut] = None

    model_config = ConfigDict(populate_by_name=True)
