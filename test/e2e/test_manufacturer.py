"""
End-to-End tests for the manufacturer router.
"""
from bson import ObjectId
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


def test_get_manufacturer_with_id(test_client):
    """Test getting a manufacturer by ID"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }
    response = test_client.post("/v1/manufacturer", json=manufacturer_post)
    response = test_client.get(f"/v1/manufacturer/{response.json()['id']}")
    assert response.status_code == 200
    manufacturer = response.json()

    assert manufacturer["name"] == manufacturer_post["name"]
    assert manufacturer["url"] == manufacturer_post["url"]
    assert manufacturer["address"] == manufacturer_post["address"]


def test_get_manufacturer_with_invalid_id(test_client):
    """Test getting a manufacturer with an invalid id"""

    response = test_client.get("/v1/manufacturer/invalid")
    assert response.status_code == 404
    assert response.json()["detail"] == "The requested manufacturer was not found"


def test_get_manufactuer_with_nonexistent_id(test_client):
    """Test getting a manufacturer with an nonexistent id"""
    response = test_client.get(f"/v1/manufacturer/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested manufacturer was not found"


def test_update(test_client):
    """Test updating a manufacturer"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    manufacturer_patch = {
        "name": "Manufacturer B",
        "url": "http://test.co.uk",
        "address": "Street B",
    }
    response = test_client.patch(f"/v1/manufacturer/{response.json()['id']}", json=manufacturer_patch)

    assert response.status_code == 200
    manufacturer = response.json()

    assert manufacturer["name"] == manufacturer_patch["name"]
    assert manufacturer["url"] == manufacturer_patch["url"]
    assert manufacturer["address"] == manufacturer_patch["address"]


def test_update_with_invalid_id(test_client):
    """Test trying to update a manufacturer with an invalid ID"""
    manufacturer_patch = {
        "name": "Manufacturer B",
        "url": "http://test.co.uk",
        "address": "Street B",
    }
    response = test_client.patch("/v1/manufacturer/invalid", json=manufacturer_patch)

    assert response.status_code == 422

    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_update_with_nonexistent_id(test_client):
    """Test trying to update a manufacturer with a non-existent ID"""
    manufacturer_patch = {
        "name": "Manufacturer B",
        "url": "http://test.co.uk",
        "address": "Street B",
    }
    response = test_client.patch(f"/v1/manufacturer/{str(ObjectId())}", json=manufacturer_patch)

    assert response.status_code == 422

    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_update_duplicate_name(test_client):
    """Test updating a manufacturer with a duplicate name"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)

    manufacturer_patch = {
        "name": "Manufacturer A",
        "url": "http://test.co.uk",
        "address": "Street B",
    }
    response = test_client.patch(f"/v1/manufacturer/{response.json()['id']}", json=manufacturer_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "A manufacturer with the same name has been found"


def test_delete(test_client):
    """Test deleting a manufacturer"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }

    response = test_client.post("/v1/manufacturer", json=manufacturer_post)
    manufacturer = response.json()

    response = test_client.delete(f"/v1/manufacturer/{manufacturer['id']}")
    assert response.status_code == 204


def test_delete_with_an_invalid_id(test_client):
    """Test trying to delete a manufacturer with an invalid ID"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)

    response = test_client.delete("/v1/manufacturer/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_delete_with_a_nonexistent_id(test_client):
    """Test trying to delete a manufacturer with a non-existent ID"""
    manufacturer_post = {
        "name": "Manufacturer A",
        "url": "http://example.com",
        "address": "Street A",
    }
    test_client.post("/v1/manufacturer", json=manufacturer_post)

    response = test_client.delete(f"/v1/manufacturer/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_delete_manufacturer_that_is_a_part_of_catalogue_item():
    """Test trying to delete a manufacturer that is a part of a Catalogue Item"""
    # pylint: disable=fixme
    # TODO - Uncomment test when catalogue item logic changes back to using manufacturer Id

    # manufacturer_post = {
    #     "name": "Manufacturer A",
    #     "url": "http://example.com",
    #     "address": "Street A",
    # }
    # response = test_client.post("/v1/manufacturer", json=manufacturer_post)
    # manufacturer_id = response.json()["id"]
    # # pylint: disable=duplicate-code
    # catalogue_category_post = {
    #     "name": "Category A",
    #     "is_leaf": True,
    #     "catalogue_item_properties": [
    #         {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
    #         {"name": "Property B", "type": "boolean", "mandatory": True},
    #     ],
    # }
    # # pylint: enable=duplicate-code
    # response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    # # pylint: disable=duplicate-code
    # catalogue_category_id = response.json()["id"]

    # catalogue_item_post = {
    #     "catalogue_category_id": catalogue_category_id,
    #     "name": "Catalogue Item A",
    #     "description": "This is Catalogue Item A",
    #     "properties": [{"name": "Property B", "value": False}],
    #     "manufacturer": manufacturer_post,
    # }
    # # pylint: enable=duplicate-code
    # test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # response = test_client.delete(f"/v1/manufacturer/{manufacturer_id}")

    # assert response.status_code == 409
    # assert response.json()["detail"] == "The specified manufacturer is a part of a Catalogue Item"
