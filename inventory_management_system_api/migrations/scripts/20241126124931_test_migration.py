"""
Module providing a migration that Does nothing
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

import logging

from pymongo.client_session import ClientSession
from pymongo.database import Database

from inventory_management_system_api.migrations.base import BaseMigration

logger = logging.getLogger()


class Migration(BaseMigration):
    """Migration that Does nothing"""

    description = "Does nothing"

    def __init__(self, database: Database):
        pass

    def forward(self, session: ClientSession):
        """Applies database changes."""

    def backward(self, session: ClientSession):
        """Reverses database changes."""
