"""
Module for defining the schema mixins to be inherited from to provide specific fields
"""

from pydantic import AwareDatetime, BaseModel, Field


class CreatedModifiedSchemaMixin(BaseModel):
    """
    Output schema mixin that provides creation and modfied time fields
    """

    created_at: AwareDatetime = Field(description="The date and time this entity was created")
    updated_at: AwareDatetime = Field(description="The date and time this entity was last updated")
