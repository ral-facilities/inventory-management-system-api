"""
Contains constants used in multiple places so they are easier to change
"""

import sys

from inventory_management_system_api.core.config import config

# Maximum length of the trail to return for breadcrumbs GET endpoints
# e.g. a value of 5 means the trail goes back to at most the last 4
# parents
BREADCRUMBS_TRAIL_MAX_LENGTH: int = 5
PUBLIC_KEY = None

# Detail to return in the 500 (Internal Server Error) responses
HTTP_500_INTERNAL_SERVER_ERROR_DETAIL = "Something went wrong"

if config.authentication.enabled:
    # Read the content of the public key file into a constant. This is used for decoding of JWT access tokens.
    try:
        with open(config.authentication.public_key_path, "r", encoding="utf-8") as file:
            PUBLIC_KEY = file.read()
    except FileNotFoundError as exc:
        sys.exit(f"Cannot find public key: {exc}")
