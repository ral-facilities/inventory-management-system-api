"""
End-to-End tests for the system type router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import SYSTEM_TYPES_GET_DATA

import pytest
from fastapi.testclient import TestClient
from httpx import Response


class ListDSL:
    """Base class for list tests."""

    test_client: TestClient

    _get_response_system_type: Response

    @pytest.fixture(autouse=True)
    def setup_system_create_dsl(self, test_client):
        """Setup fixtures"""

        self.test_client = test_client

    def get_system_types(self) -> None:
        """Gets a list of system types."""

        self._get_response_system_type = self.test_client.get("/v1/system-types")
        print("HELLO")
        print(self._get_response_system_type)

    def check_get_systems_success(self, expected_system_types_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_system_types` gave a successful response with the expected data returned

        :param expected_system_types_get_data: List of dictionaries containing the expected system type data returned
                                               as would be required for `SystemTypeSchema`'s.
        """

        assert self._get_response_system_type.status_code == 200
        assert self._get_response_system_type.json() == expected_system_types_get_data


class TestList(ListDSL):
    """Tests for getting a list of systems."""

    def test_list(self):
        """Test getting a list of all system types."""

        self.get_system_types()
        self.check_get_systems_success(SYSTEM_TYPES_GET_DATA)
