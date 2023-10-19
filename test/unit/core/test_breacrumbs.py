"""
Unit tests for the core/breadcrumbs.py functions
"""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core import breadcrumbs
from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidObjectIdError,
    MissingRecordError,
)

MOCK_AGGREGATE_RESPONSE_LESS_THAN_MAX_LENGTH = [
    {
        "result": [
            {"_id": f"entity-id-{i}", "name": f"entity-name-{i}", "parent_id": None if i == 0 else f"entity-id-{i-1}"}
            for i in range(0, BREADCRUMBS_TRAIL_MAX_LENGTH)
        ]
    }
]
MOCK_AGGREGATE_RESPONSE_GREATER_THAN_MAX_LENGTH = [
    {
        "result": [
            {"_id": f"entity-id-{i}", "name": f"entity-name-{i}", "parent_id": f"entity-id-{i-1}"}
            for i in range(10, 10 + BREADCRUMBS_TRAIL_MAX_LENGTH)
        ]
    }
]
MOCK_AGGREGATE_RESPONSE_NON_EXISTENT_ID = [{"result": []}]
MOCK_AGGREGATE_RESPONSE_INVALID_PARENT_IN_DB = [
    {
        "result": [
            {"_id": f"entity-id-{i}", "name": f"entity-name-{i}", "parent_id": f"entity-id-{i-1}"}
            for i in range(10, 8 + BREADCRUMBS_TRAIL_MAX_LENGTH)
        ]
    }
]


class TestComputeBreadcrumbsWhenValid:
    """Test query_breadcrumbs functions correctly when it has no errors"""

    def _get_expected_pipeline(self, entity_id: str, graph_lookup_from: str):
        """Returns the aggregate pipeline expected given an entity_id and graph_lookup_from values"""
        return [
            # pylint: disable=duplicate-code
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
            # pylint: enable=duplicate-code
        ]

    def _test_query_breadcrumbs(
        self, mock_aggregate_response, expected_trail: list[tuple[str, str]], expected_full_trail: bool
    ):
        """Utility function to test query_breadcrumbs given the mock aggregate pipeline response and
        expected breadcrumbs output"""
        entity_id = str(ObjectId())
        mock_entity_collection = MagicMock()
        graph_lookup_from = MagicMock()
        mock_entity_collection.aggregate.return_value = mock_aggregate_response
        expected_pipeline = self._get_expected_pipeline(entity_id, graph_lookup_from)

        result = breadcrumbs.query_breadcrumbs(
            entity_id=entity_id, entity_collection=mock_entity_collection, graph_lookup_from=graph_lookup_from
        )

        mock_entity_collection.aggregate.assert_called_once_with(expected_pipeline)

        assert result.trail == expected_trail
        assert result.full_trail is expected_full_trail

    def test_query_breadcrumbs(self):
        """
        Test query_breadcrumbs functions correctly
        """
        self._test_query_breadcrumbs(
            mock_aggregate_response=MOCK_AGGREGATE_RESPONSE_LESS_THAN_MAX_LENGTH,
            expected_trail=[
                (entity["_id"], entity["name"]) for entity in MOCK_AGGREGATE_RESPONSE_LESS_THAN_MAX_LENGTH[0]["result"]
            ],
            expected_full_trail=True,
        )

    def test_query_breadcrumbs_when_maximum_trail_length_exceeded(self):
        """
        Test query_breadcrumbs functions correctly when the maximum trail length is exceeded
        """
        self._test_query_breadcrumbs(
            mock_aggregate_response=MOCK_AGGREGATE_RESPONSE_GREATER_THAN_MAX_LENGTH,
            expected_trail=[
                (entity["_id"], entity["name"])
                for entity in MOCK_AGGREGATE_RESPONSE_GREATER_THAN_MAX_LENGTH[0]["result"]
            ],
            expected_full_trail=False,
        )

    def test_query_breadcrumbs_when_entity_not_found(self):
        """
        Test query_breadcrumbs functions correctly when the given entity_id is not found in the database
        """
        entity_id = str(ObjectId())
        mock_entity_collection = MagicMock()
        graph_lookup_from = MagicMock()
        expected_pipeline = self._get_expected_pipeline(entity_id, graph_lookup_from)

        mock_entity_collection.aggregate.return_value = MOCK_AGGREGATE_RESPONSE_NON_EXISTENT_ID

        with pytest.raises(MissingRecordError) as exc:
            breadcrumbs.query_breadcrumbs(
                entity_id=entity_id, entity_collection=mock_entity_collection, graph_lookup_from=graph_lookup_from
            )

        mock_entity_collection.aggregate.assert_called_once_with(expected_pipeline)
        assert str(exc.value) == f"Entity with the ID {entity_id} was not found in the collection {graph_lookup_from}"

    def test_query_breadcrumbs_when_entity_id_is_invalid(self):
        """
        Test query_breadcrumbs functions correctly when the given entity_id is invalid
        """
        entity_id = "invalid"
        mock_entity_collection = MagicMock()
        graph_lookup_from = MagicMock()

        mock_entity_collection.aggregate.return_value = MOCK_AGGREGATE_RESPONSE_NON_EXISTENT_ID

        with pytest.raises(InvalidObjectIdError) as exc:
            breadcrumbs.query_breadcrumbs(
                entity_id=entity_id, entity_collection=mock_entity_collection, graph_lookup_from=graph_lookup_from
            )

        mock_entity_collection.aggregate.assert_not_called()
        assert str(exc.value) == f"Invalid ObjectId value '{entity_id}'"

    def test_query_breadcrumbs_when_invalid_parent_in_db(self):
        """
        Test query_breadcrumbs functions correctly when there is an invalid parent id in the database
        """
        entity_id = str(ObjectId())
        mock_entity_collection = MagicMock()
        graph_lookup_from = MagicMock()
        expected_pipeline = self._get_expected_pipeline(entity_id, graph_lookup_from)

        mock_entity_collection.aggregate.return_value = MOCK_AGGREGATE_RESPONSE_INVALID_PARENT_IN_DB

        with pytest.raises(DatabaseIntegrityError) as exc:
            breadcrumbs.query_breadcrumbs(
                entity_id=entity_id, entity_collection=mock_entity_collection, graph_lookup_from=graph_lookup_from
            )

        mock_entity_collection.aggregate.assert_called_once_with(expected_pipeline)
        assert str(exc.value) == (
            f"Unable to locate full trail for entity with id '{entity_id}' from the database collection "
            f"'{graph_lookup_from}'"
        )
