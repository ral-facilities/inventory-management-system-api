"""
Module for providing a custom implementation of the `ObjectId` class.
"""

from bson import ObjectId

from inventory_management_system_api.core.exceptions import InvalidObjectIdError


class CustomObjectId(ObjectId):
    """
    Custom implementation of `ObjectId` that accepts a string and converts it to an `ObjectId`, primarily for the
    purpose of handling MongoDB `_id` fields that are of type `ObjectId`.
    """

    def __init__(self, value: str):
        """
        Construct a `CustomObjectId` from a string.

        :param value: The string value to be validated, representing the `ObjectId`.
        :raises InvalidObjectIdError: If the string value is an invalid `ObjectId`.
        """
        if not isinstance(value, str):
            raise InvalidObjectIdError(f"ObjectId value '{value}' must be a string")

        if not ObjectId.is_valid(value):
            raise InvalidObjectIdError(f"Invalid ObjectId value '{value}'")

        super().__init__(value)
