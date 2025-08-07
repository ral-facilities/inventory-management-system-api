"""
Module for defining the database models for representing rules.
"""

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField


class RuleOut(BaseModel):
    """
    Output database model for a rule.
    """

    id: StringObjectIdField = Field(alias="_id")
    src_system_type_id: StringObjectIdField
    dst_system_type_id: StringObjectIdField
    dst_usage_status_id: StringObjectIdField

    model_config = ConfigDict(populate_by_name=True)
