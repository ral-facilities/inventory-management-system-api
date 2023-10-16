"""
Utility methods used in the repositories
"""

import logging
from typing import Optional

from inventory_management_system_api.core.custom_object_id import CustomObjectId

logger = logging.getLogger()


def list_query(parent_id: Optional[str], entity_type: str) -> dict:
    """
    Constructs filters for a pymongo collection based on a given parent_id
    also logging the action

    :param parent_id: parent_id to filter `entity_type` by (Converted to a uuid here - a string value of "null"
                      indicates that the parent_id should be null, not that there shouldn't be a query)
    :param entity_type: Name of the entity type e.g. catalogue categories/systems (Used for logging)
    :return: Dictionary representing the query to pass to a pymongo's Collection `find` function
    """
    query = {}
    if parent_id:
        query["parent_id"] = None if parent_id == "null" else CustomObjectId(parent_id)

    message = f"Retrieving all {entity_type} from the database"
    if not query:
        logger.info(message)
    else:
        logger.info("%s matching the provided filter(s)", message)
        logger.debug("Provided filter(s): %s", query)
    return query
