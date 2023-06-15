"""
Module for connecting to a MongoDB database.
"""
from pymongo import MongoClient
from pymongo.database import Database

from inventory_management_system_api.core.config import config

db_config = config.database
mongodb_client = MongoClient(
    f"{db_config.protocol}://{db_config.username}:{db_config.password}@{db_config.hostname}:{db_config.port}"
)


def get_database() -> Database:
    """
    Connects to a MongoDB database and returns the specified database.

    :return: The MongoDB database object.
    """
    return mongodb_client[db_config.name]
