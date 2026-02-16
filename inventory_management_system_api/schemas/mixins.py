"""
Module for defining the schema mixins to be inherited from to provide specific fields
"""

from typing import Optional
from pydantic import AwareDatetime, BaseModel, Field


class BaseFieldsSchemaMixin(BaseModel):
    """
    Output schema mixin that provides the base fields
    """

    created_time: AwareDatetime = Field(description="The date and time this entity was created")
    modified_time: AwareDatetime = Field(description="The date and time this entity was last updated")
    modified_comment: Optional[str] = Field(description="A user comment justifying the state of the entity")
