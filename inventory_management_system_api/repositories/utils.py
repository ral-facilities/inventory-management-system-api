"""
Utility methods used in the repositories
"""

import logging
from typing import Optional

logger = logging.getLogger()


def path_query(path: Optional[str], parent_path: Optional[str], entity_type: str) -> dict:
    """
    Constructs filters for a pymongo collection based on a given path and parent path while
    also logging the action

    :param path: Path to filter the `entity_type` by
    :param parent_path: Parent path to filter `entity_type` by
    :param entity_type: Name of the entity type e.g. catalogue categories/systems (Used for logging)
    :return: Dictionary representing the query to pass to a pymongo's Collection `find` function
    """
    query = {}
    if path:
        query["path"] = path
    if parent_path:
        query["parent_path"] = parent_path

    message = f"Retrieving all {entity_type} from the database"
    # pylint: disable=duplicate-code
    if not query:
        logger.info(message)
    else:
        logger.info("%s matching the provided filter(s)", message)
        logger.debug("Provided filter(s): %s", query)
    return query
