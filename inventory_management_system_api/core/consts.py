"""
Contains constants used in multiple places so they are easier to change
"""

# Maximum length of the trail to return for breadcrumbs GET endpoints
# e.g. a value of 5 means the trail goes back to at most the last 4
# parents
BREADCRUMBS_TRAIL_MAX_LENGTH: int = 5
