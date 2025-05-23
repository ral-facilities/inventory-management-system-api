"""
Module for providing a custom implementation of the `ObjectId` class.
"""

from typing import Optional

from bson import ObjectId
from fastapi import status

from inventory_management_system_api.core.exceptions import InvalidObjectIdError


class CustomObjectId(ObjectId):
    """
    Custom implementation of `ObjectId` that accepts a string and converts it to an `ObjectId`, primarily for the
    purpose of handling MongoDB `_id` fields that are of type `ObjectId`.
    """

    def __init__(self, value: str, entity_type: Optional[str] = None, not_found_if_invalid: bool = False):
        """
        Construct a `CustomObjectId` from a string.

        :param value: The string value to be validated, representing the `ObjectId`.
        :raises InvalidObjectIdError: If the string value is an invalid `ObjectId`.
        """
        response_detail = None if entity_type is None else f"{entity_type.capitalize()} not found"
        status_code = status.HTTP_404_NOT_FOUND if not_found_if_invalid else None

        if not isinstance(value, str):
            raise InvalidObjectIdError(
                f"ObjectId value '{value}' must be a string",
                response_detail=response_detail,
                status_code=status_code,
            )

        if not ObjectId.is_valid(value):
            raise InvalidObjectIdError(
                f"Invalid ObjectId value '{value}'",
                response_detail=response_detail,
                status_code=status_code,
            )

        super().__init__(value)
