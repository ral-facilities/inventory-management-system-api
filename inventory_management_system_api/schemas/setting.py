"""
Module for defining the API schema models for representing settings.
"""

from pydantic import BaseModel, Field, conlist, field_validator

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

    usage_statuses: conlist(SparesDefinitionPutUsageStatusSchema, min_length=1) = Field(
        description="Usage statuses that classify items as a spare."
    )

    @field_validator("usage_statuses")
    @classmethod
    def validate_usage_statuses(
        cls, usage_statuses: list[SparesDefinitionPutUsageStatusSchema]
    ) -> list[SparesDefinitionPutUsageStatusSchema]:
        """
        Validator for the `usage_statuses` field.

        Ensures the `usage_statuses` dont contain any duplicate IDs.

        :param usage_statuses: The value of the `usage_statuses` field.
        :return: The value of the `usage_statuses` field.
        """

        # Prevent duplicates
        seen_usage_status_ids = set()
        for usage_status in usage_statuses:
            if usage_status.id in seen_usage_status_ids:
                raise ValueError(f"usage_statuses contains a duplicate ID: {usage_status.id}")
            seen_usage_status_ids.add(usage_status.id)

        return usage_statuses


class SparesDefinitionSchema(BaseModel):
    """
    Schema model for a spares definition.
    """

    usage_statuses: list[UsageStatusSchema] = Field(description="Usage statuses that classify items as a spare.")
