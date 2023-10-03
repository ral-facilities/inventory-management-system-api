"""
Module for defining custom `ObjectId` data type classes used by Pydantic models.
"""
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId


class CustomObjectIdField(ObjectId):
    """
    Custom data type for handling MongoDB ObjectId validation.
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
    Custom data type for handling MongoDB ObjectId as string.
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
