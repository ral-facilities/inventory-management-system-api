"""
End-to-End tests for the system router.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code

from test.conftest import add_ids_to_properties
from test.e2e.conftest import E2ETestHelpers, replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import USAGE_STATUS_POST_B
from test.e2e.test_catalogue_item import CATALOGUE_CATEGORY_POST_A, CATALOGUE_ITEM_POST_A
from test.e2e.test_item import ITEM_POST, MANUFACTURER_POST
from test.e2e.test_unit import UNIT_POST_A, UNIT_POST_B
from test.mock_data import (
    SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT,
    SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY,
    SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT,
    SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
)
from typing import Optional

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import Response

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH


class CreateDSL:
    """Base class for create tests."""

    test_client: TestClient

    _post_response: Response

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""

        self.test_client = test_client

    def post_system(self, system_post_data: dict) -> Optional[str]:
        """
        Posts a system with the given data and returns the id of the created system if successful.

        :param system_post_data: Dictionary containing the system data as would be required for a
                                 `SystemPostSchema`.
        :return: ID of the created system (or `None` if not successful).
        """

        self._post_response = self.test_client.post("/v1/systems", json=system_post_data)
        return self._post_response.json()["id"] if self._post_response.status_code == 201 else None

    def check_post_system_success(self, expected_system_get_data: dict) -> None:
        """
        Checks that a prior call to `post_system` gave a successful response with the expected data returned.

        :param expected_system_get_data: Dictionary containing the expected system data returned as would be required
                                         for a `SystemGetSchema`.
        """

        assert self._post_response.status_code == 201
        assert self._post_response.json() == expected_system_get_data

    def check_post_system_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `post_system` gave a failed response with the expected code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"] == detail

    def check_post_system_failed_with_validation_message(self, status_code: int, message: str) -> None:
        """
        Checks that a prior call to `post_system` gave a failed response with the expected code and pydantic
        validation error message.

        :param status_code: Expected status code of the response.
        :param message: Expected validation error message given in the response.
        """

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a system."""

    def test_create_with_only_required_values_provided(self):
        """Test creating a system with only required values provided."""

        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.check_post_system_success(SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_with_all_values_provided(self):
        """Test creating a system with all values provided."""

        self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.check_post_system_success(SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT)

    def test_create_with_valid_parent_id(self):
        """Test creating a system with a valid parent id."""

        parent_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id})
        self.check_post_system_success({**SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id})

    def test_create_with_non_existent_parent_id(self):
        """Test creating a system with a non-existent parent id."""

        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": str(ObjectId())})
        self.check_post_system_failed_with_detail(422, "The specified parent system does not exist")

    def test_create_with_invalid_parent_id(self):
        """Test creating a system with an invalid parent id."""

        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": "invalid-id"})
        self.check_post_system_failed_with_detail(422, "The specified parent system does not exist")

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a system with the same name as another within the parent system."""

        parent_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        # 2nd post should be the duplicate
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id})
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id})
        self.check_post_system_failed_with_detail(
            409, "A system with the same name already exists within the parent system"
        )

    def test_create_with_invalid_importance(self):
        """Test creating a system with an invalid importance."""

        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "importance": "invalid-importance"})
        self.check_post_system_failed_with_validation_message(422, "Input should be 'low', 'medium' or 'high'")


class GetDSL(CreateDSL):
    """Base class for get tests."""

    _get_response: Response

    def get_system(self, system_id: str):
        """
        Gets a system with the given id.

        :param system_id: ID of the system to be obtained.
        """

        self._get_response = self.test_client.get(f"/v1/systems/{system_id}")

    def check_get_system_success(self, expected_system_get_data: dict):
        """
        Checks that a prior call to `get_system` gave a successful response with the expected data returned.

        :param expected_system_get_data: Dictionary containing the expected system data returned as would be required
                                         for a `SystemGetSchema`.
        """

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_system_get_data

    def check_get_system_failed_with_detail(self, status_code: int, detail: str):
        """
        Checks that a prior call to `get_system` gave a failed response with the expected code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a system."""

    def test_get(self):
        """Test getting a system."""

        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.get_system(system_id)
        self.check_get_system_success(SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT)

    def test_get_with_non_existent_id(self):
        """Test getting a system with a non-existent id."""

        self.get_system(str(ObjectId()))
        self.check_get_system_failed_with_detail(404, "System not found")

    def test_get_with_invalid_id(self):
        """Test getting a system with an invalid id."""

        self.get_system("invalid-id")
        self.check_get_system_failed_with_detail(404, "System not found")


class GetBreadcrumbsDSL(GetDSL):
    """Base class for breadcrumbs tests."""

    _get_response: Response

    _posted_systems_get_data: list[dict]

    @pytest.fixture(autouse=True)
    def setup_breadcrumbs_dsl(self):
        """Setup fixtures"""

        self._posted_systems_get_data = []

    def post_nested_systems(self, number: int) -> list[Optional[str]]:
        """
        Posts the given number of nested systems where each successive one has the previous as its parent.

        :param number: Number of systems to create.
        :return: List of ids of the created systems.
        """

        parent_id = None
        for i in range(0, number):
            system_id = self.post_system(
                {**SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT, "name": f"System {i}", "parent_id": parent_id}
            )
            self._posted_systems_get_data.append(self._post_response.json())
            parent_id = system_id

        return [system["id"] for system in self._posted_systems_get_data]

    def get_system_breadcrumbs(self, system_id: str) -> None:
        """
        Gets a system's breadcrumbs with the given id.

        :param system_id: ID of the system to obtain the breadcrumbs of.
        """

        self._get_response = self.test_client.get(f"/v1/systems/{system_id}/breadcrumbs")

    def get_last_system_breadcrumbs(self) -> None:
        """Gets the last system posted's breadcrumbs."""

        self.get_system_breadcrumbs(self._post_response.json()["id"])

    def check_get_system_breadcrumbs_success(self, expected_trail_length: int, expected_full_trail: bool) -> None:
        """
        Checks that a prior call to 'get_system_breadcrumbs' gave a successful response with the expected data
        returned.

        :param expected_trail_length: Expected length of the breadcrumbs trail.
        :param expected_full_trail: Whether the expected trail is a full trail or not.
        """

        assert self._get_response.status_code == 200
        assert self._get_response.json() == {
            "trail": [
                [system["id"], system["name"]]
                # When the expected trail length is < the number of systems posted, only use the last
                for system in self._posted_systems_get_data[
                    (len(self._posted_systems_get_data) - expected_trail_length) :
                ]
            ],
            "full_trail": expected_full_trail,
        }

    def check_get_system_breadcrumbs_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `get_system_breadcrumbs` gave a failed response with the expected code and
        error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting a system's breadcrumbs."""

    def test_get_breadcrumbs_when_no_parent(self):
        """Test getting a system's breadcrumbs when the system has no parent."""

        self.post_nested_systems(1)
        self.get_last_system_breadcrumbs()
        self.check_get_system_breadcrumbs_success(expected_trail_length=1, expected_full_trail=True)

    def test_get_breadcrumbs_when_trail_length_less_than_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail should be less than the maximum trail
        length."""

        self.post_nested_systems(BREADCRUMBS_TRAIL_MAX_LENGTH - 1)
        self.get_last_system_breadcrumbs()
        self.check_get_system_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH - 1, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail should be equal to the maximum trail
        length."""

        self.post_nested_systems(BREADCRUMBS_TRAIL_MAX_LENGTH)
        self.get_last_system_breadcrumbs()
        self.check_get_system_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_greater_maximum(self):
        """Test getting a system's breadcrumbs when the full system trail exceeds the maximum trail length."""

        self.post_nested_systems(BREADCRUMBS_TRAIL_MAX_LENGTH + 1)
        self.get_last_system_breadcrumbs()
        self.check_get_system_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=False
        )

    def test_get_breadcrumbs_with_non_existent_id(self):
        """Test getting a system's breadcrumbs when given a non-existent system id."""

        self.get_system_breadcrumbs(str(ObjectId()))
        self.check_get_system_breadcrumbs_failed_with_detail(404, "System not found")

    def test_get_breadcrumbs_with_invalid_id(self):
        """Test getting a system's breadcrumbs when given an invalid system id."""

        self.get_system_breadcrumbs("invalid_id")
        self.check_get_system_breadcrumbs_failed_with_detail(404, "System not found")


class ListDSL(GetBreadcrumbsDSL):
    """Base class for list tests."""

    def get_systems(self, filters: dict) -> None:
        """
        Gets a list systems with the given filters.

        :param filters: Filters to use in the request.
        """

        self._get_response = self.test_client.get("/v1/systems", params=filters)

    def post_test_system_with_child(self) -> list[dict]:
        """
        Posts a system with a single child and returns their expected responses when returned by the list endpoint.

        :return: List of dictionaries containing the expected system data returned from a get endpoint in the form of a
                 `SystemGetSchema`.
        """

        parent_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id})

        return [SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT, {**SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id}]

    def check_get_systems_success(self, expected_systems_get_data: list[dict]) -> None:
        """
        Checks that a prior call to `get_systems` gave a successful response with the expected data returned.

        :param expected_systems_get_data: List of dictionaries containing the expected system data returned as would be
                                          required for `SystemGetSchema`'s.
        """

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_systems_get_data


class TestList(ListDSL):
    """Tests for getting a list of systems."""

    def test_list_with_no_filters(self):
        """
        Test getting a list of all systems with no filters provided.

        Posts a system with a child and expects both to be returned.
        """

        systems = self.post_test_system_with_child()
        self.get_systems(filters={})
        self.check_get_systems_success(systems)

    def test_list_with_parent_id_filter(self):
        """
        Test getting a list of all systems with a `parent_id` filter provided.

        Posts a system with a child and then filter using the `parent_id` expecting only the second system
        to be returned.
        """

        systems = self.post_test_system_with_child()
        self.get_systems(filters={"parent_id": systems[1]["parent_id"]})
        self.check_get_systems_success([systems[1]])

    def test_list_with_null_parent_id_filter(self):
        """
        Test getting a list of all systems with a `parent_id` filter of 'null' provided.

        Posts a system with a child and then filter using a `parent_id` of 'null' expecting only
        the first parent system to be returned.
        """

        systems = self.post_test_system_with_child()
        self.get_systems(filters={"parent_id": "null"})
        self.check_get_systems_success([systems[0]])

    def test_list_with_parent_id_filter_with_no_matching_results(self):
        """Test getting a list of all systems with a `parent_id` filter that returns no results."""

        self.get_systems(filters={"parent_id": str(ObjectId())})
        self.check_get_systems_success([])

    def test_list_with_invalid_parent_id_filter(self):
        """Test getting a list of all systems with an invalid `parent_id` filter returns no results."""

        self.get_systems(filters={"parent_id": "invalid-id"})
        self.check_get_systems_success([])


class UpdateDSL(ListDSL):
    """Base class for update tests."""

    _patch_response: Response

    def patch_system(self, system_id: str, system_patch_data: dict) -> None:
        """
        Updates a system with the given id.

        :param system_id: ID of the system to patch.
        :param system_patch_data: Dictionary containing the patch data as would be required for a `SystemPatchSchema`.
        """

        self._patch_response = self.test_client.patch(f"/v1/systems/{system_id}", json=system_patch_data)

    def check_patch_system_response_success(self, expected_system_get_data: dict) -> None:
        """
        Checks that a prior call to `patch_system` gave a successful response with the expected data returned.

        :param expected_system_get_data: Dictionary containing the expected system data returned as would be required
                                         for a `SystemGetSchema`.
        """

        assert self._patch_response.status_code == 200
        assert self._patch_response.json() == expected_system_get_data

        E2ETestHelpers.check_created_and_modified_times_updated_correctly(self._post_response, self._patch_response)

    def check_patch_system_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `patch_system` gave a failed response with the expected code and error message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._patch_response.status_code == status_code
        assert self._patch_response.json()["detail"] == detail


class TestUpdate(UpdateDSL):
    """Tests for updating a system."""

    def test_partial_update_all_fields(self):
        """Test updating every field of a system."""

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.patch_system(system_id, SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.check_patch_system_response_success(SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT)

    def test_partial_update_parent_id(self):
        """Test updating the `parent_id` of a system."""

        parent_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)

        self.patch_system(system_id, {"parent_id": parent_id})
        self.check_patch_system_response_success({**SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT, "parent_id": parent_id})

    def test_partial_update_parent_id_to_one_with_a_duplicate_name(self):
        """Test updating the `parent_id` of a system so that its name conflicts with one already in that other
        system."""

        # System with child
        parent_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "name": "Conflicting Name", "parent_id": parent_id})

        system_id = self.post_system({**SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT, "name": "Conflicting Name"})

        self.patch_system(system_id, {"parent_id": parent_id})
        self.check_patch_system_failed_with_detail(
            409, "A system with the same name already exists within the parent system"
        )

    def test_partial_update_parent_id_to_child_of_self(self):
        """Test updating the `parent_id` of a system to one of its own children."""

        system_ids = self.post_nested_systems(2)
        self.patch_system(system_ids[0], {"parent_id": system_ids[1]})
        self.check_patch_system_failed_with_detail(422, "Cannot move a system to one of its own children")

    def test_partial_update_parent_id_to_non_existent(self):
        """Test updating the `parent_id` of a system to a non-existent system."""

        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.patch_system(system_id, {"parent_id": str(ObjectId())})
        self.check_patch_system_failed_with_detail(422, "The specified parent system does not exist")

    def test_partial_update_parent_id_to_invalid_id(self):
        """Test updating the `parent_id` of a system to an invalid id."""

        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.patch_system(system_id, {"parent_id": "invalid-id"})
        self.check_patch_system_failed_with_detail(422, "The specified parent system does not exist")

    def test_partial_update_name_to_duplicate(self):
        """Test updating the name of a system to conflict with a pre-existing one."""

        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT)
        self.patch_system(system_id, {"name": SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY["name"]})
        self.check_patch_system_failed_with_detail(
            409, "A system with the same name already exists within the parent system"
        )

    def test_partial_update_name_capitalisation(self):
        """Test updating the capitalisation of the name of a system (to ensure it the check doesn't confuse with
        duplicates)."""

        system_id = self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "name": "Test system"})
        self.patch_system(system_id, {"name": "Test System"})
        self.check_patch_system_response_success(
            {**SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY, "name": "Test System", "code": "test-system"}
        )

    def test_partial_update_with_non_existent_id(self):
        """Test updating a non-existent system."""

        self.patch_system(str(ObjectId()), {})
        self.check_patch_system_failed_with_detail(404, "System not found")

    def test_partial_update_invalid_id(self):
        """Test updating a system with an invalid id."""

        self.patch_system("invalid-id", {})
        self.check_patch_system_failed_with_detail(404, "System not found")


class DeleteDSL(UpdateDSL):
    """Base class for delete tests."""

    _delete_response: Response

    def delete_system(self, system_id: str) -> None:
        """
        Deletes a system with the given id.

        :param system_id: ID of the system to be deleted.
        """

        self._delete_response = self.test_client.delete(f"/v1/systems/{system_id}")

    def check_delete_system_success(self) -> None:
        """Checks that a prior call to `delete_system` gave a successful response with the expected data returned."""

        assert self._delete_response.status_code == 204

    def check_delete_system_failed_with_detail(self, status_code: int, detail: str) -> None:
        """
        Checks that a prior call to `delete_system` gave a failed response with the expected code and error
        message.

        :param status_code: Expected status code of the response.
        :param detail: Expected detail given in the response.
        """

        assert self._delete_response.status_code == status_code
        assert self._delete_response.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a system."""

    def test_delete(self):
        """Test deleting a system."""

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.delete_system(system_id)
        self.check_delete_system_success()

        self.get_system(system_id)
        self.check_get_system_failed_with_detail(404, "System not found")

    def test_delete_with_child_system(self):
        """Test deleting a system with a child system."""

        system_ids = self.post_nested_systems(2)
        self.delete_system(system_ids[0])

        self.check_delete_system_failed_with_detail(409, "System has child elements and cannot be deleted")

    def test_delete_with_child_item(self):
        """Test deleting a system with a child system."""

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)

        # pylint:disable=fixme
        # TODO: This should be cleaned up in future
        # Create a child item
        # pylint: disable=duplicate-code
        response = self.test_client.post("/v1/units", json=UNIT_POST_A)
        unit_mm = response.json()

        response = self.test_client.post("/v1/units", json=UNIT_POST_B)
        unit_cm = response.json()

        units = [unit_mm, unit_cm]

        response = self.test_client.post(
            "/v1/catalogue-categories",
            json={
                **CATALOGUE_CATEGORY_POST_A,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_A["properties"], units
                ),
            },
        )
        catalogue_category = response.json()

        response = self.test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
        manufacturer_id = response.json()["id"]

        catalogue_item_post = {
            **CATALOGUE_ITEM_POST_A,
            "catalogue_category_id": catalogue_category["id"],
            "manufacturer_id": manufacturer_id,
            "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
        }
        response = self.test_client.post("/v1/catalogue-items", json=catalogue_item_post)
        catalogue_item_id = response.json()["id"]

        response = self.test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_B)
        usage_status_id = response.json()["id"]

        item_post = {
            **ITEM_POST,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
            "usage_status_id": usage_status_id,
            "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
        }
        self.test_client.post("/v1/items", json=item_post)
        # pylint: enable=duplicate-code

        self.delete_system(system_id)
        self.check_delete_system_failed_with_detail(409, "System has child elements and cannot be deleted")

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent system."""

        self.delete_system(str(ObjectId()))
        self.check_delete_system_failed_with_detail(404, "System not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a system with an invalid id."""

        self.delete_system("invalid_id")
        self.check_delete_system_failed_with_detail(404, "System not found")
