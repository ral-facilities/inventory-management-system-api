"""
End-to-End tests for the manufacturer router.
"""
import pytest


from inventory_management_system_api.core.database import get_database


@pytest.fixture(name="cleanup_manufacturer", autouse=True)
def fixture_cleanup_manufacturer():
    """
    Fixture to clean up the manufacturer collection in test database
    """
    database = get_database()
    yield
    database.manufacturer.delete_many({})


def test_create_manufacturer(test_client):
    """Test creating a manufacturer"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    assert response.status_code == 201

    manufacturer = response.json()

    assert manufacturer["name"] == manufacturer_post["name"]
    assert manufacturer["url"] == manufacturer_post["url"]
    assert manufacturer["address"] == manufacturer_post["address"]


def test_check_duplicate_name_within_manufacturer(test_client):
    """Test creating a manufactuer with a duplicate name"""

    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)

    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://test.com",
        "address": "Street B",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "A manufacturer with the same name has been found"


def test_list(test_client):
    """Test getting all manufacturers"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)
    manufacturer_post = {
        "name": "Manufacturer B",
        "url": "http://2ndExample.com",
        "address": "Street B",
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)

    response = test_client.get("/v1/manufacturer")

    assert response.status_code == 200

    manufacturers = list(response.json())

    assert len(manufacturers) == 2
    assert manufacturers[0]["name"] == "Manufacturer A"
    assert manufacturers[0]["url"] == "http://example.com"
    assert manufacturers[0]["address"] == "Street A"
    assert manufacturers[0]["code"] == "manufacturer-a"

    assert manufacturers[1]["name"] == "Manufacturer B"
    assert manufacturers[1]["url"] == "http://2ndExample.com"
    assert manufacturers[1]["address"] == "Street B"
    assert manufacturers[1]["code"] == "manufacturer-b"


def test_list_when_no_manufacturers(test_client):
    """Test trying to get all manufacturers when there are none in the databse"""

    response = test_client.get("/v1/manufacturer")

    assert response.status_code == 200
    manufacturers = list(response.json())
    assert not manufacturers
