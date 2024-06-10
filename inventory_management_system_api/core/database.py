"""
Module for connecting to a MongoDB database.
"""

from pymongo import MongoClient
from pymongo.database import Database

from inventory_management_system_api.core.config import config

db_config = config.database
mongodb_client = MongoClient(
    f"{db_config.protocol.get_secret_value()}://{db_config.username.get_secret_value()}"
    f":{db_config.password.get_secret_value()}@{db_config.hostname.get_secret_value()}"
    f":{db_config.port.get_secret_value()}",
    tz_aware=True,
)


def get_database() -> Database:
    """
    Connects to a MongoDB database and returns the specified database.

    :return: The MongoDB database object.
    """
    return mongodb_client[db_config.name.get_secret_value()]
