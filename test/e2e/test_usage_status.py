"""
End-to-End tests for the usage status router
"""

from typing import Optional

from test.e2e.test_catalogue_category_property import CATALOGUE_ITEM_POST_A, ITEM_POST
from test.mock_data import (
    CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
    SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    USAGE_STATUS_GET_DATA_NEW,
    USAGE_STATUS_GET_DATA_USED,
    USAGE_STATUS_POST_DATA_NEW,
    USAGE_STATUS_POST_DATA_USED,
)

from bson import ObjectId

import pytest
from fastapi.testclient import TestClient
from httpx import Response


class CreateDSL:
    """Base class for create tests."""

    test_client: TestClient

    _post_response_usage_status: Response

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""
        self.test_client = test_client

    def post_usage_status(self, usage_status_post_data: dict) -> Optional[str]:
        """
        Posts a usage status with the given data, returns the ID of the created usage status if successful.

        :param usage_status_post_data: Dictionary containing the usage status data as would be required for a
                                                            `UsageStatusPostSchema`.
        :return: ID of the created usage status (or `None` if not successful).
        """
        self._post_response_usage_status = self.test_client.post("/v1/usage-statuses", json=usage_status_post_data)
        return (
            self._post_response_usage_status.json()["id"]
            if self._post_response_usage_status.status_code == 201
            else None
        )

    def check_post_usage_status_success(self, expected_usage_status_get_data: dict) -> None:
        """
        Checks that a prior call to `post_usage_status` gave a successful response with the expected data returned.

        :param expected_usage_status_get_data: Dictionary containing the expected usage status data as would be required
                                                                          for a `UsageStatusSchema`.
        """
        assert self._post_response_usage_status.status_code == 201
        assert self._post_response_usage_status.json() == expected_usage_status_get_data

    def check_post_usage_status_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `post_usage_status` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._post_response_usage_status.status_code == status_code
        assert self._post_response_usage_status.json()["detail"] == detail


class TestCreate(CreateDSL):
    """Tests for creating a usage status."""

    def test_create_usage_status(self):
        """Test creating a usage status"""

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.check_post_usage_status_success(USAGE_STATUS_GET_DATA_NEW)

    def test_create_usage_status_with_duplicate_value(self):
        """Test creating a usage status with a duplicate value."""

        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.check_post_usage_status_failed_with_detail(409, "A usage status with the same value already exists")


class GetDSL(CreateDSL):
    """Base class for get tests"""

    _get_response_usage_status = Response

    def get_usage_status(self, usage_status_id: str) -> None:
        """
        Gets a usage status with the given ID.

        :param usage_status_id: ID of the usage status to be obtained.
        """
        self._get_response_usage_status = self.test_client.get(f"/v1/usage-statuses/{usage_status_id}")

    def check_get_usage_status_success(self, expected_usage_status_get_data: dict) -> None:
        """
        Checks that a prior call to `get_usage_status` gave a successful response with the expected data returned.

        :param expected_usage_status_get_data: Dictionary containing the expected usage status data as would be required
                                                                           for a `UsageStatusSchema`.
        """
        assert self._get_response_usage_status.status_code == 200
        assert self._get_response_usage_status.json() == expected_usage_status_get_data

    def check_get_usage_status_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `get_usage_status` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._get_response_usage_status.status_code == status_code
        assert self._get_response_usage_status.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a usage status."""

    def test_get(self):
        """Test getting a usage status."""
        usage_status_id = self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.get_usage_status(usage_status_id)
        self.check_get_usage_status_success(USAGE_STATUS_GET_DATA_NEW)

    def test_get_with_non_existent_id(self):
        """Test getting a usage status with a non-existent ID."""
        self.get_usage_status(str(ObjectId()))
        self.check_get_usage_status_failed_with_detail(404, "Usage status not found")

    def test_get_with_invalid_id(self):
        """Test getting a usage status with an invalid ID."""
        self.get_usage_status("invalid-id")
        self.check_get_usage_status_failed_with_detail(404, "Usage status not found")


class ListDSL(GetDSL):
    """Base class for list tests."""

    def get_usage_statuses(self) -> None:
        """Gets a list of usage statuses."""
        self._get_response_usage_status = self.test_client.get("/v1/usage-statuses")

    def check_get_usage_statuses_success(self, expected_usage_statuss_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_usage_statuses` gave a successful response with the expected data returned.

        :param expected_usage_statuss_get_data: List of dictionaries containing the expected usage status data as would
        be required for a `UsageStatusSchema`.
        """
        assert self._get_response_usage_status.status_code == 200
        assert self._get_response_usage_status.json() == expected_usage_statuss_get_data


class TestList(ListDSL):
    """Tests for getting a list of usage statuses."""

    def test_list(self):
        """Test getting a list of all usage statuses."""
        self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.post_usage_status(USAGE_STATUS_POST_DATA_USED)
        self.get_usage_statuses()
        self.check_get_usage_statuses_success([USAGE_STATUS_GET_DATA_NEW, USAGE_STATUS_GET_DATA_USED])

    def test_list_no_usage_statuss(self):
        """Test getting a list of all usage statuses when there are no usage statuses."""
        self.get_usage_statuses()
        self.check_get_usage_statuses_success([])


class DeleteDSL(ListDSL):
    """Base class for delete tests."""

    _delete_response_usage_status: Response

    def delete_usage_status(self, usage_status_id: str) -> None:
        """
        Delete a usage status with the given ID.

        :param usage_status_id: ID of the usage status to be deleted.
        """
        self._delete_response_usage_status = self.test_client.delete(f"/v1/usage-statuses/{usage_status_id}")

    def check_delete_usage_status_success(self) -> None:
        """Checks that a prior call to `delete_usage_status` gave a successful response."""
        assert self._delete_response_usage_status.status_code == 204

    def check_delete_usage_status_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_usage_status` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._delete_response_usage_status.status_code == status_code
        assert self._delete_response_usage_status.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a usage status."""

    def test_delete(self):
        """Test deleting a usage status."""
        usage_status_id = self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)
        self.delete_usage_status(usage_status_id)
        self.check_delete_usage_status_success()

        self.get_usage_status(usage_status_id)
        self.check_get_usage_status_failed_with_detail(404, "Usage status not found")

    def test_delete_when_part_of_item(self):
        """Test deleting a usage status when it is part of an item."""
        usage_status_id = self.post_usage_status(USAGE_STATUS_POST_DATA_NEW)

        # pylint: disable=duplicate-code
        response = self.test_client.post(
            "/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES
        )
        catalogue_category = response.json()

        response = self.test_client.post("/v1/systems", json=SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        system_id = response.json()["id"]

        response = self.test_client.post("/v1/manufacturers", json=MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)

        manufacturer_id = response.json()["id"]

        catalogue_item_post = {
            **CATALOGUE_ITEM_POST_A,
            "properties": [],
            "catalogue_category_id": catalogue_category["id"],
            "manufacturer_id": manufacturer_id,
        }

        response = self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)
        catalogue_item = response.json()

        item_post = {
            **ITEM_POST,
            "properties": [],
            "catalogue_item_id": catalogue_item["id"],
            "system_id": system_id,
            "usage_status_id": usage_status_id,
        }
        # pylint: enable=duplicate-code
        self.test_client.post("/v1/items", json=item_post)

        self.delete_usage_status(usage_status_id)
        self.check_delete_usage_status_failed_with_detail(409, "The specified usage status is part of an Item")

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent usage status."""
        self.delete_usage_status(str(ObjectId()))
        self.check_delete_usage_status_failed_with_detail(404, "Usage status not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a usage status with invalid ID."""
        self.delete_usage_status("invalid-id")
        self.check_delete_usage_status_failed_with_detail(404, "Usage status not found")
