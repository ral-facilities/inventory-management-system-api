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


def list_query(id_fields: dict[str, Optional[str]], entity_type: str) -> dict:
    """
    Constructs filters for a pymongo collection based on a given list of ID values to filter by while also logging the
    action.

    :param id_fields: List of ID filters to filter `entity_type` by. Each key value is the name of the ID field,
                      and each value is the value to filter by. The value is converted to a uuid here - a string value
                      of "null" indicates that the relevant ID should be null, not that there shouldn't be a query on
                      it.
    :param entity_type: Name of the entity type e.g. catalogue categories/systems (Used for logging)
    :return: Dictionary representing the query to pass to a pymongo's Collection `find` function or aggregate pipeline
             match stage.
    """
    query = {}
    for field_name, field_value in id_fields.items():
        if field_value:
            query[field_name] = None if field_value == "null" else CustomObjectId(field_value)

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
        # The following ensures that just a list of the full breadcrumbs results are returned with only the
        # necessary information in order from the top level down
        {
            "$facet": {
                # Keep only these parameters
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
    Processes the result of running breadcrumb query using the pipeline returned by
    create_breadcrumbs_aggregation_pipeline above

    :param entity_id: ID of the entity the breadcrumbs are for. Should be the same as was used for
                      create_breadcrumbs_aggregation_pipeline (used for error messages)
    :param breadcrumb_query_result: Result of running the aggregation pipeline returned by
                                    create_breadcrumbs_aggregation_pipeline
    :param collection_name: Should be the same as the value passed to create_breadcrumbs_aggregation_pipeline
                            (used for error messages)
    :raises MissingRecordError: If the entity with id 'entity_id' isn't found in the database
    :raises DatabaseIntegrityError: If the query returned less than the maximum allowed trail while not
                                    giving the full trail - this indicates a `parent_id` is invalid or doesn't
                                    exist in the database which shouldn't occur
    :return: See BreadcrumbsGetSchema
    """

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


def create_move_check_aggregation_pipeline(entity_id: str, destination_id: str, collection_name: str) -> list:
    """
    Returns an aggregate query for checking whether an entity has been requested to move to one of its own children

    :param entity_id: ID of the entity being moved
    :param destination_id: ID of the entity it is being moved to (i.e. the new parent_id)

    :raises InvalidObjectIdError: If the given entity_id or destination_id is invalid
    :return: The query to feed to the collection's aggregate method. The value of list(result) should
             be passed to is_valid_move_result below.
    """
    return [
        {"$match": {"_id": CustomObjectId(destination_id)}},
        {
            "$graphLookup": {
                "from": collection_name,
                "startWith": "$parent_id",
                "connectFromField": "parent_id",
                "connectToField": "_id",
                "as": "ancestors",
                "depthField": "level",
                # Stop if hit the entity itself, no need to check further
                "restrictSearchWithMatch": {"_id": {"$ne": CustomObjectId(entity_id)}},
            }
        },
        # The following ensures that just a list of the parents containing only the parent_id's are returned
        # in order from the top level down
        {
            "$facet": {
                # Keep only these parameters
                "root": [{"$project": {"parent_id": 1}}],
                "ancestors": [
                    {"$unwind": "$ancestors"},
                    {
                        "$sort": {
                            "ancestors.level": -1,
                        },
                    },
                    {"$replaceRoot": {"newRoot": "$ancestors"}},
                    {"$project": {"parent_id": 1}},
                ],
            }
        },
        {"$project": {"result": {"$concatArrays": ["$ancestors", "$root"]}}},
    ]


def is_valid_move_result(move_parent_check_result: list) -> bool:
    """
    Processes the result of running the query returned by create_move_check_aggregation_pipeline above and returns
    whether it represents a valid move

    :param move_parent_check_result: Result of running the aggregation pipeline returned by
                                     create_move_check_aggregation_pipeline
    :return: True if the move is valid, False when the move destination is a child of the entity being moved
    """
    result = move_parent_check_result[0]["result"]
    return len(result) > 0 and result[0]["parent_id"] is None
