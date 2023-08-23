"""
End-to-End tests for the catalogue category router.
"""
import pytest

from bson import ObjectId

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPostRequestSchema,
    CatalogueCategorySchema,
)


@pytest.fixture(name="cleanup_catalogue_categories", autouse=True)
def fixture_cleanup_catalogue_categories():
    """
    Fixture to clean up the catalogue categories collection in the test database after the session finishes.
    """
    database = get_database()
    yield
    database.catalogue_categories.delete_many({})


def test_create_catalogue_category(test_client):
    """
    Test creating a catalogue category.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 201

    catalogue_category = CatalogueCategorySchema(**response.json())

    assert catalogue_category.name == catalogue_category_post.name
    assert catalogue_category.code == "category-a"
    assert catalogue_category.is_leaf is False
    assert catalogue_category.path == "/category-a"
    assert catalogue_category.parent_path == "/"
    assert catalogue_category.parent_id is None


def test_create_catalogue_category_with_valid_parent_id(test_client):
    """
    Test creating a catalogue category with a valid parent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=True, parent_id=parent_id)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 201

    catalogue_category = CatalogueCategorySchema(**response.json())

    assert catalogue_category.name == catalogue_category_post.name
    assert catalogue_category.code == "category-a"
    assert catalogue_category.is_leaf is True
    assert catalogue_category.path == "/category-a/category-a"
    assert catalogue_category.parent_path == "/category-a"
    assert catalogue_category.parent_id == parent_id


def test_create_catalogue_category_with_duplicate_name_within_parent(test_client):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False, parent_id=parent_id)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=True, parent_id=parent_id)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_create_catalogue_category_with_invalid_parent_id(test_client):
    """
    Test creating a catalogue category with an invalid parent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False, parent_id="invalid")

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist in the database"


def test_create_catalogue_category_with_nonexistent_parent_id(test_client):
    """
    Test creating a catalogue category with a nonexistent parent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(
        name="Category A", is_leaf=False, parent_id=str(ObjectId())
    )

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist in the database"


def test_create_catalogue_category_with_leaf_parent_catalogue_category(test_client):
    """
    Test creating a catalogue category in a leaf parent catalogue category.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=True)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False, parent_id=parent_id)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue category to a leaf parent catalogue category is not allowed"


def test_delete_catalogue_category(test_client):
    """
    Test deleting a catalogue category.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    response = test_client.delete(f"/v1/catalogue-categories/{catalogue_category.id}")

    assert response.status_code == 204
    response = test_client.get(f"/v1/catalogue-categories/{catalogue_category.id}")
    assert response.status_code == 404


def test_delete_catalogue_category_with_invalid_id(test_client):
    """
    Test deleting a catalogue category with an invalid ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.delete("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_delete_catalogue_with_children_elements(test_client):
    """
    Test deleting a catalogue category with children elements.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    parent_response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**parent_response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=True, parent_id=parent_id)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.delete(f"/v1/catalogue-categories/{parent_response.json()['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be deleted"


def test_delete_catalogue_category_with_nonexistent_id(test_client):
    """
    Test deleting a catalogue category with a nonexistent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.delete(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_get_catalogue_category(test_client):
    """
    Test getting a catalogue category.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=True, parent_id=parent_id)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get(f"/v1/catalogue-categories/{response.json()['id']}")

    assert response.status_code == 200

    catalogue_category = CatalogueCategorySchema(**response.json())

    assert catalogue_category.name == catalogue_category_post.name
    assert catalogue_category.code == "category-a"
    assert catalogue_category.is_leaf is True
    assert catalogue_category.path == "/category-a/category-a"
    assert catalogue_category.parent_path == "/category-a"
    assert catalogue_category.parent_id == parent_id


def test_get_catalogue_category_with_invalid_id(test_client):
    """
    Test getting a catalogue category with an invalid ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested catalogue category was not found"


def test_get_catalogue_category_with_nonexistent_id(test_client):
    """
    Test getting a catalogue category with a nonexistent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested catalogue category was not found"


def test_get_catalogue_categories(test_client):
    """
    Test getting catalogue categories.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category B", is_leaf=False)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category C", is_leaf=True, parent_id=parent_id)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get("/v1/catalogue-categories")

    assert response.status_code == 200

    catalogue_categories = [CatalogueCategorySchema(**r) for r in response.json()]

    assert len(catalogue_categories) == 3
    assert catalogue_categories[0].path == "/category-a"
    assert catalogue_categories[0].parent_path == "/"
    assert catalogue_categories[1].path == "/category-b"
    assert catalogue_categories[1].parent_path == "/"
    assert catalogue_categories[2].path == "/category-b/category-c"
    assert catalogue_categories[2].parent_path == "/category-b"


def test_list_with_path_filter(test_client):
    """
    Test getting catalogue categories based on the provided parent path filter.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category B", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get("/v1/catalogue-categories", params={"path": "/category-a"})

    assert response.status_code == 200

    catalogue_categories = [CatalogueCategorySchema(**r) for r in response.json()]

    assert len(catalogue_categories) == 1
    assert catalogue_categories[0].path == "/category-a"
    assert catalogue_categories[0].parent_path == "/"


def test_list_with_parent_path_filter(test_client):
    """
    Test getting catalogue categories based on the provided parent path filter.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category B", is_leaf=False)
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category = CatalogueCategorySchema(**response.json())

    parent_id = catalogue_category.id
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category C", is_leaf=True, parent_id=parent_id)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get("/v1/catalogue-categories", params={"parent_path": "/"})

    assert response.status_code == 200

    catalogue_categories = [CatalogueCategorySchema(**r) for r in response.json()]

    assert len(catalogue_categories) == 1
    assert catalogue_categories[0].path == "/category-b"
    assert catalogue_categories[0].parent_path == "/"


def test_list_with_path_and_parent_path_filters(test_client):
    """
    Test getting catalogue categories based on the provided path and parent path filters.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category B", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get("/v1/catalogue-categories", params={"path": "/category-b", "parent_path": "/"})

    assert response.status_code == 200

    catalogue_categories = [CatalogueCategorySchema(**r) for r in response.json()]

    assert len(catalogue_categories) == 1
    assert catalogue_categories[0].path == "/category-b"
    assert catalogue_categories[0].parent_path == "/"


def test_list_with_path_and_parent_path_filters_no_matching_results(test_client):
    """
    Test getting catalogue categories based on the provided path and parent path filters when there is no matching
    results in the database.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category B", is_leaf=False)
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    response = test_client.get("/v1/catalogue-categories", params={"path": "/category-c", "parent_path": "/"})

    assert response.status_code == 200

    catalogue_categories = [CatalogueCategorySchema(**r) for r in response.json()]

    assert len(catalogue_categories) == 0
