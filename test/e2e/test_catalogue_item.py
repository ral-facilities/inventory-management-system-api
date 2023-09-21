"""
End-to-End tests for the catalogue item router.
"""
import pytest
from bson import ObjectId

from inventory_management_system_api.core.database import get_database

CATALOGUE_CATEGORY_POST = {  # pylint: disable=duplicate-code
    "name": "Category A",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
        {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
    ],
}


@pytest.fixture(name="cleanup_catalogue_categories", autouse=True)
def fixture_cleanup_catalogue_categories():
    """
    Fixture to clean up the catalogue categories collection in the test database after the session finishes.
    """
    database = get_database()
    yield
    database.catalogue_categories.delete_many({})


@pytest.fixture(name="cleanup_catalogue_items", autouse=True)
def fixture_cleanup_catalogue_items():
    """
    Fixture to clean up the catalogue items collection in the test database after the session finishes.
    """
    database = get_database()
    yield
    database.catalogue_items.delete_many({})


def test_create_catalogue_item(test_client):
    """
    Test creating a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    catalogue_item_post["properties"][0]["unit"] = "mm"
    catalogue_item_post["properties"][1]["unit"] = None
    catalogue_item_post["properties"][2]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_post["properties"]


def test_create_catalogue_item_with_duplicate_name_within_catalogue_category(test_client):
    """
    Test creating a catalogue item with a duplicate name within the catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 409
    assert (
        response.json()["detail"] == "A catalogue item with the same name already exists within the catalogue category"
    )


def test_create_catalogue_item_with_invalid_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with an invalid catalogue category id.
    """
    catalogue_item_post = {
        "catalogue_category_id": "invalid",
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist in the database"


def test_create_catalogue_item_with_nonexistent_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with a nonexistent catalogue category id.
    """
    catalogue_item_post = {
        "catalogue_category_id": str(ObjectId()),
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist in the database"


def test_create_catalogue_item_in_non_leaf_catalogue_category(test_client):
    """
    Test creating a catalogue item in a non-leaf catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


def test_create_catalogue_item_with_missing_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_create_catalogue_item_with_missing_non_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing non-mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    catalogue_item_post["properties"][0]["unit"] = None
    catalogue_item_post["properties"][1]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_post["properties"]


def test_create_catalogue_item_with_invalid_value_type_for_string_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a string catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": True},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property C'. Expected type: string."
    )


def test_create_catalogue_item_with_invalid_value_type_for_number_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a number catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": "20"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property A'. Expected type: number."
    )


def test_create_catalogue_item_with_invalid_value_type_for_boolean_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a boolean catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": "False"},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
    )
