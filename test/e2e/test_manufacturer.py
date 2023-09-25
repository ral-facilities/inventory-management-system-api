"""
End-to-End tests for the manufacturer router.
"""
import pytest

from bson import ObjectId

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
        "address": {
            "name": "Manufacturer A",
            "street_name": "Street A",
            "city": "City A",
            "county": "County A",
            "post_code": "AB1 2CD",
            "country": "UK",
        },
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    assert response.status_code == 201

    manufacturer = response.json()

    assert manufacturer["name"] == manufacturer_post["name"]
    assert manufacturer["url"] == manufacturer_post["url"]
    assert manufacturer["address"] == manufacturer_post["address"]


def test_check_duplicate_url_within_manufacturer(test_client):
    """Test creating a manufactuer with a duplicate url"""

    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "example.com",
        "address": {
            "name": "Manufacturer A",
            "street_name": "Street A",
            "city": "City A",
            "county": "County A",
            "post_code": "AB1 2CD",
            "country": "UK",
        },
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)

    manufacturer_post = {
        "name": "Manufacturer B",
        "url": "example.com",
        "address": {
            "name": "Manufacturer B",
            "street_name": "Street B",
            "city": "City B",
            "county": "County B",
            "post_code": "AB1 2CD",
            "country": "UK",
        },
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "A manufacturer with the same url has been found"
