"""
End-to-End tests for the System router
"""

from test.conftest import add_ids_to_properties
from test.e2e.conftest import replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import (
    CREATED_MODIFIED_VALUES_EXPECTED,
    SYSTEM_POST_A,
    SYSTEM_POST_A_EXPECTED,
    SYSTEM_POST_B,
    SYSTEM_POST_B_EXPECTED,
    SYSTEM_POST_C,
    USAGE_STATUS_POST_B,
)
from test.e2e.test_catalogue_item import CATALOGUE_CATEGORY_POST_A, CATALOGUE_ITEM_POST_A
from test.e2e.test_item import ITEM_POST, MANUFACTURER_POST
from test.e2e.test_unit import UNIT_POST_A, UNIT_POST_B
from typing import Any, Optional
from unittest.mock import ANY

import pytest
from bson import ObjectId
from fastapi import Response
from fastapi.testclient import TestClient

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH

# TODO: Unify with others - could perhaps even reuse here too
SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY = {
    "name": "System Test Required Values Only",
    "importance": "low",
}

SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY = {
    **SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "description": None,
    "location": None,
    "owner": None,
    "code": "system-test-required-values-only",
}

SYSTEM_POST_DATA_ALL_VALUES = {
    **SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    "name": "System Test All Values",
    "parent_id": None,
    "description": "Test description",
    "location": "Test location",
    "owner": "Test owner",
}

SYSTEM_GET_DATA_ALL_VALUES = {
    **SYSTEM_POST_DATA_ALL_VALUES,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "system-test-all-values",
}


class CreateDSL:
    """Base class for create tests"""

    test_client: TestClient

    _post_response: Response

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        """Setup fixtures"""

        self.test_client = test_client

    def post_system(self, system_post_data: dict) -> Optional[str]:
        """Posts a System with the given data, returns the id of the created system if successful"""
        self._post_response = self.test_client.post("/v1/systems", json=system_post_data)

        return self._post_response.json()["id"] if self._post_response.status_code == 201 else None

    def check_post_system_success(self, expected_system_get_data: dict):
        """Checks that a prior call to 'post_system' gave a successful response with the expected data returned"""

        assert self._post_response.status_code == 201
        assert self._post_response.json() == expected_system_get_data

    def check_post_system_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'post_system' gave a failed response with the expected code and error message"""

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"] == detail

    def check_post_system_failed_with_validation_message(self, status_code: int, message: str):
        """Checks that a prior call to 'post_system' gave a failed response with the expected code and pydantic validation
        error message"""

        assert self._post_response.status_code == status_code
        assert self._post_response.json()["detail"][0]["msg"] == message


class TestCreate(CreateDSL):
    """Tests for creating a System"""

    def test_create_with_only_required_values_provided(self):
        """Test creating a System with only required values provided"""

        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.check_post_system_success(SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY)

    def test_create_with_all_values_provided(self):
        """Test creating a System with all values provided"""

        self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.check_post_system_success(SYSTEM_GET_DATA_ALL_VALUES)

    def test_create_with_valid_parent_id(self):
        """Test creating a System with a valid parent id"""

        parent_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "parent_id": parent_id})
        self.check_post_system_success({**SYSTEM_GET_DATA_ALL_VALUES, "parent_id": parent_id})

    def test_create_with_non_existent_parent_id(self):
        """Test creating a System with a non-existent parent id"""

        self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "parent_id": str(ObjectId())})
        self.check_post_system_failed_with_message(422, "The specified parent System does not exist")

    def test_create_with_invalid_parent_id(self):
        """Test creating a System with an invalid parent id"""

        self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "parent_id": "invalid-id"})
        self.check_post_system_failed_with_message(422, "The specified parent System does not exist")

    def test_create_with_duplicate_name_within_parent(self):
        """Test creating a System with the same name as another within the same parent"""

        parent_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        # 2nd post should be the duplicate
        self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "parent_id": parent_id})
        self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "parent_id": parent_id})
        self.check_post_system_failed_with_message(
            409, "A System with the same name already exists within the same parent System"
        )

    def test_create_with_invalid_importance(self):
        """Test creating a System with an invalid importance"""

        self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "importance": "invalid-importance"})
        self.check_post_system_failed_with_validation_message(422, "Input should be 'low', 'medium' or 'high'")


class GetDSL(CreateDSL):
    """Base class for get tests"""

    _get_response: Response

    def get_system(self, system_id: str):
        """Gets a System with the given id"""

        self._get_response = self.test_client.get(f"/v1/systems/{system_id}")

    def check_get_success(self, expected_system_get_data: dict):
        """Checks that a prior call to 'get_system' gave a successful response with the expected data returned"""

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_system_get_data

    def check_get_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'get_system' gave a failed response with the expected code and error message"""

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGet(GetDSL):
    """Tests for getting a System"""

    def test_get(self):
        """Test getting a System"""

        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.get_system(system_id)
        self.check_get_success(SYSTEM_GET_DATA_ALL_VALUES)

    def test_get_with_non_existent_id(self):
        """Test getting a System with a non-existent id"""

        self.get_system(str(ObjectId()))
        self.check_get_failed_with_message(404, "System not found")

    def test_get_with_invalid_id(self):
        """Test getting a System with an invalid id"""

        self.get_system("invalid-id")
        self.check_get_failed_with_message(404, "System not found")


class GetBreadcrumbsDSL(CreateDSL):
    """Base class for breadcrumbs tests"""

    _get_response: Response
    _posted_systems_get_data = []

    def post_nested_systems(self, number: int) -> list[str]:
        """Posts the given number of nested systems where each successive one has the previous as its parent"""

        parent_id = None
        for i in range(0, number):
            system_id = self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "name": f"System {i}", "parent_id": parent_id})
            self._posted_systems_get_data.append(self._post_response.json())
            parent_id = system_id

        return [system["id"] for system in self._posted_systems_get_data]

    def get_system_breadcrumbs(self, system_id: str):
        """Gets a System's breadcrumbs with the given id"""

        self._get_response = self.test_client.get(f"/v1/systems/{system_id}/breadcrumbs")

    def get_last_system_breadcrumbs(self):
        """Gets the last System posted's breadcrumbs"""

        self.get_system_breadcrumbs(self._posted_systems_get_data[-1]["id"])

    def check_get_breadcrumbs_success(self, expected_trail_length: int, expected_full_trail: bool):
        """Checks that a prior call to 'get_system_breadcrumbs' gave a successful response with the expected data returned"""

        assert self._get_response.status_code == 200
        assert self._get_response.json() == {
            "trail": [
                [system["id"], system["name"]]
                # When the expected trail length is < the number of systems posted, only use the last
                # few systems inside the trail
                for system in self._posted_systems_get_data[
                    (len(self._posted_systems_get_data) - expected_trail_length) :
                ]
            ],
            "full_trail": expected_full_trail,
        }

    def check_get_breadcrumbs_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'get_system_breadcrumbs' gave a failed response with the expected code and
        error message"""

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestGetBreadcrumbs(GetBreadcrumbsDSL):
    """Tests for getting a System's breadcrumbs"""

    def test_get_breadcrumbs_when_no_parent(self):
        """Test getting a System's breadcrumbs when the system has no parent"""

        self.post_nested_systems(1)
        self.get_last_system_breadcrumbs()
        self.check_get_breadcrumbs_success(expected_trail_length=1, expected_full_trail=True)

    def test_get_breadcrumbs_when_trail_length_less_than_maximum(self):
        """Test getting a System's breadcrumbs when the full system trail should be less than the maximum trail
        length"""

        self.post_nested_systems(BREADCRUMBS_TRAIL_MAX_LENGTH - 1)
        self.get_last_system_breadcrumbs()
        self.check_get_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH - 1, expected_full_trail=True
        )

    def test_get_breadcrumbs_when_trail_length_maximum(self):
        """Test getting a System's breadcrumbs when the full system trail should be equal to the maximum trail
        length"""

        self.post_nested_systems(BREADCRUMBS_TRAIL_MAX_LENGTH)
        self.get_last_system_breadcrumbs()
        self.check_get_breadcrumbs_success(expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=True)

    def test_get_breadcrumbs_when_trail_length_greater_maximum(self):
        """Test getting a System's breadcrumbs when the full system trail exceeds the maximum trail length"""

        self.post_nested_systems(BREADCRUMBS_TRAIL_MAX_LENGTH + 1)
        self.get_last_system_breadcrumbs()
        self.check_get_breadcrumbs_success(
            expected_trail_length=BREADCRUMBS_TRAIL_MAX_LENGTH, expected_full_trail=False
        )

    def test_get_breadcrumbs_with_non_existent_id(self):
        """Test getting a System's breadcrumbs when given a non-existent system id"""

        self.get_system_breadcrumbs(str(ObjectId()))
        self.check_get_breadcrumbs_failed_with_message(404, "System not found")

    def test_get_breadcrumbs_with_invalid_id(self):
        """Test getting a System's breadcrumbs when given an invalid system id"""

        self.get_system_breadcrumbs("invalid_id")
        self.check_get_breadcrumbs_failed_with_message(404, "System not found")


class ListDSL(CreateDSL):
    """Base class for list tests"""

    _get_response: Response

    def list_systems(self, filters: dict):
        """Gets a list Systems with the given filters"""

        self._get_response = self.test_client.get("/v1/systems", params=filters)

    def post_test_system_with_child(self) -> list[dict]:
        """Posts a System with a single child and returns their expected responses when returned by the list endpoint"""

        parent_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id})

        return [SYSTEM_GET_DATA_ALL_VALUES, {**SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY, "parent_id": parent_id}]

    def check_list_success(self, expected_systems_get_data: list[dict]):
        """Checks that a prior call to 'list' gave a successful response with the expected data returned"""

        assert self._get_response.status_code == 200
        assert self._get_response.json() == expected_systems_get_data

    def check_list_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'list' gave a failed response with the expected code and error message"""

        assert self._get_response.status_code == status_code
        assert self._get_response.json()["detail"] == detail


class TestList(ListDSL):
    """Tests for getting a list of Systems"""

    def test_list_with_no_filters(self):
        """Test getting a list of all Systems with no filters provided

        Posts a system with a child and expects both to be returned.
        """

        systems = self.post_test_system_with_child()
        self.list_systems(filters={})
        self.check_list_success(systems)

    def test_list_with_parent_id_filter(self):
        """Test getting a list of all Systems with a parent_id filter provided

        Posts a system with a child and then filter using the parent_id expecting only the second system
        to be returned.
        """

        systems = self.post_test_system_with_child()
        self.list_systems(filters={"parent_id": systems[1]["parent_id"]})
        self.check_list_success([systems[1]])

    def test_list_with_null_parent_id_filter(self):
        """Test getting a list of all Systems with a parent_id filter of "null" provided

        Posts a system with a child and then filter using a parent_id of "null" expecting only
        the first parent system to be returned.
        """

        systems = self.post_test_system_with_child()
        self.list_systems(filters={"parent_id": "null"})
        self.check_list_success([systems[0]])

    def test_list_with_parent_id_filter_with_no_matching_results(self):
        """Test getting a list of all Systems with a parent_id filter that returns no results"""

        self.list_systems(filters={"parent_id": str(ObjectId())})
        self.check_list_success([])

    def test_list_with_invalid_parent_id_filter(self):
        """Test getting a list of all Systems with an invalid parent_id filter returns no results"""

        self.list_systems(filters={"parent_id": "invalid-id"})
        self.check_list_success([])


# TODO: Put nested system stuff in create rather than get then change this to that
class UpdateDSL(GetBreadcrumbsDSL):
    """Base class for update tests"""

    _patch_response: Response

    def patch_system(self, system_id: str, system_patch_data: dict):
        """Updates a System with the given id"""

        self._patch_response = self.test_client.patch(f"/v1/systems/{system_id}", json=system_patch_data)

    def check_patch_system_response_success(self, expected_system_get_data: dict):
        """Checks the response of patching a property succeeded as expected"""

        assert self._patch_response.status_code == 200
        assert self._patch_response.json() == expected_system_get_data

    def check_patch_system_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'patch_system' gave a failed response with the expected code and error message"""

        assert self._patch_response.status_code == status_code
        assert self._patch_response.json()["detail"] == detail


class TestUpdate(UpdateDSL):
    """Tests for updating a System"""

    def test_partial_update_all_fields(self):
        """Test updating every field of a System"""

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.patch_system(system_id, SYSTEM_POST_DATA_ALL_VALUES)
        self.check_patch_system_response_success(SYSTEM_GET_DATA_ALL_VALUES)

    def test_partial_update_parent_id(self):
        """Test updating the parent_id of a System"""

        parent_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)

        self.patch_system(system_id, {"parent_id": parent_id})
        self.check_patch_system_response_success({**SYSTEM_GET_DATA_ALL_VALUES, "parent_id": parent_id})

    def test_partial_update_parent_id_to_one_with_a_duplicate_name(self):
        """Test updating the parent_id of a System so that its name conflicts with one already in that other
        system"""

        # System with child
        parent_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "name": "Conflicting Name", "parent_id": parent_id})

        system_id = self.post_system({**SYSTEM_POST_DATA_ALL_VALUES, "name": "Conflicting Name"})

        self.patch_system(system_id, {"parent_id": parent_id})
        self.check_patch_system_failed_with_message(
            409, "A System with the same name already exists within the parent System"
        )

    def test_partial_update_parent_id_to_child_of_self(self):
        """Test updating the parent_id of a System to one of its own children"""

        system_ids = self.post_nested_systems(2)
        self.patch_system(system_ids[0], {"parent_id": system_ids[1]})
        self.check_patch_system_failed_with_message(422, "Cannot move a system to one of its own children")

    def test_partial_update_parent_id_to_non_existent(self):
        """Test updating the parent_id of a System to a non-existent System"""

        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.patch_system(system_id, {"parent_id": str(ObjectId())})
        self.check_patch_system_failed_with_message(422, "The specified parent System does not exist")

    def test_partial_update_parent_id_to_invalid(self):
        """Test updating the parent_id of a System to an invalid id"""

        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.patch_system(system_id, {"parent_id": "invalid-id"})
        self.check_patch_system_failed_with_message(422, "The specified parent System does not exist")

    def test_partial_update_name_to_duplicate(self):
        """Test updating the name of a System to conflict with a pre-existing one"""

        self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        system_id = self.post_system(SYSTEM_POST_DATA_ALL_VALUES)
        self.patch_system(system_id, {"name": SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY["name"]})
        self.check_patch_system_failed_with_message(
            409, "A System with the same name already exists within the parent System"
        )

    def test_partial_update_name_capitalisation(self):
        """Test updating the capitalisation of the name of a System (to ensure it the check doesn't confuse with duplicates)"""

        system_id = self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "name": "Test system"})
        self.patch_system(system_id, {"name": "Test System"})
        self.check_patch_system_response_success(
            {**SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY, "name": "Test System", "code": "test-system"}
        )

    def test_partial_update_with_non_existent_id(self):
        """Test updating a non-existent System"""

        self.patch_system(str(ObjectId()), {})
        self.check_patch_system_failed_with_message(404, "System not found")

    def test_partial_update_invalid_id(self):
        """Test updating a System with an invalid id"""

        self.patch_system("invalid-id", {})
        self.check_patch_system_failed_with_message(404, "System not found")


class DeleteDSL(CreateDSL):
    """Base class for delete tests"""

    _delete_response: Response

    def delete_system(self, system_id: str):
        """Deletes a System with the given id"""

        self._delete_response = self.test_client.delete(f"/v1/systems/{system_id}")

    def check_delete_success(self):
        """Checks that a prior call to 'delete_system' gave a successful response with the expected data returned"""

        assert self._delete_response.status_code == 204

    def check_delete_failed_with_message(self, status_code: int, detail: str):
        """Checks that a prior call to 'delete_system' gave a failed response with the expected code and error message"""

        assert self._delete_response.status_code == status_code
        assert self._delete_response.json()["detail"] == detail


class TestDelete(DeleteDSL):
    """Tests for deleting a System"""

    def test_delete(self):
        """Test deleting a System"""

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.delete_system(system_id)
        self.check_delete_success()

    def test_delete_with_child_system(self):
        """Test deleting a System with a child system"""

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": system_id})
        self.delete_system(system_id)
        self.check_delete_failed_with_message(409, "System has child elements and cannot be deleted")

    def test_delete_with_child_item(self):
        """Test deleting a System with a child system"""

        # TODO: Cleanup in future

        system_id = self.post_system(SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY)
        self.post_system({**SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY, "parent_id": system_id})

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
        self.check_delete_failed_with_message(409, "System has child elements and cannot be deleted")

    def test_delete_with_non_existent_id(self):
        """Test deleting a non-existent System"""

        self.delete_system(str(ObjectId()))
        self.check_delete_failed_with_message(404, "System not found")

    def test_delete_with_invalid_id(self):
        """Test deleting a System with an invalid id"""

        self.delete_system("invalid_id")
        self.check_delete_failed_with_message(404, "System not found")
