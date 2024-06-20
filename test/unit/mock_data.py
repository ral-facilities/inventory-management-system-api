"""
Mock data for use in unit tests

Names should ideally be descriptive enough to recognise what they are without looking at the data itself.
Letters may be appended in places to indicate the data is of the same type, but has different specific values
to others.

_POST_DATA - Is for a `PostSchema` schema
_IN_DATA - Is for an `In` model
"""

SYSTEM_POST_DATA_NO_PARENT_A = {
    "parent_id": None,
    "name": "Test name A",
    "description": "Test description A",
    "location": "Test location A",
    "owner": "Test owner A",
    "importance": "low",
}

SYSTEM_POST_DATA_NO_PARENT_B = {
    "parent_id": None,
    "name": "Test name B",
    "description": "Test description B",
    "location": "Test location B",
    "owner": "Test owner B",
    "importance": "low",
}

SYSTEM_IN_DATA_NO_PARENT_A = {
    **SYSTEM_POST_DATA_NO_PARENT_A,
    "code": "test-name-a",
}

SYSTEM_IN_DATA_NO_PARENT_B = {
    **SYSTEM_POST_DATA_NO_PARENT_B,
    "code": "test-name-b",
}
