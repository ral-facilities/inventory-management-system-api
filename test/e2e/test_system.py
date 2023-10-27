"""
End-to-End tests for the System router
"""

from unittest.mock import ANY

from bson import ObjectId

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH

SYSTEM_POST_REQUIRED_ONLY = {
    "name": "System Test",
    "importance": "low",
}

SYSTEM_POST_REQUIRED_ONLY_EXPECTED = {
    **SYSTEM_POST_REQUIRED_ONLY,
    "id": ANY,
    "parent_id": None,
    "description": None,
    "location": None,
    "owner": None,
    "code": "system-test",
}

SYSTEM_POST_A = {
    "name": "System A",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
SYSTEM_POST_A_EXPECTED = {
    **SYSTEM_POST_A,
    "id": ANY,
    "parent_id": None,
    "code": "system-a",
}

# To be posted as a child of the above
SYSTEM_POST_B = {
    "name": "System B",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
SYSTEM_POST_B_EXPECTED = {
    **SYSTEM_POST_B,
    "id": ANY,
    "code": "system-b",
}

SYSTEM_POST_C = {
    "name": "System C",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
SYSTEM_POST_C_EXPECTED = {
    **SYSTEM_POST_C,
    "id": ANY,
    "parent_id": None,
    "code": "system-c",
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
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})

    assert response.status_code == 409
    assert response.json()["detail"] == "A System with the same name already exists within the same parent System"


def test_create_system_with_invalid_parent_id(test_client):
    """
    Test creating a System with an invalid parent ID
    """
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_A, "parent_id": "invalid"})

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent System ID does not exist"


def test_create_system_with_non_existent_parent_id(test_client):
    """
    Test creating a System with a non-existent parent ID
    """
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_A, "parent_id": str(ObjectId())})

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent System ID does not exist"


def test_create_system_with_invalid_importance(test_client):
    """
    Test creating a System with an invalid importance
    """
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_A, "importance": "invalid"})

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "value is not a valid enumeration member; permitted: 'low', 'medium', 'high'"
    )


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
    assert response.json()["detail"] == "System with such ID was not found"


def test_delete_system_with_non_existent_id(test_client):
    """
    Test deleting a System with a non existent ID
    """
    # Delete
    response = test_client.delete(f"/v1/systems/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "System with such ID was not found"


def test_delete_system_with_child_system(test_client):
    """
    Test deleting a System
    """
    # Create one to delete
    # Parent
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    parent_system = response.json()

    # Child
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": parent_system["id"]})

    # Delete
    response = test_client.delete(f"/v1/systems/{parent_system['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "System has child elements and cannot be deleted"


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
    assert response.json()["detail"] == "A System with such ID was not found"


def test_get_system_with_non_existent_id(test_client):
    """
    Test getting a System with a non-existent ID
    """
    response = test_client.get(f"/v1/systems/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A System with such ID was not found"


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


def test_systems_with_invalid_parent_id_filter(test_client):
    """
    Test getting a list of Systems when given invalid parent_id filter
    """
    response = test_client.get("/v1/systems", params={"parent_id": "invalid"})

    assert response.status_code == 200
    assert response.json() == []


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
    assert response.json()["detail"] == "System with such ID was not found"


def test_get_system_breadcrumbs_with_non_existent_id(test_client):
    """
    Test getting the breadcrumbs for a non existent system
    """
    response = test_client.get(f"/v1/systems/{str(ObjectId())}/breadcrumbs")

    assert response.status_code == 404
    assert response.json()["detail"] == "System with such ID was not found"
