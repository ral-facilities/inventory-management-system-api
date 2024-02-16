"""
Module for defining the database models mixins to be inherited from to provide specific fields
and functionality
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import AwareDatetime, BaseModel, Field, model_validator


class CreatedModifedAtInMixin(BaseModel):
    """
    Input model mixin that provides creation and modfied time fields

    For a create request an instance of the model should be created without supplying the `created_at` field
    as this will cause it to be assigned as the current time.
    When updating, the `created_at` time should be given so that it is kept the same. The `updated_at` will be
    assigned regardless as it is assumed that a new instance will be created only when creating/updating a
    database entry.
    """

    created_at: AwareDatetime = datetime.now(timezone.utc)
    updated_at: Optional[AwareDatetime] = None

    @model_validator(mode="after")
    def validator(self) -> "CreatedModifedAtInMixin":
        """
        Validator that assigns the created_at and updated_at times.

        When `updated_at` is None, which occurrs when not assigning data from an existing database model this
        assigns the `updated_at` time to be the same as the `created_at` to ensure they are identical. When
        `updated_at` is defined then it is reassigned as its assumed it already exists and is now being updated.
        """
        if self.updated_at is None:
            self.updated_at = self.created_at
        else:
            self.updated_at = datetime.now(timezone.utc)
        return self


class CreatedModifiedAtOutMixin(BaseModel):
    """
    Output model mixin that provides creation and modfied time fields
    """

    created_at: AwareDatetime
    updated_at: AwareDatetime
