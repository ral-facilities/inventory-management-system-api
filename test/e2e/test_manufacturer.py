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
        "url": "example.com",
        "address": "Street A",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    assert response.status_code == 201

    manufacturer = response.json()

    assert manufacturer["name"] == manufacturer_post["name"]
    assert manufacturer["url"] == manufacturer_post["url"]
    assert manufacturer["address"] == manufacturer_post["address"]


def test_check_duplicate_url_within_manufacturer(test_client):
    """Test creating a manufactuer with a duplicate name"""

    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "example.com",
        "address": "Street A",
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)

    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "test.com",
        "address": "Street B",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "A manufacturer with the same name has been found"
