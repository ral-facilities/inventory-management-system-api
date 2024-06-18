"""
Mock data for sharing between different repo tests
"""

from datetime import datetime, timezone

from bson import ObjectId

MOCK_CREATED_MODIFIED_TIME = {
    "created_time": datetime(2024, 2, 16, 14, 1, 13, 0, tzinfo=timezone.utc),
    "modified_time": datetime(2024, 2, 16, 14, 1, 13, 0, tzinfo=timezone.utc),
}

MOCK_CATALOGUE_CATEGORY_PROPERTY_A_INFO = {
    "id": str(ObjectId()),
    "name": "Property A",
    "type": "number",
    "unit": "mm",
    "mandatory": False,
}

MOCK_PROPERTY_A_INFO = {
    "id": str(ObjectId()),
    "name": "Property A",
    "value": "Test value",
    "unit": None,
}
