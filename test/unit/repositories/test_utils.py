"""
Unit tests for the `utils` in /repositories
"""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH
from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.repositories import utils

MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH = [
    {
        "result": [
            {"_id": f"entity-id-{i}", "name": f"entity-name-{i}", "parent_id": None if i == 0 else f"entity-id-{i-1}"}
            for i in range(0, BREADCRUMBS_TRAIL_MAX_LENGTH)
        ]
    }
]
MOCK_BREADCRUMBS_QUERY_RESULT_GREATER_THAN_MAX_LENGTH = [
    {
        "result": [
            {"_id": f"entity-id-{i}", "name": f"entity-name-{i}", "parent_id": f"entity-id-{i-1}"}
            for i in range(10, 10 + BREADCRUMBS_TRAIL_MAX_LENGTH)
        ]
    }
]
MOCK_BREADCRUMBS_QUERY_RESULT_NON_EXISTENT_ID = [{"result": []}]
MOCK_BREADCRUMBS_QUERY_RESULT_INVALID_PARENT_IN_DB = [
    {
        "result": [
            {"_id": f"entity-id-{i}", "name": f"entity-name-{i}", "parent_id": f"entity-id-{i-1}"}
            for i in range(10, 8 + BREADCRUMBS_TRAIL_MAX_LENGTH)
        ]
    }
]

MOCK_MOVE_QUERY_RESULT_VALID = [
    {"result": [{"_id": f"entity-id-{i}", "parent_id": None if i == 0 else f"entity-id-{i-1}"} for i in range(0, 5)]}
]

MOCK_MOVE_QUERY_RESULT_INVALID = [
    {"result": [{"_id": f"entity-id-{i}", "parent_id": f"entity-id-{i-1}"} for i in range(10, 15)]}
]

MOCK_MOVE_QUERY_RESULT_NON_EXISTENT_ID = [{"result": []}]


class TestListQuery:
    """Test `list_query` functions correctly."""

    def test_list_query(self):
        """Tests that `list_query` functions correctly when given valid ID values."""

        id_fields = {"id1": str(ObjectId()), "id2": "null", "id3": None}
        result = utils.list_query(id_fields, entity_type="test")

        assert result == {"id1": CustomObjectId(id_fields["id1"]), "id2": None}

    def test_list_query_with_invalid_id(self):
        """Tests that `list_query` raises an error when a given ID is invalid."""

        id_fields = {"id1": "invalid_id"}

        with pytest.raises(InvalidObjectIdError) as exc:
            utils.list_query(id_fields, entity_type="test")

        assert str(exc.value) == f"Invalid ObjectId value '{id_fields["id1"]}'"


class TestCreateBreadcrumbsAggregationPipeline:
    """Test `create_breadcrumbs_aggregation_pipeline` functions correctly."""

    # Only test error here - exact query tested in e2e test
    def test_create_breadcrumbs_aggregation_pipeline_when_entity_id_is_invalid(self):
        """Tests that `create_breadcrumbs_aggregation_pipeline` raises an error when the given entity id is invalid."""
        entity_id = "invalid"
        collection_name = MagicMock()

        with pytest.raises(InvalidObjectIdError) as exc:
            utils.create_breadcrumbs_aggregation_pipeline(entity_id=entity_id, collection_name=collection_name)

        assert str(exc.value) == f"Invalid ObjectId value '{entity_id}'"


class TestComputeBreadcrumbs:
    """Test `compute_breadcrumbs` functions correctly."""

    def _test_compute_breadcrumbs(
        self, breadcrumb_query_result: list, expected_trail: list[tuple[str, str]], expected_full_trail: bool
    ):
        """Utility function to test `compute_breadcrumbs` given the breadcrumb_query_result response and
        expected breadcrumbs output."""
        entity_id = str(ObjectId())
        collection_name = MagicMock()

        result = utils.compute_breadcrumbs(
            entity_id=entity_id, breadcrumb_query_result=breadcrumb_query_result, collection_name=collection_name
        )

        assert result.trail == expected_trail
        assert result.full_trail is expected_full_trail

    def test_compute_breadcrumbs(self):
        """Test `compute_breadcrumbs` functions correctly."""
        self._test_compute_breadcrumbs(
            breadcrumb_query_result=MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH,
            expected_trail=[
                (entity["_id"], entity["name"])
                for entity in MOCK_BREADCRUMBS_QUERY_RESULT_LESS_THAN_MAX_LENGTH[0]["result"]
            ],
            expected_full_trail=True,
        )

    def test_compute_breadcrumbs_when_maximum_trail_length_exceeded(self):
        """Test `compute_breadcrumbs` functions correctly when the maximum trail length is exceeded."""
        self._test_compute_breadcrumbs(
            breadcrumb_query_result=MOCK_BREADCRUMBS_QUERY_RESULT_GREATER_THAN_MAX_LENGTH,
            expected_trail=[
                (entity["_id"], entity["name"])
                for entity in MOCK_BREADCRUMBS_QUERY_RESULT_GREATER_THAN_MAX_LENGTH[0]["result"]
            ],
            expected_full_trail=False,
        )

    def test_compute_breadcrumbs_when_entity_not_found(self):
        """Test `compute_breadcrumbs` functions correctly when the given entity_id is not found in the database."""
        entity_id = str(ObjectId())
        collection_name = MagicMock()

        with pytest.raises(MissingRecordError) as exc:
            utils.compute_breadcrumbs(
                entity_id=entity_id,
                breadcrumb_query_result=MOCK_BREADCRUMBS_QUERY_RESULT_NON_EXISTENT_ID,
                collection_name=collection_name,
            )

        assert str(exc.value) == f"Entity with the ID '{entity_id}' was not found in the collection '{collection_name}'"

    def test_compute_breadcrumbs_when_invalid_parent_in_db(self):
        """Test `compute_breadcrumbs` functions correctly when there is an invalid parent id in the database."""
        entity_id = str(ObjectId())
        collection_name = MagicMock()

        with pytest.raises(DatabaseIntegrityError) as exc:
            utils.compute_breadcrumbs(
                entity_id=entity_id,
                breadcrumb_query_result=MOCK_BREADCRUMBS_QUERY_RESULT_INVALID_PARENT_IN_DB,
                collection_name=collection_name,
            )

        assert str(exc.value) == (
            f"Unable to locate full trail for entity with id '{entity_id}' from the database collection "
            f"'{collection_name}'"
        )


class TestCreateMoveCheckAggregationPipeline:
    """Test `create_move_check_aggregation_pipeline` functions correctly"""

    # Only test errors here - exact query tested in e2e test
    def test_create_move_check_aggregation_pipeline_when_entity_id_is_invalid(self):
        """Tests that `create_move_check_aggregation_pipeline` raises an error when the given entity id is invalid."""
        entity_id = "invalid"
        destination_id = str(ObjectId())
        collection_name = MagicMock()

        with pytest.raises(InvalidObjectIdError) as exc:
            utils.create_move_check_aggregation_pipeline(
                entity_id=entity_id, destination_id=destination_id, collection_name=collection_name
            )

        assert str(exc.value) == f"Invalid ObjectId value '{entity_id}'"

    def test_create_move_check_aggregation_pipeline_when_destination_id_is_invalid(self):
        """Tests that `create_move_check_aggregation_pipeline` raises an error when the given destination id is
        invalid."""
        entity_id = str(ObjectId())
        destination_id = "invalid"
        collection_name = MagicMock()

        with pytest.raises(InvalidObjectIdError) as exc:
            utils.create_move_check_aggregation_pipeline(
                entity_id=entity_id, destination_id=destination_id, collection_name=collection_name
            )

        assert str(exc.value) == f"Invalid ObjectId value '{destination_id}'"


class TestIsValidMoveResult:
    """Test `is_valid_move_result` functions correctly."""

    def test_is_valid_move_result_when_valid(self):
        """Test `is_valid_move_result` functions correctly when the result is valid."""
        assert utils.is_valid_move_result(MOCK_MOVE_QUERY_RESULT_VALID) is True

    def test_is_valid_move_result_when_invalid(self):
        """Test `is_valid_move_result` functions correctly when the result is invalid."""
        assert utils.is_valid_move_result(MOCK_MOVE_QUERY_RESULT_INVALID) is False

    def test_is_valid_move_result_when_entity_not_found(self):
        """Test `is_valid_move_result` functions correctly when the entity ID doesn't exist in the database to begin
        with."""
        assert utils.is_valid_move_result(MOCK_MOVE_QUERY_RESULT_NON_EXISTENT_ID) is False
