"""
Module for defining the database models mixins to be inherited from to provide specific fields
and functionality
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import AwareDatetime, BaseModel, Field, model_validator


class CreatedModifiedTimeInMixin(BaseModel):
    """
    Input model mixin that provides creation and modfied time fields

    For a create request an instance of the model should be created without supplying the `created_time` field
    as this will cause it to be assigned as the current time.
    When updating, the `created_time` time should be given so that it is kept the same. The `modified_time` will be
    assigned regardless as it is assumed that a new instance will be created only when creating/updating a
    database entry.
    """

    created_time: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_time: Optional[AwareDatetime] = None

    @model_validator(mode="after")
    def validator(self) -> "CreatedModifiedTimeInMixin":
        """
        Validator that assigns the created_time and modified_time times.

        When `modified_time` is None, which occurs when not assigning data from an existing database model this
        assigns the `modified_time` time to be the same as the `created_time` to ensure they are identical. When
        `modified_time` is defined then it is reassigned as its assumed it already exists and is now being updated.
        """
        if self.modified_time is None:
            self.modified_time = self.created_time
        else:
            self.modified_time = datetime.now(timezone.utc)
        return self


class CreatedModifiedTimeOutMixin(BaseModel):
    """
    Output model mixin that provides creation and modfied time fields
    """

    created_time: AwareDatetime
    modified_time: AwareDatetime
