"""
End-to-End tests for the manufacturer router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.mock_data import (
    MANUFACTURER_GET_DATA_ALL_VALUES,
    MANUFACTURER_GET_DATA_REQUIRED_VALUES_ONLY,
    MANUFACTURER_POST_DATA_ALL_VALUES,
    MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
)
from typing import Optional

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import Response


class CreateDSL:
    """Base class for create tests."""

    test_client: TestClient

    _post_response_manufacturer: Response

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""
        self.test_client = test_client

    def post_manufacturer(self, manufacturer_post_data: dict) -> Optional[str]:
        """
        Posts a manufacturer with the given data, returns the ID of the created manufacturer if successful.

        :param manufacturer_post_data: Dictionary containing the manufacturer data as would be required for a
            `ManufacturerPostSchema`.
        :return: ID of the created manufacturer (or `None` if not successful).
        """
        self._post_response_manufacturer = self.test_client.post("/v1/manufacturers", json=manufacturer_post_data)
        return (
            self._post_response_manufacturer.json()["id"]
            if self._post_response_manufacturer.status_code == 201
            else None
        )

    def check_post_manufacturer_success(self, expected_manufacturer_get_data: dict) -> None:
        """
        Checks that a prior call to `post_manufacturer` gave a successful response with the expected data returned.

        :param expected_manufacturer_get_data: Dictionary containing the expected manufacturer data as would be required
            for a `ManufacturerSchema`.
        """
        assert self._post_response_manufacturer.status_code == 201
        assert self._post_response_manufacturer.json() == expected_manufacturer_get_data

    def check_post_manufacturer_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `post_manufacturer` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._post_response_manufacturer.status_code == status_code
        assert self._post_response_manufacturer.json()["detail"] == detail

    def check_post_manufacturer_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_manufacturers` gave a failed response with the expected code and pydantic
        validation error message.

        :param status_code: Expected status code to be returned.
        :param message: Expected pydantic validation error message to be returned.
        """
        assert self._post_response_manufacturer.status_code == status_code
        assert self._post_response_manufacturer.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a manufacturer."""

    def test_create_with_only_required_values_provided(self):
        """Test creating a manufacturer with only required values provided."""
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.check_post_manufacturer_success(MANUFACTURER_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_with_all_values_provided(self):
        """Test creating a manufacturer with all values provided."""
        self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)
        self.check_post_manufacturer_success(MANUFACTURER_GET_DATA_ALL_VALUES)

    def test_create_with_duplicate_name(self):
        """Test creating a manufacturer with the same name as another."""
        self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)
        self.check_post_manufacturer_failed_with_detail(409, "A manufacturer with the same name already exists")


class GetDSL(CreateDSL):
    """Base class for get tests."""

    _get_response_manufacturer = Response

    def get_manufacturer(self, manufacturer_id: str) -> None:
        """
        Gets a manufacturer with the given ID.

        :param manufacturer_id: ID of the manufacturer to be obtained.
        """
        self._get_response_manufacturer = self.test_client.get(f"/v1/manufacturers/{manufacturer_id}")

    def check_get_manufacturer_success(self, expected_manufacturer_get_data: dict) -> None:
        """
        Checks that a prior call to `get_manufacturer` gave a successful response with the expected data returned.

        :param expected_manufacturer_get_data: Dictionary containing the expected manufacturer data as would be required
            for a `ManufacturerSchema`.
        """
        assert self._get_response_manufacturer.status_code == 200
        assert self._get_response_manufacturer.json() == expected_manufacturer_get_data

    def check_get_manufacturer_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `get_manufacturer` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._get_response_manufacturer.status_code == status_code
        assert self._get_response_manufacturer.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a manufacturer."""

    def test_get(self):
        """Test getting a manufacturer."""
        manufacturer_id = self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)
        self.get_manufacturer(manufacturer_id)
        self.check_get_manufacturer_success(MANUFACTURER_GET_DATA_ALL_VALUES)

    def test_get_with_non_existent_id(self):
        """Test getting a manufacturer with a non-existent ID."""
        self.get_manufacturer(str(ObjectId()))
        self.check_get_manufacturer_failed_with_detail(404, "Manufacturer not found")

    def test_get_with_invalid_id(self):
        """Test getting a manufacturer with an invalid ID."""
        self.get_manufacturer("invalid-id")
        self.check_get_manufacturer_failed_with_detail(404, "Manufacturer not found")


class ListDSL(GetDSL):
    """Base class for list tests."""

    def get_manufacturers(self) -> None:
        """Gets a list of manufacturers."""
        self._get_response_manufacturer = self.test_client.get("/v1/manufacturers")

    def check_get_manufacturers_success(self, expected_manufacturers_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_manufacturers` gave a successful response with the expected data returned.

        :param expected_manufacturers_get_data: List of dictionaries containing the expected manufacturer data as would
            be required for a `ManufacturerSchema`.
        """
        assert self._get_response_manufacturer.status_code == 200
        assert self._get_response_manufacturer.json() == expected_manufacturers_get_data


class TestList(ListDSL):
    """Tests for getting a list of manufacturers."""

    def test_list(self):
        """Test getting a list of all manufacturers."""
        self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.get_manufacturers()
        self.check_get_manufacturers_success(
            [MANUFACTURER_GET_DATA_ALL_VALUES, MANUFACTURER_GET_DATA_REQUIRED_VALUES_ONLY]
        )

    def test_list_no_manufacturers(self):
        """Test getting a list of all manufacturers when there are no manufactuers."""
        self.get_manufacturers()
        self.check_get_manufacturers_success([])


class UpdateDSL(ListDSL):
    """Base class for update tests."""

    _patch_response_manufacturer: Response

    def patch_manufacturer(self, manufacturer_id: str, manufacturer_patch_data: dict) -> None:
        """
        Updates a manufacturer with the given ID.

        :param manufacturer_id: ID of the manufacturer to be updated.
        :param manufacturer_patch_data: Dictionary containing the manufacturer patch data as would be required for a
            `ManufacturerPatchSchema`.
        """
        self._patch_response_manufacturer = self.test_client.patch(
            f"/v1/manufacturers/{manufacturer_id}", json=manufacturer_patch_data
        )

    def check_patch_manufacturer_success(self, expected_manufacturer_get_data: dict) -> None:
        """
        Checks that a prior call to `patch_manufacturer` gave a successful response with the expected data returned.

        :param expected_manufacturer_get_data: Dictionaries containing the expected manufacturer data as would be
            required for a `ManufacturerSchema`.
        """
        assert self._patch_response_manufacturer.status_code == 200
        assert self._patch_response_manufacturer.json() == expected_manufacturer_get_data

    def check_patch_manufacturer_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that prior call to `patch_manufacturer` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._patch_response_manufacturer.status_code == status_code
        assert self._patch_response_manufacturer.json()["detail"] == detail


class TestUpdate(UpdateDSL):
    """Tests for updating a manufacturer."""

    def test_partial_update_all_fields(self):
        """Test updating every field of a manufacturer."""
        manufacturer_id = self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.patch_manufacturer(manufacturer_id, MANUFACTURER_POST_DATA_ALL_VALUES)
        self.check_patch_manufacturer_success(MANUFACTURER_GET_DATA_ALL_VALUES)

    def test_partial_update_name_to_duplicate(self):
        """Test updating the name of a manufacturer to conflict with a pre-existing one."""
        self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        system_id = self.post_manufacturer(MANUFACTURER_POST_DATA_ALL_VALUES)
        self.patch_manufacturer(system_id, {"name": MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY["name"]})
        self.check_patch_manufacturer_failed_with_detail(409, "A manufacturer with the same name already exists")

    def test_partial_update_name_capitalisation(self):
        """Test updating a manufacturer when the capitalisation of the name is different (to ensure it the check doesn't
        confuse with duplicates)."""
        manufacturer_id = self.post_manufacturer(
            {**MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY, "name": "Test manufacturer"}
        )
        self.patch_manufacturer(manufacturer_id, {"name": "Test Manufacturer"})
        self.check_patch_manufacturer_success(
            {**MANUFACTURER_GET_DATA_REQUIRED_VALUES_ONLY, "name": "Test Manufacturer", "code": "test-manufacturer"}
        )

    def test_partial_update_with_non_existent_id(self):
        """Test updating a non-existent manufacturer."""
        self.patch_manufacturer(str(ObjectId()), {})
        self.check_patch_manufacturer_failed_with_detail(404, "Manufacturer not found")

    def test_partial_update_invalid_id(self):
        """Test updating a manufacturer with an invalid ID."""
        self.patch_manufacturer("invalid-id", {})
        self.check_patch_manufacturer_failed_with_detail(404, "Manufacturer not found")


class DeleteDSL(UpdateDSL):
    """Base class for delete tests."""

    _delete_response_manufacturer: Response

    def delete_manufacturer(self, manufacturer_id: str) -> None:
        """
        Delete a manufacturer with the given ID.

        :param manufacturer_id: ID of the manufacturer to be deleted.
        """
        self._delete_response_manufacturer = self.test_client.delete(f"/v1/manufacturers/{manufacturer_id}")

    def check_delete_manufacturer_success(self) -> None:
        """Checks that a prior call to `delete_manufacturer` gave a successful response."""
        assert self._delete_response_manufacturer.status_code == 204

    def check_delete_manufacturer_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_manufacturer` gave a failed response with the expected code and detail.

        :param status_code: Expected status code to be returned.
        :param detail: Expected detail to be returned.
        """
        assert self._delete_response_manufacturer.status_code == status_code
        assert self._delete_response_manufacturer.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a manufacturer."""

    def test_delete(self):
        """Test deleting a manufacturer."""
        manufacturer_id = self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)
        self.delete_manufacturer(manufacturer_id)
        self.check_delete_manufacturer_success()

        self.get_manufacturer(manufacturer_id)
        self.check_get_manufacturer_failed_with_detail(404, "Manufacturer not found")

    def test_delete_when_part_of_catalogue_item(self):
        """Test deleting a manufacturer when it is part of a catalogue item."""
        manufacturer_id = self.post_manufacturer(MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY)

        # pylint:disable=fixme
        # TODO: Reuse catalogue category and item data once catalogue category and item tests have been refactored
        catalogue_category_post = {"name": "Category A", "is_leaf": True, "properties": []}
        response = self.test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
        catalogue_category_id = response.json()["id"]

        catalogue_item_post = {
            "name": "Catalogue Item A",
            "catalogue_category_id": catalogue_category_id,
            "cost_gbp": 129.99,
            "days_to_replace": 2.0,
            "is_obsolete": False,
            "manufacturer_id": manufacturer_id,
        }
        self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)

        self.delete_manufacturer(manufacturer_id)
        self.check_delete_manufacturer_failed_with_detail(
            409, "The specified manufacturer is a part of a catalogue item"
        )

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent manufacturer."""
        self.delete_manufacturer(str(ObjectId()))
        self.check_delete_manufacturer_failed_with_detail(404, "Manufacturer not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a manufacturer with invalid ID."""
        self.delete_manufacturer("invalid-id")
        self.check_delete_manufacturer_failed_with_detail(404, "Manufacturer not found")
