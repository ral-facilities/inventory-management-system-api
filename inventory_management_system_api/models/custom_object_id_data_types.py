"""
Module for defining custom `ObjectId` data type classes used by Pydantic models.
"""
from typing import Any

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from inventory_management_system_api.core.custom_object_id import CustomObjectId


class CustomObjectIdField(ObjectId):
    """
    Custom data type for handling MongoDB ObjectId validation.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value: str, _: core_schema.ValidationInfo) -> CustomObjectId:
        """
        Validate if the string value is a valid `ObjectId`.

        :param value: The string value to be validated.
        :param _: Unused
        :return: The validated `ObjectId`.
        """
        return CustomObjectId(value)


class StringObjectIdField(str):
    """
    Custom data type for handling MongoDB ObjectId as string.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value: ObjectId, _: core_schema.ValidationInfo) -> str:
        """
        Convert the `ObjectId` value to string.

        :param value: The `ObjectId` value to be converted.
        :param _: Unused
        :return: The converted `ObjectId` as a string.
        """
        return str(value)
