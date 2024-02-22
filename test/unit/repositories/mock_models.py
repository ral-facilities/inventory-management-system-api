"""
Mock data for sharing between different repo tests
"""

from datetime import datetime, timezone

MOCK_CREATED_MODIFIED_TIME = {
    "created_time": datetime(2024, 2, 16, 14, 1, 13, 0, tzinfo=timezone.utc),
    "modified_time": datetime(2024, 2, 16, 14, 1, 13, 0, tzinfo=timezone.utc),
}
