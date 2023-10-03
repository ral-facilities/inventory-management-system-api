"""
Unit tests for the `CustomObjectId` class.
"""

import pytest

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import InvalidObjectIdError


def test_valid_object_id():
    """
    Test creating an `ObjectId` from a valid string.
    """
    value = "60cfa3a616d3f57c16fe4d0a"
    custom_id = CustomObjectId(value)
    assert str(custom_id) == value


def test_invalid_object_id():
    """
    Test creating an `ObjectId` from an invalid string.
    """
    value = "invalid"
    with pytest.raises(InvalidObjectIdError) as exc:
        CustomObjectId(value)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_non_string_input():
    """
    Test creating an `ObjectId` from a non string input.
    """
    value = 123
    with pytest.raises(InvalidObjectIdError) as exc:
        CustomObjectId(value)
    assert str(exc.value) == f"ObjectId value '{value}' must be a string"


def test_empty_string_input():
    """
    Test creating an `ObjectId` from an empty string.
    """
    value = ""
    with pytest.raises(InvalidObjectIdError) as exc:
        CustomObjectId(value)
    assert str(exc.value) == f"Invalid ObjectId value '{value}'"


def test_none_input():
    """
    Test creating an `ObjectId` from a `None`.
    """
    value = None
    with pytest.raises(InvalidObjectIdError) as exc:
        CustomObjectId(value)
    assert str(exc.value) == f"ObjectId value '{value}' must be a string"
