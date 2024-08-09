"""
Mock data for sharing between different e2e tests - In particular avoids circular imports between them
"""

# Leaf with allowed values in properties


# pylint: disable=fixme
# TODO: Remove this file - replace by mock_data.py

from unittest.mock import ANY

CREATED_MODIFIED_VALUES_EXPECTED = {"created_time": ANY, "modified_time": ANY}

SYSTEM_POST_A = {
    "name": "System A",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}

# To be posted as a child of the above
SYSTEM_POST_B = {
    "name": "System B",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
# pylint: enable=duplicate-code

USAGE_STATUS_POST_A = {"value": "New"}

USAGE_STATUS_POST_A_EXPECTED = {
    **USAGE_STATUS_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "new",
    "id": ANY,
}

USAGE_STATUS_POST_B = {"value": "Used"}

USAGE_STATUS_POST_B_EXPECTED = {
    **USAGE_STATUS_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "used",
    "id": ANY,
}

USAGE_STATUS_POST_C = {"value": "In Use"}

USAGE_STATUS_POST_C_EXPECTED = {
    **USAGE_STATUS_POST_C,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "in-use",
    "id": ANY,
}

USAGE_STATUS_POST_D = {"value": "Scrapped"}

USAGE_STATUS_POST_D_EXPECTED = {
    **USAGE_STATUS_POST_D,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "scrapped",
    "id": ANY,
}
