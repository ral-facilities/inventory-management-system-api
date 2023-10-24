"""
Utility methods used in the repositories
"""

import logging
from typing import Optional

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DatabaseIntegrityError, MissingRecordError
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema

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
    if not query:
        logger.info(message)
    else:
        logger.info("%s matching the provided filter(s)", message)
        logger.debug("Provided filter(s): %s", query)
    return query


def create_breadcrumbs_aggregation_pipeline(entity_id: str, collection_name: str) -> list:
    """
    Returns an aggregate query for collecting breadcrumbs data

    :param entity_id: ID of the entity to look up the breadcrumbs for
    :param collection_name: Value of "from" to use for the $graphLookup query - Should be the name of
                            the collection

    :raises InvalidObjectIdError: If the given entity_id is invalid
    :return: The query to feed to the collection's aggregate method. The value of list(result) should
             be passed to compute_breadcrumbs below.
    """
    return [
        {"$match": {"_id": CustomObjectId(entity_id)}},
        {
            "$graphLookup": {
                "from": collection_name,
                "startWith": "$parent_id",
                "connectFromField": "parent_id",
                "connectToField": "_id",
                "as": "ancestors",
                # maxDepth 0 will do one parent look up i.e. a trail length of 2
                "maxDepth": BREADCRUMBS_TRAIL_MAX_LENGTH - 2,
                "depthField": "level",
            }
        },
        {
            "$facet": {
                "root": [{"$project": {"_id": 1, "name": 1, "parent_id": 1}}],
                "ancestors": [
                    {"$unwind": "$ancestors"},
                    {
                        "$sort": {
                            "ancestors.level": -1,
                        },
                    },
                    {"$replaceRoot": {"newRoot": "$ancestors"}},
                    {"$project": {"_id": 1, "name": 1, "parent_id": 1}},
                ],
            }
        },
        {"$project": {"result": {"$concatArrays": ["$ancestors", "$root"]}}},
    ]


def compute_breadcrumbs(breadcrumb_query_result: list, entity_id: str, collection_name: str) -> BreadcrumbsGetSchema:
    """
    Process the result of running breadcrumb query using the pipeline returned by
    create_breadcrumbs_aggregation_pipeline above

    :param entity_id: ID of the entity the breadcrumbs are for. Should be the same as was used for
                      create_breadcrumbs_aggregation_pipeline (used for logging)
    :param breadcrumb_query_result: Result of the running the aggregation pipeline returned by
                                    create_breadcrumbs_aggregation_pipeline (used for logging)
    :param collection_name: Should be the same as the value passed to create_breadcrumbs_aggregation_pipeline
                            (used for logging)
    :raises DatabaseIntegrityError: If the query returned less than the maximum allowed trail while not
                                    giving the full trail - this indicates a parent_id is invalid or doesn't
                                    exist in the database which shouldn't occur
    :return: See BreadcrumbsGetSchema
    """

    logger.info("Querying breadcrumbs for entity with id '%s' in the collection '%s'", entity_id, collection_name)

    trail: list[tuple[str, str]] = []

    result = breadcrumb_query_result[0]["result"]
    if len(result) == 0:
        raise MissingRecordError(
            f"Entity with the ID '{entity_id}' was not found in the collection '{collection_name}'"
        )
    for element in result:
        trail.append((str(element["_id"]), element["name"]))
    full_trail = result[0]["parent_id"] is None

    # Ensure none of the parent_id's are invalid - if they are we wont get the full trail even though we are supposed
    # to
    if not full_trail and len(trail) != BREADCRUMBS_TRAIL_MAX_LENGTH:
        raise DatabaseIntegrityError(
            f"Unable to locate full trail for entity with id '{entity_id}' from the database "
            f"collection '{collection_name}'"
        )
    return BreadcrumbsGetSchema(trail=trail, full_trail=full_trail)
