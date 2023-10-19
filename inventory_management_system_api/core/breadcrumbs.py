"""
Useful functions for computing breadcrumbs
"""
import logging

from pymongo.collection import Collection

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DatabaseIntegrityError, MissingRecordError
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema

logger = logging.getLogger()


def query_breadcrumbs(entity_id: str, entity_collection: Collection, graph_lookup_from: str) -> BreadcrumbsGetSchema:
    """
    Query breadcrumbs for an entity given it's ID

    :param entity_id: ID of the entity to look up
    :param entity_collection: Collection for looking up entities - It is assumed that the entities have
                              an _id, _name and parent_id field
    :param graph_lookup_from: Value of "from" to use for the $graphLookup query - Should be the name of
                              the collection
    :raises InvalidObjectIdError: If the given entity_id is invalid
    :raises DatabaseIntegrityError: If the query returns a less than the maximum allowed trail while not
                                    giving the full trail - this indicates a parent_id is invalid or doesn't
                                    exist in the database which shouldn't occur
    :return: See BreadcrumbsGetSchema
    """

    trail: list[tuple[str, str]] = []

    result = list(
        entity_collection.aggregate(
            [
                {"$match": {"_id": CustomObjectId(entity_id)}},
                {
                    "$graphLookup": {
                        "from": graph_lookup_from,
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
        )
    )[0]["result"]
    if len(result) == 0:
        raise MissingRecordError(f"Entity with the ID {entity_id} was not found in the collection {graph_lookup_from}")
    for element in result:
        trail.append((str(element["_id"]), element["name"]))
    full_trail = result[0]["parent_id"] is None

    # Ensure none of the parent_id's are invalid - if they are we wont get the full trail even though we are supposed
    # to
    if not full_trail and len(trail) != BREADCRUMBS_TRAIL_MAX_LENGTH:
        raise DatabaseIntegrityError(
            f"Unable to locate full trail for entity with id '{entity_id}' from the database collection "
            f"'{graph_lookup_from}'"
        )
    return BreadcrumbsGetSchema(trail=trail, full_trail=full_trail)
