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


def list_query(parent_id: Optional[str], entity_type: str) -> dict:
    """
    Constructs filters for a pymongo collection based on a given `parent_id`
    also logging the action

    :param parent_id: `parent_id` to filter `entity_type` by (Converted to a uuid here - a string value of "null"
                      indicates that the `parent_id` should be null, not that there shouldn't be a query)
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


def create_system_tree_aggregation_pipeline(
    parent_id: str, 
    max_subsystems: Optional[int] = None
) -> list:
    """
    Returns an aggregate query for collecting system tree data with an optimization for maximum subsystems.

    :param parent_id: ID of the root system to start the tree.
    :param max_subsystems: Maximum allowed subsystems.

    :return: Aggregation pipeline for MongoDB.
    """
    pipeline = [
        # Step 1: Match the root system by its ID
        {"$match": {"_id": CustomObjectId(parent_id)}},

        # Step 2: Recursively fetch subsystems with $graphLookup
        {
            "$graphLookup": {
                "from": "systems",
                "startWith": "$_id",
                "connectFromField": "_id",
                "connectToField": "parent_id",
                "as": "subsystems"
            }
        },

        # Step 3: Filter the subsystems based on the max_subsystems count
        {
            "$addFields": {
                "subsystems": {
                    "$slice": ["$subsystems", max_subsystems] if max_subsystems is not None else "$subsystems"
                }
            }
        },

        # Step 4: Calculate the total number of subsystems after limiting
        {
            "$addFields": {
                "subsystemCount": {"$size": "$subsystems"}
            }
        },

        # Step 5: Add the `fullTree` field based on whether the limit is exceeded
        {
            "$addFields": {
                "fullTree": {
                    "$cond": {
                        "if": {"$lte": ["$subsystemCount", max_subsystems] if max_subsystems is not None else True},
                        "then": True,
                        "else": False
                    }
                }
            }
        },

        # Step 6: Fetch all items belonging to the systems and subsystems
        {
            "$lookup": {
                "from": "items",
                "localField": "subsystems._id",
                "foreignField": "system_id",
                "as": "allItems"
            }
        },

        # Step 7: Fetch root system items
        {
            "$lookup": {
                "from": "items",
                "localField": "_id",
                "foreignField": "system_id",
                "as": "rootItems"
            }
        },

        # Step 8: Fetch details for catalogue items referenced in all items
        {
            "$lookup": {
                "from": "catalogue_items",
                "localField": "allItems.catalogue_item_id",
                "foreignField": "_id",
                "as": "catalogueItemDetails"
            }
        },

        # Step 9: Fetch catalogue item details for root items
        {
            "$lookup": {
                "from": "catalogue_items",
                "localField": "rootItems.catalogue_item_id",
                "foreignField": "_id",
                "as": "rootCatalogueItemDetails"
            }
        },

        # Step 10: Restructure subsystems and group items by catalogue items
        {
            "$addFields": {
                "subsystems": {
                    "$map": {
                        "input": "$subsystems",
                        "as": "subsystem",
                        "in": {
                            "_id": "$$subsystem._id",
                            "name": "$$subsystem.name",
                            "description": "$$subsystem.description",
                            "location": "$$subsystem.location",
                            "owner": "$$subsystem.owner",
                            "importance": "$$subsystem.importance",
                            "code": "$$subsystem.code",
                            "parent_id": "$$subsystem.parent_id",
                            "catalogue_items": {
                                "$map": {
                                    "input": {
                                        "$filter": {
                                            "input": "$allItems",
                                            "as": "item",
                                            "cond": {"$eq": ["$$item.system_id", "$$subsystem._id"]}
                                        }
                                    },
                                    "as": "item",
                                    "in": {
                                        "_id": "$$item.catalogue_item_id",
                                        "catalogue_item": {
                                            "$arrayElemAt": [
                                                {
                                                    "$filter": {
                                                        "input": "$catalogueItemDetails",
                                                        "as": "catalogueItem",
                                                        "cond": {"$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"]}
                                                    }
                                                },
                                                0
                                            ]
                                        },
                                        "itemsQuantity": {
                                            "$size": {
                                                "$filter": {
                                                    "input": "$allItems",
                                                    "as": "innerItem",
                                                    "cond": {"$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"]}
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "subsystems": []
                        }
                    }
                }
            }
        },

        # Step 11: Final projection for clarity
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "location": 1,
                "owner": 1,
                "importance": 1,
                "code": 1,
                "parent_id": 1,
                "catalogue_items": {
                    "$map": {
                        "input": {
                            "$filter": {
                                "input": "$rootItems",
                                "as": "item",
                                "cond": {"$eq": ["$$item.system_id", "$_id"]}
                            }
                        },
                        "as": "item",
                        "in": {
                            "_id": "$$item.catalogue_item_id",
                            "catalogue_item": {
                                "$arrayElemAt": [
                                    {
                                        "$filter": {
                                            "input": "$rootCatalogueItemDetails",
                                            "as": "catalogueItem",
                                            "cond": {"$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"]}
                                        }
                                    },
                                    0
                                ]
                            },
                            "itemsQuantity": {
                                "$size": {
                                    "$filter": {
                                        "input": "$rootItems",
                                        "as": "innerItem",
                                        "cond": {"$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"]}
                                    }
                                }
                            }
                        }
                    }
                },
                "subsystems": 1,
                "fullTree": 1  # Include the fullTree field in the output
            }
        }
    ]

    return pipeline

# def create_system_tree_aggregation_pipeline(
#     parent_id: str, 
#     max_subsystems: Optional[int] = None
# ) -> list:
#     """
#     Returns an aggregate query for collecting system tree data with an optimization for maximum subsystems.

#     :param parent_id: ID of the root system to start the tree.
#     :param max_subsystems: Maximum allowed subsystems.

#     :return: Aggregation pipeline for MongoDB.
#     """
#     pipeline = [
#         # Step 1: Match the root system by its ID
#         {"$match": {"_id": CustomObjectId(parent_id)}},

#         # Step 2: Recursively fetch subsystems with $graphLookup
#         {
#             "$graphLookup": {
#                 "from": "systems",
#                 "startWith": "$_id",
#                 "connectFromField": "_id",
#                 "connectToField": "parent_id",
#                 "as": "subsystems",
#                  "maxDepth": max_subsystems,  # Set a max depth limit for recursion
#                 "restrictSearchWithMatch": {}  # Optional, to further restrict recursion conditions if needed
                
#             }
#         },

#         # Step 3: Calculate the total number of subsystems
#         {
#             "$addFields": {
#                 "subsystemCount": {"$size": "$subsystems"}
#             }
#         },

#         # Step 4: Add the `fullTree` field based on whether the limit is exceeded
#         {
#             "$addFields": {
#                 "fullTree": {
#                     "$cond": {
#                         "if": {"$lte": ["$subsystemCount", max_subsystems] if max_subsystems is not None else True},
#                         "then": True,
#                         "else": False
#                     }
#                 }
#             }
#         },

#         # Step 5: Fetch all items belonging to the systems and subsystems
#         {
#             "$lookup": {
#                 "from": "items",
#                 "localField": "subsystems._id",
#                 "foreignField": "system_id",
#                 "as": "allItems"
#             }
#         },

#         # Step 6: Fetch root system items
#         {
#             "$lookup": {
#                 "from": "items",
#                 "localField": "_id",
#                 "foreignField": "system_id",
#                 "as": "rootItems"
#             }
#         },

#         # Step 7: Fetch details for catalogue items referenced in all items
#         {
#             "$lookup": {
#                 "from": "catalogue_items",
#                 "localField": "allItems.catalogue_item_id",
#                 "foreignField": "_id",
#                 "as": "catalogueItemDetails"
#             }
#         },

#         # Step 8: Fetch catalogue item details for root items
#         {
#             "$lookup": {
#                 "from": "catalogue_items",
#                 "localField": "rootItems.catalogue_item_id",
#                 "foreignField": "_id",
#                 "as": "rootCatalogueItemDetails"
#             }
#         },

#         # Step 9: Restructure subsystems and group items by catalogue items
#         {
#             "$addFields": {
#                 "subsystems": {
#                     "$map": {
#                         "input": "$subsystems",
#                         "as": "subsystem",
#                         "in": {
#                             "_id": "$$subsystem._id",
#                             "name": "$$subsystem.name",
#                             "description": "$$subsystem.description",
#                             "location": "$$subsystem.location",
#                             "owner": "$$subsystem.owner",
#                             "importance": "$$subsystem.importance",
#                             "code": "$$subsystem.code",
#                             "parent_id": "$$subsystem.parent_id",
#                             "catalogue_items": {
#                                 "$map": {
#                                     "input": {
#                                         "$filter": {
#                                             "input": "$allItems",
#                                             "as": "item",
#                                             "cond": {"$eq": ["$$item.system_id", "$$subsystem._id"]}
#                                         }
#                                     },
#                                     "as": "item",
#                                     "in": {
#                                         "_id": "$$item.catalogue_item_id",
#                                         "catalogue_item": {
#                                             "$arrayElemAt": [
#                                                 {
#                                                     "$filter": {
#                                                         "input": "$catalogueItemDetails",
#                                                         "as": "catalogueItem",
#                                                         "cond": {"$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"]}
#                                                     }
#                                                 },
#                                                 0
#                                             ]
#                                         },
#                                         "itemsQuantity": {
#                                             "$size": {
#                                                 "$filter": {
#                                                     "input": "$allItems",
#                                                     "as": "innerItem",
#                                                     "cond": {"$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"]}
#                                                 }
#                                             }
#                                         }
#                                     }
#                                 }
#                             },
#                             "subsystems": []
#                         }
#                     }
#                 }
#             }
#         },

#         # Step 10: Final projection for clarity
#         {
#             "$project": {
#                 "_id": 1,
#                 "name": 1,
#                 "description": 1,
#                 "location": 1,
#                 "owner": 1,
#                 "importance": 1,
#                 "code": 1,
#                 "parent_id": 1,
#                 "catalogue_items": {
#                     "$map": {
#                         "input": {
#                             "$filter": {
#                                 "input": "$rootItems",
#                                 "as": "item",
#                                 "cond": {"$eq": ["$$item.system_id", "$_id"]}
#                             }
#                         },
#                         "as": "item",
#                         "in": {
#                             "_id": "$$item.catalogue_item_id",
#                             "catalogue_item": {
#                                 "$arrayElemAt": [
#                                     {
#                                         "$filter": {
#                                             "input": "$rootCatalogueItemDetails",
#                                             "as": "catalogueItem",
#                                             "cond": {"$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"]}
#                                         }
#                                     },
#                                     0
#                                 ]
#                             },
#                             "itemsQuantity": {
#                                 "$size": {
#                                     "$filter": {
#                                         "input": "$rootItems",
#                                         "as": "innerItem",
#                                         "cond": {"$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"]}
#                                     }
#                                 }
#                             }
#                         }
#                     }
#                 },
#                 "subsystems": 1,
#                 "fullTree": 1  # Include the fullTree field in the output
#             }
#         }
#     ]

#     return pipeline

# def create_system_tree_aggregation_pipeline(parent_id: str) -> list:
#     """
#     Returns an aggregate query for collecting system tree data including systems, subsystems, items, and catalogue items.

#     :param parent_id: ID of the system to look up the system tree for.

#     :return: The query to feed to the collection's aggregate method.
#     """
#     return [
#         # Step 1: Match the root system by its ID
#         { "$match": { "_id": CustomObjectId(parent_id) } },

#         # Step 2: Recursively fetch subsystems using $graphLookup
#         {
#             "$graphLookup": {
#                 "from": "systems",             # Collection to traverse
#                 "startWith": "$_id",           # Starting with the root system ID
#                 "connectFromField": "_id",     # Traversing from `_id`
#                 "connectToField": "parent_id", # To `parent_id` for hierarchy
#                 "as": "subsystems"             # Output field containing all recursive subsystems
#             }
#         },

#         # Step 3: Fetch all items belonging to the systems and subsystems
#         {
#             "$lookup": {
#                 "from": "items",
#                 "localField": "subsystems._id", # Match subsystem IDs with `items.system_id`
#                 "foreignField": "system_id",
#                 "as": "allItems"
#             }
#         },

#         # Step 4: Fetch root system items
#         {
#             "$lookup": {
#                 "from": "items",
#                 "localField": "_id", # Match root system ID with `items.system_id`
#                 "foreignField": "system_id",
#                 "as": "rootItems"
#             }
#         },

#         # Step 5: Fetch details for catalogue items referenced in all items
#         {
#             "$lookup": {
#                 "from": "catalogue_items",
#                 "localField": "allItems.catalogue_item_id", # Match item catalogue IDs
#                 "foreignField": "_id",
#                 "as": "catalogueItemDetails"
#             }
#         },

#         # Step 6: Fetch catalogue item details for root items
#         {
#             "$lookup": {
#                 "from": "catalogue_items",
#                 "localField": "rootItems.catalogue_item_id", # Match root item catalogue IDs
#                 "foreignField": "_id",
#                 "as": "rootCatalogueItemDetails"
#             }
#         },

#         # Step 7: Restructure to group items by catalogue items and include subsystems recursively
#         {
#             "$addFields": {
#                 "subsystems": {
#                     "$map": {
#                         "input": "$subsystems",
#                         "as": "subsystem",
#                         "in": {
#                             "_id": "$$subsystem._id",
#                             "name": "$$subsystem.name",
#                             "description": "$$subsystem.description",
#                             "location": "$$subsystem.location",
#                             "owner": "$$subsystem.owner",
#                             "importance": "$$subsystem.importance",
#                             "code": "$$subsystem.code",
#                             "parent_id": "$$subsystem.parent_id",
#                             "catalogue_items": {
#                                 "$map": {
#                                     "input": {
#                                         "$filter": {
#                                             "input": "$allItems", # Filter items belonging to the current subsystem
#                                             "as": "item",
#                                             "cond": { "$eq": ["$$item.system_id", "$$subsystem._id"] }
#                                         }
#                                     },
#                                     "as": "item",
#                                     "in": {
#                                         "_id": "$$item.catalogue_item_id",
#                                         "catalogue_item": {
#                                             "$arrayElemAt": [
#                                                 {
#                                                     "$filter": {
#                                                         "input": "$catalogueItemDetails", # Match catalogue item details
#                                                         "as": "catalogueItem",
#                                                         "cond": { "$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"] }
#                                                     }
#                                                 },
#                                                 0
#                                             ]
#                                         },
#                                         "itemsQuantity": {
#                                             "$size": {
#                                                 "$filter": {
#                                                     "input": "$allItems", # Count items for this catalogue_item_id
#                                                     "as": "innerItem",
#                                                     "cond": { "$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"] }
#                                                 }
#                                             }
#                                         }
#                                     }
#                                 }
#                             },
#                             "subsystems": []  # Placeholder for recursive subsystems
#                         }
#                     }
#                 }
#             }
#         },

#         # Step 8: Final projection for clarity
#         {
#             "$project": {
#                 "_id": 1,
#                 "name": 1,
#                 "description": 1,
#                 "location": 1,
#                 "owner": 1,
#                 "importance": 1,
#                 "code": 1,
#                 "parent_id": 1,
#                 "catalogue_items": {
#                     "$map": {
#                         "input": {
#                             "$filter": {
#                                 "input": "$rootItems", # Filter items belonging to the current system
#                                 "as": "item",
#                                 "cond": { "$eq": ["$$item.system_id", "$_id"] }
#                             }
#                         },
#                         "as": "item",
#                         "in": {
#                             "_id": "$$item.catalogue_item_id",
#                             "catalogue_item": {
#                                 "$arrayElemAt": [
#                                     {
#                                         "$filter": {
#                                             "input": "$rootCatalogueItemDetails", # Match root catalogue item details
#                                             "as": "catalogueItem",
#                                             "cond": { "$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"] }
#                                         }
#                                     },
#                                     0
#                                 ]
#                             },
#                             "itemsQuantity": {
#                                 "$size": {
#                                     "$filter": {
#                                         "input": "$rootItems", # Count root items for the catalogue_item_id
#                                         "as": "innerItem",
#                                         "cond": { "$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"] }
#                                     }
#                                 }
#                             }
#                         }
#                     }
#                 },
#                 "subsystems": 1
#             }
#         }
#     ]

# def create_system_tree_aggregation_pipeline_2(
#     parent_id: str, 
#     max_subsystems: Optional[int] = None, 
#     max_depth: Optional[int] = None, 
#     current_depth: int = 0, 
#     subsystems_cutoff_point: Optional[int] = None
# ) -> list:
#     """
#     Returns an aggregate query for collecting system tree data with optimizations for depth, subsystem limits, and cutoff points.

#     :param parent_id: ID of the root system to start the tree.
#     :param max_subsystems: Maximum allowed subsystems.
#     :param max_depth: Maximum depth of recursion.
#     :param current_depth: Current recursion depth (default: 0).
#     :param subsystems_cutoff_point: Cutoff point for total subsystems.

#     :return: Aggregation pipeline for MongoDB.
#     """
#     pipeline = [
#         # Step 1: Match the root system by its ID
#         {"$match": {"_id": CustomObjectId(parent_id)}},

#         # Step 2: Add a depth field to manage recursion depth
#         {"$addFields": {"currentDepth": current_depth}},

#         # Step 3: Recursively fetch subsystems with $graphLookup, respecting maxDepth
#         {
#             "$graphLookup": {
#                 "from": "systems",
#                 "startWith": "$_id",
#                 "connectFromField": "_id",
#                 "connectToField": "parent_id",
#                 "as": "subsystems",
#                 "maxDepth": max_depth if max_depth is not None else 100,
#                 "depthField": "depth"
#             }
#         },

#         # Step 4: Limit total subsystems using $setWindowFields (requires MongoDB 5.0+)
#         {
#             "$setWindowFields": {
#                 "partitionBy": None,
#                 "sortBy": {"_id": 1},
#                 "output": {
#                     "subsystemCount": {"$count": {}}
#                 }
#             }
#         },

#         # Step 5: Filter out systems exceeding cutoff points
#         {
#             "$match": {
#                 "$expr": {
#                     "$and": [
#                         {"$lte": ["$currentDepth", max_depth]} if max_depth is not None else {},
#                         {"$lte": ["$subsystemCount", max_subsystems]} if max_subsystems is not None else {},
#                         {"$lte": ["$subsystemCount", subsystems_cutoff_point]} if subsystems_cutoff_point is not None else {}
#                     ]
#                 }
#             }
#         },

#         # Step 6: Fetch all items belonging to the systems and subsystems
#         {
#             "$lookup": {
#                 "from": "items",
#                 "localField": "subsystems._id",
#                 "foreignField": "system_id",
#                 "as": "allItems"
#             }
#         },

#         # Step 7: Fetch root system items
#         {
#             "$lookup": {
#                 "from": "items",
#                 "localField": "_id",
#                 "foreignField": "system_id",
#                 "as": "rootItems"
#             }
#         },

#         # Step 8: Fetch details for catalogue items referenced in all items
#         {
#             "$lookup": {
#                 "from": "catalogue_items",
#                 "localField": "allItems.catalogue_item_id",
#                 "foreignField": "_id",
#                 "as": "catalogueItemDetails"
#             }
#         },

#         # Step 9: Fetch catalogue item details for root items
#         {
#             "$lookup": {
#                 "from": "catalogue_items",
#                 "localField": "rootItems.catalogue_item_id",
#                 "foreignField": "_id",
#                 "as": "rootCatalogueItemDetails"
#             }
#         },

#         # Step 10: Restructure subsystems and group items by catalogue items
#         {
#             "$addFields": {
#                 "subsystems": {
#                     "$map": {
#                         "input": "$subsystems",
#                         "as": "subsystem",
#                         "in": {
#                             "_id": "$$subsystem._id",
#                             "name": "$$subsystem.name",
#                             "description": "$$subsystem.description",
#                             "location": "$$subsystem.location",
#                             "owner": "$$subsystem.owner",
#                             "importance": "$$subsystem.importance",
#                             "code": "$$subsystem.code",
#                             "parent_id": "$$subsystem.parent_id",
#                             "catalogue_items": {
#                                 "$map": {
#                                     "input": {
#                                         "$filter": {
#                                             "input": "$allItems",
#                                             "as": "item",
#                                             "cond": {"$eq": ["$$item.system_id", "$$subsystem._id"]}
#                                         }
#                                     },
#                                     "as": "item",
#                                     "in": {
#                                         "_id": "$$item.catalogue_item_id",
#                                         "catalogue_item": {
#                                             "$arrayElemAt": [
#                                                 {
#                                                     "$filter": {
#                                                         "input": "$catalogueItemDetails",
#                                                         "as": "catalogueItem",
#                                                         "cond": {"$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"]}
#                                                     }
#                                                 },
#                                                 0
#                                             ]
#                                         },
#                                         "itemsQuantity": {
#                                             "$size": {
#                                                 "$filter": {
#                                                     "input": "$allItems",
#                                                     "as": "innerItem",
#                                                     "cond": {"$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"]}
#                                                 }
#                                             }
#                                         }
#                                     }
#                                 }
#                             },
#                             "subsystems": []
#                         }
#                     }
#                 }
#             }
#         },

#         # Step 11: Final projection for clarity
#         {
#             "$project": {
#                 "_id": 1,
#                 "name": 1,
#                 "description": 1,
#                 "location": 1,
#                 "owner": 1,
#                 "importance": 1,
#                 "code": 1,
#                 "parent_id": 1,
#                 "catalogue_items": {
#                     "$map": {
#                         "input": {
#                             "$filter": {
#                                 "input": "$rootItems",
#                                 "as": "item",
#                                 "cond": {"$eq": ["$$item.system_id", "$_id"]}
#                             }
#                         },
#                         "as": "item",
#                         "in": {
#                             "_id": "$$item.catalogue_item_id",
#                             "catalogue_item": {
#                                 "$arrayElemAt": [
#                                     {
#                                         "$filter": {
#                                             "input": "$rootCatalogueItemDetails",
#                                             "as": "catalogueItem",
#                                             "cond": {"$eq": ["$$catalogueItem._id", "$$item.catalogue_item_id"]}
#                                         }
#                                     },
#                                     0
#                                 ]
#                             },
#                             "itemsQuantity": {
#                                 "$size": {
#                                     "$filter": {
#                                         "input": "$rootItems",
#                                         "as": "innerItem",
#                                         "cond": {"$eq": ["$$innerItem.catalogue_item_id", "$$item.catalogue_item_id"]}
#                                     }
#                                 }
#                             }
#                         }
#                     }
#                 },
#                 "subsystems": 1
#             }
#         }
#     ]

#     return pipeline

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
