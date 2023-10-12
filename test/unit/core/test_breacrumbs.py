"""
Unit tests for the core/breadcrumbs.py functions
"""

from collections import namedtuple
from unittest.mock import Mock, call

import pytest

from inventory_management_system_api.core import breadcrumbs
from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    EntityNotFoundError,
    InvalidObjectIdError,
)
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService
from inventory_management_system_api.services.system import SystemService

MockEntity = namedtuple("MockEntity", "id parent_id code")

# Reverse order here so first look up always has parents
MOCK_ENTITIES = [
    MockEntity(id=f"id-{i}", parent_id=None if i == 0 else f"id-{i-1}", code=f"code-{i}")
    for i in range(0, BREADCRUMBS_TRAIL_MAX_LENGTH * 2)
][::-1]


@pytest.mark.parametrize(
    "mock_service,expected_entity_type",
    [(Mock(CatalogueCategoryService), "catalogue category"), (Mock(SystemService), "system")],
)
class TestComputeBreadcrumbsWhenValid:
    """Test compute_breadcrumbs functions correctly when it has no errors"""

    def _test_compute_breadcrumbs(self, mock_service, mock_entities, expected_trail_length, expected_full_trail):
        mock_service.get.side_effect = mock_entities
        result = breadcrumbs.compute_breadcrumbs(mock_entities[0].id, mock_service)

        # Maximum of BREADCRUMBS_TRAIL_MAX_LENGTH actually looked up via the service
        expected_entities_looked_up = (
            mock_entities
            if len(mock_entities) <= BREADCRUMBS_TRAIL_MAX_LENGTH
            else mock_entities[0:BREADCRUMBS_TRAIL_MAX_LENGTH]
        )

        assert mock_service.get.call_args_list == [call(mock_entity.id) for mock_entity in expected_entities_looked_up]
        assert mock_service.get.call_count == expected_trail_length
        assert result.trail == [(mock_entity.id, mock_entity.code) for mock_entity in expected_entities_looked_up[::-1]]
        assert result.full_trail is expected_full_trail

    # pylint:disable=W0613
    def test_compute_breadcrumbs_with_single_breadcrumb(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs functions correctly when there are no parent entities to look up
        """
        self._test_compute_breadcrumbs(
            mock_service=mock_service,
            mock_entities=[MOCK_ENTITIES[-1]],
            expected_trail_length=1,
            expected_full_trail=True,
        )

    def test_compute_breadcrumbs_with_maximum_trail_length(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs functions correctly when the breadcrumb trail length required is
        equal to the maximum
        """
        self._test_compute_breadcrumbs(
            mock_service=mock_service,
            # Want last BREADCRUMBS_TRAIL_MAX_LENGTH so last in trail has no parent
            mock_entities=MOCK_ENTITIES[-BREADCRUMBS_TRAIL_MAX_LENGTH:],
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH,
            expected_full_trail=True,
        )

    def test_compute_breadcrumbs_when_exceeding_maximum_trail_length(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs functions correctly when the breadcrumb trail length is longer than
        the maximum i.e. the full trail is not returned
        """
        self._test_compute_breadcrumbs(
            mock_service=mock_service,
            mock_entities=MOCK_ENTITIES,
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH,
            expected_full_trail=False,
        )

    def test_compute_breadcrumbs_when_first_entity_id_invalid(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs raises an InvalidObjectIdError when the first entity looked
        up has an invalid id
        """
        mock_error = InvalidObjectIdError("Some error message")
        mock_service.get.side_effect = mock_error

        with pytest.raises(InvalidObjectIdError) as exc:
            breadcrumbs.compute_breadcrumbs("entity_id", mock_service)

        assert str(exc.value) == str(mock_error)

    def test_compute_breadcrumbs_when_first_entity_not_found(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs raises an EntityNotFoundError when the first entity looked
        up doesn't exist
        """
        mock_service.get.side_effect = [None]

        with pytest.raises(EntityNotFoundError) as exc:
            breadcrumbs.compute_breadcrumbs("entity_id", mock_service)

        assert str(exc.value) == f"{expected_entity_type.capitalize()} with ID entity_id was not found"

    def test_compute_breadcrumbs_when_second_entity_id_invalid(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs raises a DatabaseIntegrityError when the second entity looked
        up has an invalid id
        """
        mock_error = InvalidObjectIdError("Some error message")
        mock_service.get.side_effect = [MOCK_ENTITIES[0], mock_error]

        with pytest.raises(DatabaseIntegrityError) as exc:
            breadcrumbs.compute_breadcrumbs("entity_id", mock_service)

        assert str(exc.value) == (
            f"{expected_entity_type.capitalize()} ID {MOCK_ENTITIES[1].id} was invalid while finding "
            "breadcrumbs for entity_id"
        )

    def test_compute_breadcrumbs_when_second_entity_not_found(self, mock_service, expected_entity_type):
        """
        Test compute_breadcrumbs raises a DatabaseIntegrityError when the second entity looked
        up doesn't exist
        """
        mock_service.get.side_effect = [MOCK_ENTITIES[0], None]

        with pytest.raises(DatabaseIntegrityError) as exc:
            breadcrumbs.compute_breadcrumbs("entity_id", mock_service)

        assert str(exc.value) == (
            f"{expected_entity_type.capitalize()} with ID {MOCK_ENTITIES[1].id} was not found while finding "
            "breadcrumbs for entity_id"
        )
