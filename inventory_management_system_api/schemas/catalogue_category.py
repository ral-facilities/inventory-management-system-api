"""
Module for defining the API schema models for representing catalogue categories.
"""
from typing import Optional

from pydantic import BaseModel


class CatalogueCategoryPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue category creation request.
    """

    name: str
    is_leaf: bool
    parent_id: Optional[str] = None


class CatalogueCategorySchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str
    code: str
    path: str
    parent_path: str
