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


class StringObjectIdField(str):
    """
    Custom field for handling MongoDB ObjectId as string.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: ObjectId) -> str:
        """
        Convert the `ObjectId` value to string.

        :param value: The `ObjectId` value to be converted.
        :return: The converted `ObjectId` as a string.
        """
        return str(value)


class CatalogueCategoryIn(BaseModel):
    """
    Input database model for a catalogue category.
    """

    name: str
    code: str
    path: str
    parent_path: str
    parent_id: Optional[CustomObjectIdField] = None


class CatalogueCategoryOut(CatalogueCategoryIn):
    """
    Output database model for a catalogue category.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    class Config:
        # pylint: disable=C0115
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
