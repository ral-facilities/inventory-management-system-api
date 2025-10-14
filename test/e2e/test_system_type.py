"""
End-to-End tests for the system type router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import SYSTEM_TYPE_GET_DATA_OPERATIONAL, SYSTEM_TYPES_GET_DATA

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import Response


class GetDSL:
    """Base class for get_system_type tests."""

    test_client: TestClient
    _get_response_system_type: Response

    @pytest.fixture(autouse=True)
    def setup_system_type_create_dsl(self, test_client):
        """Setup fixtures"""

        self.test_client = test_client

    def get_system_type(self, system_type_id: str) -> None:
        """
        Gets a system type.

        :param system_type_id: ID of the system type.
        """
        self._get_response_system_type = self.test_client.get(f"/v1/system-types/{system_type_id}")

    def check_get_system_type_success(self, expected_system_type_get_data: dict) -> None:
        """
        Checks that a prior call to 'get_system_type' gave a successful response with the expected data
            returned.

        :param expected_system_type_get_data: Dictionary containing the expected system type data
                                            returned as would be required for 'SystemTypeSchema'.
        """

        assert self._get_response_system_type.status_code == 200
        assert self._get_response_system_type.json() == expected_system_type_get_data

    def check_get_system_type_failed_with_detail(self, status_code: int, detail: str):
        """
        Checks that a prior call to `get_system_type` gave a failed response with the expected code and error
            message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """
        assert self._get_response_system_type.status_code == status_code
        assert self._get_response_system_type.json()["detail"] == detail


class TestGetDSL(GetDSL):
    """Test getting a system type."""

    def test_get(self):
        """Tests getting a system type."""

        self.get_system_type(SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"])
        self.check_get_system_type_success(SYSTEM_TYPE_GET_DATA_OPERATIONAL)

    def test_get_with_non_existent_id(self):
        """Test getting a system type with a non-existent ID."""

        self.get_system_type(str(ObjectId()))
        self.check_get_system_type_failed_with_detail(404, "System type not found")

    def test_get_with_invalid_id(self):
        """Test getting a system type with an invalid ID."""

        self.get_system_type("invalid-id")
        self.check_get_system_type_failed_with_detail(404, "System type not found")


class ListDSL(GetDSL):
    """Base class for list tests."""

    def get_system_types(self) -> None:
        """Gets a list of system types."""

        self._get_response_system_type = self.test_client.get("/v1/system-types")

    def check_get_system_types_success(self, expected_system_types_get_data: list[dict]) -> None:
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
        self.check_get_system_types_success(SYSTEM_TYPES_GET_DATA)
