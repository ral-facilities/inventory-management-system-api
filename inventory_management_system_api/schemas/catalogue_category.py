"""
Module for defining the API schema models for representing catalogue categories.
"""
from typing import Optional, Dict, Any

from bson import ObjectId
from pydantic import BaseModel


class StringObjectIdField(ObjectId):
    """
    Custom field for handling MongoDB ObjectId as string.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: ObjectId) -> str:
        """
        Convert the ObjectId value to string.

        :param value: The ObjectId value to be converted.
        :return: The converted ObjectId as a string.
        """
        return str(value)

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        """
        Modify the field schema to indicate it as a string type.

        :param field_schema: The schema of the field.
        """
        field_schema.update(type="string")


class CatalogueCategoryPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue category creation request.
    """
    name: str
    parent_id: Optional[StringObjectIdField] = None


class CatalogueCategorySchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """
    id: StringObjectIdField
