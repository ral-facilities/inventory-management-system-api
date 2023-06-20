"""
Module for defining the database models for representing catalogue categories.
"""
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from inventory_management_system_api.core.custom_object_id import CustomObjectId


class CustomObjectIdField(ObjectId):
    """
    Custom field for handling MongoDB ObjectId validation.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> CustomObjectId:
        """
        Validate if the string value is a valid `ObjectId`.

        :param value: The string value to be validated.
        :return: The validated `ObjectId`.
        """
        return CustomObjectId(value)


class CatalogueCategoryIn(BaseModel):
    """
    Input database model for a catalogue category.
    """

    name: str
    code: str
    parent_id: Optional[CustomObjectIdField] = None


class CatalogueCategoryOut(CatalogueCategoryIn):
    """
    Output database model for a catalogue category.
    """

    id: ObjectId = Field(alias="_id")

    class Config:
        # pylint: disable=C0115
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
