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

from bson import ObjectId

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH

SYSTEM_POST_REQUIRED_ONLY = {
    "name": "System Test",
    "importance": "low",
}

SYSTEM_POST_REQUIRED_ONLY_EXPECTED = {
    **SYSTEM_POST_REQUIRED_ONLY,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "description": None,
    "location": None,
    "owner": None,
    "code": "system-test",
}


def _post_nested_systems(test_client, entities: list[dict]):
    """Utility function for posting a set of mock systems where each successive entity should
    be the parent of the next"""

    systems = []
    parent_id = None
    for entity in entities:
        system = test_client.post("/v1/systems", json={**entity, "parent_id": parent_id}).json()
        parent_id = system["id"]
        systems.append(system)

    return (*systems,)


def _post_systems(test_client):
    """Utility function for posting all mock systems defined at the top of this file"""

    (system_a, system_b, *_) = _post_nested_systems(test_client, [SYSTEM_POST_A, SYSTEM_POST_B])
    (system_c, *_) = _post_nested_systems(test_client, [SYSTEM_POST_C])

    return system_a, system_b, system_c


def _post_n_systems(test_client, number):
    """Utility function to post a given number of nested systems (all based on system A)"""
    return _post_nested_systems(
        test_client,
        [
            {
                **SYSTEM_POST_A,
                "name": f"System {i}",
            }
            for i in range(0, number)
        ],
    )


def _test_partial_update_system(
    test_client, update_values: dict[str, Any], additional_expected_values: Optional[dict[str, Any]] = None
):
    """
    Utility method that tests updating a system

    :param update_values: Values to update
    :param additional_expected_values: Any additional values expected from the output e.g. code
    """
    if additional_expected_values is None:
        additional_expected_values = {}

    # Create one to update
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system = response.json()

    # Update
    response = test_client.patch(f"/v1/systems/{system['id']}", json=update_values)

    assert response.status_code == 200
    assert response.json() == {
        **system,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        **update_values,
        **additional_expected_values,
    }


def test_create_system(test_client):
    """
    Test creating a System
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)

    assert response.status_code == 201

    system = response.json()

    assert system == SYSTEM_POST_A_EXPECTED


def test_create_system_with_only_required_values_given(test_client):
    """
    Test creating a System when only the required values are given
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_REQUIRED_ONLY)

    assert response.status_code == 201

    system = response.json()

    assert system == SYSTEM_POST_REQUIRED_ONLY_EXPECTED


def test_create_system_with_valid_parent_id(test_client):
    """
    Test creating a System with a valid parent ID
    """
    # Parent
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    parent_system = response.json()

    # Child
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})

    assert response.status_code == 201
    system = response.json()
    assert system == {**SYSTEM_POST_B_EXPECTED, "parent_id": parent_system["id"]}


def test_create_system_with_duplicate_name_within_parent(test_client):
    """
    Test creating a System with a duplicate name within the parent System
    """
    # Parent
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    parent_system = response.json()

    # Child - post twice as will have the same name
    test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})

    assert response.status_code == 409
    assert response.json()["detail"] == "A System with the same name already exists within the same parent System"


def test_create_system_with_invalid_parent_id(test_client):
    """
    Test creating a System with an invalid parent ID
    """
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_A, "parent_id": "invalid"})

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent System does not exist"


def test_create_system_with_non_existent_parent_id(test_client):
    """
    Test creating a System with a non-existent parent ID
    """
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_A, "parent_id": str(ObjectId())})

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent System does not exist"


def test_create_system_with_invalid_importance(test_client):
    """
    Test creating a System with an invalid importance
    """
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_A, "importance": "invalid"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be 'low', 'medium' or 'high'"


def test_get_systems(test_client):
    """
    Test getting a list of Systems
    """
    system_a, system_b, system_c = _post_systems(test_client)

    # Get all systems (no filters)
    response = test_client.get("/v1/systems")

    assert response.status_code == 200
    assert response.json() == [system_a, system_b, system_c]


def test_get_systems_with_parent_id_filter(test_client):
    """
    Test getting a list of Systems with a parent_id filter
    """
    _, system_b, _ = _post_systems(test_client)

    # Get only those with the given parent_id
    response = test_client.get("/v1/systems", params={"parent_id": system_b["parent_id"]})

    assert response.status_code == 200
    assert response.json() == [system_b]


def test_get_systems_with_null_parent_id_filter(test_client):
    """
    Test getting a list of Systems with a parent_id filter of "null"
    """

    system_a, _, system_c = _post_systems(test_client)

    # Get only those with the given parent parent_id
    response = test_client.get("/v1/systems", params={"parent_id": "null"})

    assert response.status_code == 200
    assert response.json() == [system_a, system_c]


def test_get_systems_with_parent_id_filter_no_matching_results(test_client):
    """
    Test getting a list of Systems with a parent_id filter when there is no
    matching results in the database
    """
    _, _, _ = _post_systems(test_client)

    # Get only those with the given parent_id
    response = test_client.get("/v1/systems", params={"parent_id": str(ObjectId())})

    assert response.status_code == 200
    assert response.json() == []


def test_get_systems_with_invalid_parent_id_filter(test_client):
    """
    Test getting a list of Systems when given invalid parent_id filter
    """
    response = test_client.get("/v1/systems", params={"parent_id": "invalid"})

    assert response.status_code == 200
    assert response.json() == []


def test_get_system(test_client):
    """
    Test getting a System
    """
    # Post one first
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system = response.json()
    system_id = system["id"]

    # Ensure can get it again
    response = test_client.get(f"/v1/systems/{system_id}")

    assert response.status_code == 200
    assert response.json() == SYSTEM_POST_A_EXPECTED


def test_get_system_with_invalid_id(test_client):
    """
    Test getting a System with an invalid ID
    """
    response = test_client.get("/v1/systems/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_get_system_with_non_existent_id(test_client):
    """
    Test getting a System with a non-existent ID
    """
    response = test_client.get(f"/v1/systems/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_get_system_breadcrumbs_when_no_parent(test_client):
    """
    Test getting the breadcrumbs for a system with no parents
    """
    (system_c, *_) = _post_nested_systems(test_client, [SYSTEM_POST_C])

    response = test_client.get(f"/v1/systems/{system_c['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {"trail": [[system_c["id"], system_c["name"]]], "full_trail": True}


def test_get_system_breadcrumbs_when_trail_length_less_than_maximum(test_client):
    """
    Test getting the breadcrumbs for a system with less than the the maximum trail length
    """
    systems = _post_n_systems(test_client, BREADCRUMBS_TRAIL_MAX_LENGTH - 1)

    # Get breadcrumbs for last added
    response = test_client.get(f"/v1/systems/{systems[-1]['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {"trail": [[system["id"], system["name"]] for system in systems], "full_trail": True}


def test_get_system_breadcrumbs_when_trail_length_maximum(test_client):
    """
    Test getting the breadcrumbs for a system with the maximum trail length
    """
    systems = _post_n_systems(test_client, BREADCRUMBS_TRAIL_MAX_LENGTH)

    # Get breadcrumbs for last added
    response = test_client.get(f"/v1/systems/{systems[-1]['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {"trail": [[system["id"], system["name"]] for system in systems], "full_trail": True}


def test_get_system_breadcrumbs_when_trail_length_greater_than_maximum(test_client):
    """
    Test getting the breadcrumbs for a system with greater than the the maximum trail length
    """
    systems = _post_n_systems(test_client, BREADCRUMBS_TRAIL_MAX_LENGTH + 1)

    # Get breadcrumbs for last added
    response = test_client.get(f"/v1/systems/{systems[-1]['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {"trail": [[system["id"], system["name"]] for system in systems[1:]], "full_trail": False}


def test_get_system_breadcrumbs_with_invalid_id(test_client):
    """
    Test getting the breadcrumbs for a system when the given id is invalid
    """
    response = test_client.get("/v1/systems/invalid/breadcrumbs")

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_get_system_breadcrumbs_with_non_existent_id(test_client):
    """
    Test getting the breadcrumbs for a non-existent system
    """
    response = test_client.get(f"/v1/systems/{str(ObjectId())}/breadcrumbs")

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_partial_update_system_parent_id(test_client):
    """
    Test updating a System's parent_id
    """
    parent_system = test_client.post("/v1/systems", json=SYSTEM_POST_B).json()

    _test_partial_update_system(test_client, {"parent_id": parent_system["id"]}, {})


def test_partial_update_system_parent_id_to_child_id(test_client):
    """
    Test updating a System's parent_id to be the id of one of its children
    """
    nested_systems = _post_n_systems(test_client, 4)

    # Attempt to move first into one of its children
    response = test_client.patch(f"/v1/systems/{nested_systems[0]['id']}", json={"parent_id": nested_systems[3]["id"]})

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot move a system to one of its own children"


def test_partial_update_system_invalid_parent_id(test_client):
    """
    Test updating a System's parent_id when the ID is invalid
    """
    # Create one to update
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system = response.json()

    # Update
    response = test_client.patch(f"/v1/systems/{system['id']}", json={"parent_id": "invalid"})

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent System does not exist"


def test_partial_update_system_non_existent_parent_id(test_client):
    """
    Test updating a System's parent_id when the ID is non-existent
    """
    # Create one to update
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system = response.json()

    # Update
    response = test_client.patch(f"/v1/systems/{system['id']}", json={"parent_id": str(ObjectId())})

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent System does not exist"


def test_partial_update_system_parent_id_duplicate_name(test_client):
    """
    Test updating a System's parent_id when the new parent has a child with a duplicate name
    """
    # Parent to move to
    parent_system = test_client.post("/v1/systems", json=SYSTEM_POST_A).json()

    # Two identical systems, one already with a parent the other without
    test_client.post(
        "/v1/systems", json={**SYSTEM_POST_B, "name": "Duplicate name", "parent_id": parent_system["id"]}
    ).json()
    system = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "name": "Duplicate name"}).json()

    # Change the parent of system to be the same as system1
    response = test_client.patch(f"/v1/systems/{system['id']}", json={"parent_id": parent_system["id"]})

    assert response.status_code == 409
    assert response.json()["detail"] == "A System with the same name already exists within the parent System"


def test_partial_update_system_name(test_client):
    """
    Test updating a System's name
    """
    _test_partial_update_system(test_client, {"name": "Updated name"}, {"code": "updated-name"})


def test_partial_update_capitalisation_of_system_name(test_client):
    """
    Test updating a capitalisation of the System's name
    """
    _test_partial_update_system(
        test_client,
        {
            "name": "SyStEm A",
        },
    )


def test_partial_update_all_other_fields(test_client):
    """
    Test updating the rest of a systems fields not tested above
    """
    _test_partial_update_system(
        test_client,
        {
            "description": "Updated description",
            "location": "Updated location",
            "owner": "Updated owner",
            "importance": "high",
        },
    )


def test_partial_update_system_invalid_id(test_client):
    """
    Test updating a System when the ID is invalid
    """
    response = test_client.patch("/v1/systems/invalid", json={"name": "Updated name"})

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_partial_update_system_non_existent_id(test_client):
    """
    Test updating a System when the ID is non-existent
    """
    response = test_client.patch(f"/v1/systems/{str(ObjectId())}", json={"name": "Updated name"})

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_delete_system(test_client):
    """
    Test deleting a System
    """
    # Create one to delete
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system = response.json()

    # Delete
    response = test_client.delete(f"/v1/systems/{system['id']}")

    assert response.status_code == 204
    response = test_client.get(f"/v1/systems/{system['id']}")
    assert response.status_code == 404


def test_delete_system_with_invalid_id(test_client):
    """
    Test deleting a System with an invalid ID
    """
    # Delete
    response = test_client.delete("/v1/systems/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_delete_system_with_non_existent_id(test_client):
    """
    Test deleting a System with a non-existent ID
    """
    # Delete
    response = test_client.delete(f"/v1/systems/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "System not found"


def test_delete_system_with_child_system(test_client):
    """
    Test deleting a System that has subsystem
    """
    # Create one to delete
    # Parent
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    parent_system = response.json()

    # Child
    test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})

    # Delete
    response = test_client.delete(f"/v1/systems/{parent_system['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "System has child elements and cannot be deleted"


def test_delete_system_with_child_item(test_client):
    """
    Test deleting a System that contains an item
    """
    # Create one to delete
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    # Create a child item
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_A["properties"], units),
        },
    )
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_B)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["properties"], ITEM_POST["properties"]),
    }
    test_client.post("/v1/items", json=item_post)
    # pylint: enable=duplicate-code

    # Delete
    response = test_client.delete(f"/v1/systems/{system_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "System has child elements and cannot be deleted"
