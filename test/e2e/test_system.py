"""
End-to-End tests for the System router
"""

from unittest.mock import ANY

from bson import ObjectId


SYSTEM_POST_A = {"name": "System A", "location": "Test location", "owner": "Me", "importance": "low"}
SYSTEM_POST_A_EXPECTED = {
    **SYSTEM_POST_A,
    "id": ANY,
    "code": "system-a",
    "path": "/system-a",
    "parent_path": "/",
    "parent_id": None,
}

# To be posted as a child of the above
SYSTEM_POST_B = {"name": "System B", "location": "Test location", "owner": "Me", "importance": "low"}
SYSTEM_POST_B_EXPECTED = {
    **SYSTEM_POST_B,
    "id": ANY,
    "code": "system-b",
    "path": "/system-a/system-b",
    "parent_path": "/system-a",
}

SYSTEM_POST_C = {"name": "System C", "location": "Test location", "owner": "Me", "importance": "low"}
SYSTEM_POST_C_EXPECTED = {
    **SYSTEM_POST_C,
    "id": ANY,
    "code": "system-c",
    "path": "/system-c",
    "parent_path": "/",
    "parent_id": None,
}


def test_create_system(test_client):
    """
    Test creating a System
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)

    assert response.status_code == 201

    system = response.json()

    assert system == SYSTEM_POST_A_EXPECTED


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


def _post_systems(test_client):
    """Utility function for posting all mock systems"""

    # Parent
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_a = response.json()

    # Child
    response = test_client.post("/v1/systems", json={**SYSTEM_POST_B, "parent_id": system_a["id"]})
    system_b = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_C)
    system_c = response.json()

    return system_a, system_b, system_c


def test_get_systems(test_client):
    """
    Test getting a list of Systems
    """

    system_a, system_b, system_c = _post_systems(test_client)

    # Get all systems (no filters)
    response = test_client.get("/v1/systems")

    assert response.status_code == 200
    assert response.json() == [system_a, system_b, system_c]


def test_get_systems_with_path_filter(test_client):
    """
    Test getting a list of Systems with a path filter
    """

    _, _, system_c = _post_systems(test_client)

    # Get only those with the given path
    response = test_client.get("/v1/systems", params={"path": "/system-c"})

    assert response.status_code == 200
    assert response.json() == [system_c]


def test_get_systems_with_parent_path_filter(test_client):
    """
    Test getting a list of Systems with a parent path filter
    """

    _, system_b, _ = _post_systems(test_client)

    # Get only those with the given parent path
    response = test_client.get("/v1/systems", params={"parent_path": "/system-a"})

    assert response.status_code == 200
    assert response.json() == [system_b]


def test_get_systems_with_path_and_parent_path_filter(test_client):
    """
    Test getting a list of Systems with a path and parent path filter
    """

    _, system_b, _ = _post_systems(test_client)

    # Get only those with the given path and parent path
    response = test_client.get("/v1/systems", params={"path": "/system-a/system-b", "parent_path": "/system-a"})

    assert response.status_code == 200
    assert response.json() == [system_b]


def test_get_systems_with_path_and_parent_path_filters_no_matching_results(test_client):
    """
    Test getting a list of Systems with a path and parent path filter when there is no
    matching results in the database
    """

    _, _, _ = _post_systems(test_client)

    # Get only those with the given path and parent path
    response = test_client.get("/v1/systems", params={"path": "/", "parent_path": "/system-b"})

    assert response.status_code == 200
    assert response.json() == []
