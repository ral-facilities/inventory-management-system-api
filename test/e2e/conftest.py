"""
Module providing test fixtures for the e2e tests.
"""
import pytest
from fastapi.testclient import TestClient

from inventory_management_system_api.main import app


@pytest.fixture()
def test_client() -> TestClient:
    """
    Fixture for creating a test client for the application.

    :return: The test client.
    """
    return TestClient(app)
