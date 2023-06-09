"""
Module for defining the database models for representing catalogue categories.
"""
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class CatalogueCategoryIn(BaseModel):
    """
    Input database model for a catalogue category.
    """
    name: str
    parent_id: Optional[ObjectId] = None


class CatalogueCategoryOut(CatalogueCategoryIn):
    """
    Output database model for a catalogue category.
    """
    id: ObjectId = Field(alias="_id")

    class Config:
        # pylint: disable=C0115
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
