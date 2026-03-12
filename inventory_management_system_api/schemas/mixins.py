"""
Module for defining the schema mixins to be inherited from to provide specific fields
"""

from typing import Any, Optional
from pydantic import AwareDatetime, BaseModel, Field, model_validator


class BaseFieldsSchemaMixin(BaseModel):
    """
    Output schema mixin that provides the base fields
    """

    created_time: AwareDatetime = Field(description="The date and time this entity was created")
    modified_time: AwareDatetime = Field(description="The date and time this entity was last updated")
    modified_comment: Optional[str] = Field(description="A user comment justifying the state of the entity")


class BaseFieldsPostSchemaMixin(BaseModel):
    """
    A custom input base class that provides the base fields
    """

    modified_comment: Optional[str] = Field(
        default=None, description="A user comment justifying the state of the entity"
    )
    
    @model_validator(mode="before")
    @classmethod
    def force_modified_comment(cls, data: Any) -> Any:
        """
        Function that ensures the modified_comment is always included in any model.
        
        When `modified_comment` is not in the request body, it ensures it is assigned to `None`,
        so that it is applied in the database and not excluded from `model_dump`
        """
        if isinstance(data, dict) and "modified_comment" not in data:
            data["modified_comment"] = None
        return data
            
        
