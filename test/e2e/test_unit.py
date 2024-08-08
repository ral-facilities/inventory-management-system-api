"""
End-to-End tests for the Unit router
"""

from typing import Optional

from test.mock_data import (
    CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    UNIT_GET_DATA_CM,
    UNIT_GET_DATA_MM,
    UNIT_POST_DATA_CM,
    UNIT_POST_DATA_MM,
)

from bson import ObjectId

import pytest
from fastapi.testclient import TestClient
from httpx import Response


class CreateDSL:
    """Base class for create tests."""

    test_client: TestClient

    _post_response: Response

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""
        self.test_client = test_client

    def post_unit(self, unit_post_data: dict) -> Optional[str]:
        """
        Posts a unit with the given data, returns the ID of the created unit if successful.

        :param unit_post_data: Dictionary containing the unit data as would be required for a
            `UnitPostSchema`.
        :return: ID of the created unit (or `None` if not successful).
        """
        self._post_response = self.test_client.post("/v1/units", json=unit_post_data)
        return self._post_response.json()["id"] if self._post_response.status_code == 201 else None

    def check_post_unit_success(self, expected_unit_get_data: dict) -> None:
        """
        Checks that a prior call to `post_unit` gave a successful response with the expected data returned.

        :param expected_unit_get_data: Dictionary containing the expected unit data as would be required
            for a `UnitSchema`.
        """
        assert self._post_response.status_code == 201
        assert self._post_response.json() == expected_unit_get_data

    def check_post_unit_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `post_unit` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"] == detail

    def check_post_unit_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_unit` gave a failed response with the expected code and pydantic
        validation error message.

        :param status_code: Expected status code to be returned.
        :param message: Expected pydantic validation error message to be returned.
        """
        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a unit."""

    def test_create_unit(self):
        """Test creating a unit"""

        self.post_unit(UNIT_POST_DATA_MM)
        self.check_post_unit_success(UNIT_GET_DATA_MM)

    def test_create_unit_with_duplicate_name(self):
        """Test creating a unit with a duplicate name"""

        self.post_unit(UNIT_POST_DATA_MM)
        self.post_unit(UNIT_POST_DATA_MM)
        self.check_post_unit_failed_with_detail(409, "A unit with the same value already exists")


class GetDSL(CreateDSL):
    """Base class for get tests"""

    _get_response = Response

    def get_unit(self, unit_id: str) -> None:
        """
        Gets a unit with the given ID.

        :param unit_id: ID of the unit to be obtained.
        """
        self._get_response = self.test_client.get(f"/v1/units/{unit_id}")

    def check_get_unit_success(self, expected_unit_get_data: dict) -> None:
        """
        Checks that a prior call to `get_unit` gave a successful response with the expected data returned.

        :param expected_unit_get_data: Dictionary containing the expected unit data as would be required
            for a `UnitSchema`.
        """
        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_unit_get_data

    def check_get_unit_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `get_unit` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a unit."""

    def test_get(self):
        """Test getting a unit."""
        unit_id = self.post_unit(UNIT_POST_DATA_MM)
        self.get_unit(unit_id)
        self.check_get_unit_success(UNIT_GET_DATA_MM)

    def test_get_with_non_existent_id(self):
        """Test getting a unit with a non-existent ID."""
        self.get_unit(str(ObjectId()))
        self.check_get_unit_failed_with_detail(404, "Unit not found")

    def test_get_with_invalid_id(self):
        """Test getting a unit with an invalid ID."""
        self.get_unit("invalid-id")
        self.check_get_unit_failed_with_detail(404, "Unit not found")


class ListDSL(GetDSL):
    """Base class for list tests."""

    def get_units(self) -> None:
        """Gets a list of units."""
        self._get_response = self.test_client.get("/v1/units")

    def check_get_units_success(self, expected_units_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_units` gave a successful response with the expected data returned.

        :param expected_units_get_data: List of dictionaries containing the expected unit data as would
            be required for a `UnitSchema`.
        """
        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_units_get_data


class TestList(ListDSL):
    """Tests for getting a list of units."""

    def test_list(self):
        """Test getting a list of all units."""
        self.post_unit(UNIT_POST_DATA_MM)
        self.post_unit(UNIT_POST_DATA_CM)
        self.get_units()
        self.check_get_units_success([UNIT_GET_DATA_MM, UNIT_GET_DATA_CM])

    def test_list_no_units(self):
        """Test getting a list of all units when there are no units."""
        self.get_units()
        self.check_get_units_success([])


class DeleteDSL(ListDSL):
    """Base class for delete tests."""

    _delete_response: Response

    def delete_unit(self, unit_id: str) -> None:
        """
        Delete a unit with the given ID.

        :param unit_id: ID of the unit to be deleted.
        """
        self._delete_response = self.test_client.delete(f"/v1/units/{unit_id}")

    def check_delete_unit_success(self) -> None:
        """Checks that a prior call to `delete_unit` gave a successful response."""
        assert self._delete_response.status_code == 204

    def check_delete_unit_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_unit` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._delete_response.status_code == status_code
        assert self._delete_response.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a unit."""

    def test_delete(self):
        """Test deleting a unit."""
        unit_id = self.post_unit(UNIT_POST_DATA_MM)
        self.delete_unit(unit_id)
        self.check_delete_unit_success()

        self.get_unit(unit_id)
        self.check_get_unit_failed_with_detail(404, "Unit not found")

    def test_delete_when_part_of_catalogue_category(self):
        """Test deleting a unit when it is part of a catalogue item."""
        unit_id = self.post_unit(UNIT_POST_DATA_MM)

        catalogue_category_data = {
            **CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
            "properties": [
                {
                    **CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
                    "unit_id": unit_id,
                }
            ],
        }

        self.test_client.post("/v1/catalogue-categories", json=catalogue_category_data)

        self.delete_unit(unit_id)
        self.check_delete_unit_failed_with_detail(409, "The specified unit is part of a Catalogue category")

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent unit."""
        self.delete_unit(str(ObjectId()))
        self.check_delete_unit_failed_with_detail(404, "Unit not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a unit with invalid ID."""
        self.delete_unit("invalid-id")
        self.check_delete_unit_failed_with_detail(404, "Unit not found")
