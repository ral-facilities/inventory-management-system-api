"""
Module providing test fixtures for the e2e tests.
"""

from test.conftest import VALID_ACCESS_TOKEN
from test.e2e.mock_schemas import USAGE_STATUSES

import pytest
from fastapi.testclient import TestClient

from inventory_management_system_api.core.database import get_database
from inventory_management_system_api.main import app


@pytest.fixture(name="test_client")
def fixture_test_client() -> TestClient:
    """
    Fixture for creating a test client for the application.

    :return: The test client.
    """
    return TestClient(app, headers={"Authorization": f"Bearer {VALID_ACCESS_TOKEN}"})


@pytest.fixture(name="add_usage_statuses_to_database", autouse=True, scope="session")
def fixture_add_usage_statuses_to_database():
    """
    Fixture to add usage statuses to the usage_statuses collection in the database before any tests run
    """
    usage_statuses_collection = get_database().usage_statuses
    usage_statuses_collection.delete_many({})
    usage_statuses_collection.insert_many(USAGE_STATUSES)
    yield


@pytest.fixture(name="cleanup_database_collections", autouse=True)
def fixture_cleanup_database_collections():
    """
    Fixture to clean up the collections in the test database after the session finishes.
    """
    database = get_database()
    yield
    database.catalogue_categories.delete_many({})
    database.catalogue_items.delete_many({})
    database.items.delete_many({})
    database.manufacturers.delete_many({})
    database.systems.delete_many({})
