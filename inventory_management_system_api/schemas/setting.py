"""
Module for defining the API schema models for representing settings.
"""

from pydantic import BaseModel, Field

from inventory_management_system_api.schemas.usage_status import UsageStatusSchema


class SparesDefinitionPutUsageStatusSchema(BaseModel):
    """
    Schema model for a usage status within a spares definition update request.
    """

    id: str = Field(description="The ID of the usage status.")


class SparesDefinitionUsageStatusSchema(SparesDefinitionPutUsageStatusSchema):
    """
    Schema model for a usage status within a spares definition.
    """

    id: str = Field(description="The ID of the usage status.")


class SparesDefinitionPutSchema(BaseModel):
    """
    Schema model for a spares definition update request.
    """

    usage_statuses: list[SparesDefinitionPutUsageStatusSchema] = Field(
        description="Usage statuses that classify items as a spare."
    )


class SparesDefinitionSchema(SparesDefinitionPutSchema):
    """
    Schema model for a spares definition.
    """

    usage_statuses: list[UsageStatusSchema] = Field(description="Usage statuses that classify items as a spare.")
