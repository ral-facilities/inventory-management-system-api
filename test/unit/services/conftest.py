"""
Module for providing common test configuration and test fixtures.
"""
from unittest.mock import Mock

import pytest

from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo


@pytest.fixture(name="catalogue_category_repository_mock")
def fixture_catalogue_category_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `CatalogueCategoryRepo` dependency.

    :return: Mocked CatalogueCategoryRepo instance.
    """
    return Mock(CatalogueCategoryRepo)


@pytest.fixture(name="manufacturer_repository_mock")
def fixture_manufacturer_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `ManufacturerRepo dependency

    :return: Mocked ManufacturerRepo instance
    """
    return Mock(ManufacturerRepo)
