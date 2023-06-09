"""
End-to-End tests for the catalogue category router.
"""
import pytest

from bson import ObjectId

from inventory_management_system_api.core.database import db
from inventory_management_system_api.schemas.catalogue_category import CatalogueCategoryPostRequestSchema, \
    CatalogueCategorySchema


@pytest.fixture(scope="session", autouse=True)
def cleanup_catalogue_categories(request):
    """
    Fixture to clean up the catalogue categories collection in the test database after the session finishes.

    :param request: The pytest request object.
    """
    def session_finish():
        db.catalogue_categories.delete_many({})

    request.addfinalizer(session_finish)


def test_create_catalogue_category(test_client):
    """
    Test creating a catalogue category.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A")

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 201

    catalogue_category = CatalogueCategorySchema(**response.json())

    assert catalogue_category.name == catalogue_category_post.name


def test_create_catalogue_category_with_invalid_parent_id(test_client):
    """
    Test creating a catalogue category with an invalid parent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", parent_id="invalid")

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist in the database"


def test_create_catalogue_category_with_nonexistent_parent_id(test_client):
    """
    Test creating a catalogue category with a nonexistent parent ID.
    """
    catalogue_category_post = CatalogueCategoryPostRequestSchema(name="Category A", parent_id=str(ObjectId()))

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post.dict())

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist in the database"
