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
