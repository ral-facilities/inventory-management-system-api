"""
Module for providing common test configuration and test fixtures.
"""

from typing import List, Type, Union
from unittest.mock import Mock

import pytest

from inventory_management_system_api.models.catalogue_category import CatalogueCategoryOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut
from inventory_management_system_api.models.item import ItemOut
from inventory_management_system_api.models.system import SystemOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService
from inventory_management_system_api.services.catalogue_item import CatalogueItemService
from inventory_management_system_api.services.item import ItemService
from inventory_management_system_api.services.manufacturer import ManufacturerService
from inventory_management_system_api.services.system import SystemService


@pytest.fixture(name="catalogue_category_repository_mock")
def fixture_catalogue_category_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `CatalogueCategoryRepo` dependency.

    :return: Mocked CatalogueCategoryRepo instance.
    """
    return Mock(CatalogueCategoryRepo)


@pytest.fixture(name="catalogue_item_repository_mock")
def fixture_catalogue_item_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `CatalogueItemRepo` dependency.

    :return: Mocked CatalogueItemRepo instance.
    """
    return Mock(CatalogueItemRepo)


@pytest.fixture(name="item_repository_mock")
def fixture_item_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `ItemRepo` dependency.

    :return: Mocked ItemRepo instance.
    """
    return Mock(ItemRepo)


@pytest.fixture(name="manufacturer_repository_mock")
def fixture_manufacturer_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `ManufacturerRepo dependency

    :return: Mocked ManufacturerRepo instance
    """
    return Mock(ManufacturerRepo)


@pytest.fixture(name="system_repository_mock")
def fixture_system_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `SystemRepo` dependency.

    :return: Mocked SystemRepo instance.
    """
    return Mock(SystemRepo)


@pytest.fixture(name="catalogue_category_service")
def fixture_catalogue_category_service(catalogue_category_repository_mock: Mock) -> CatalogueCategoryService:
    """
    Fixture to create a `CatalogueCategoryService` instance with a mocked `CatalogueCategoryRepo` dependency.

    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :return: `CatalogueCategoryService` instance with the mocked dependency.
    """
    return CatalogueCategoryService(catalogue_category_repository_mock)


@pytest.fixture(name="catalogue_item_service")
def fixture_catalogue_item_service(
    catalogue_item_repository_mock: Mock, catalogue_category_repository_mock: Mock, manufacturer_repository_mock: Mock
) -> CatalogueItemService:
    """
    Fixture to create a `CatalogueItemService` instance with a mocked `CatalogueItemRepo` and `CatalogueCategoryRepo`
    dependencies.

    :param catalogue_item_repository_mock: Mocked `CatalogueItemRepo` instance.
    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :return: `CatalogueItemService` instance with the mocked dependency.
    """
    return CatalogueItemService(
        catalogue_item_repository_mock, catalogue_category_repository_mock, manufacturer_repository_mock
    )


@pytest.fixture(name="item_service")
def fixture_item_service(
    item_repository_mock: Mock,
    catalogue_category_repository_mock: Mock,
    catalogue_item_repository_mock: Mock,
    system_repository_mock: Mock,
) -> ItemService:
    """
    Fixture to create an `ItemService` instance with mocked `ItemRepo`, `CatalogueItemRepo`, and
    `CatalogueCategoryRepo` dependencies.

    :param item_repository_mock: Mocked `ItemRepo` instance.
    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :param catalogue_item_repository_mock: Mocked `CatalogueItemRepo` instance.
    :return: `ItemService` instance with the mocked dependencies.
    """
    return ItemService(
        item_repository_mock, catalogue_category_repository_mock, catalogue_item_repository_mock, system_repository_mock
    )


@pytest.fixture(name="manufacturer_service")
def fixture_manufacturer_service(manufacturer_repository_mock: Mock) -> ManufacturerService:
    """
    Fixture to create a `ManufacturerService` instance with a mocked `ManufacturerRepo`

    :param: manufacturer_repository_mock: Mocked `ManufacturerRepo` instance.
    :return: `ManufacturerService` instance with mocked dependency
    """
    return ManufacturerService(manufacturer_repository_mock)


@pytest.fixture(name="system_service")
def fixture_system_service(system_repository_mock: Mock) -> SystemService:
    """
    Fixture to create a `SystemService` instance with a mocked `SystemRepo`
    dependencies.

    :param system_repository_mock: Mocked `SystemRepo` instance
    :return: `SystemService` instance with the mocked dependency
    """
    return SystemService(system_repository_mock)


class ServiceTestHelpers:
    """
    A utility class containing common helper methods for the service tests.

    This class provides a set of static methods that encapsulate common functionality frequently used in the service
    tests.
    """

    @staticmethod
    def mock_create(
        repository_mock: Mock, repo_obj: Union[CatalogueCategoryOut, CatalogueItemOut, ItemOut, SystemOut]
    ) -> None:
        """
        Mock the `create` method of the repository mock to return a repository object.

        :param repository_mock: Mocked repository instance.
        :param repo_obj: The repository object to be returned by the `create` method.
        """
        repository_mock.create.return_value = repo_obj

    @staticmethod
    def mock_get(
        repository_mock: Mock, repo_obj: Union[CatalogueCategoryOut, CatalogueItemOut, ItemOut, SystemOut, None]
    ) -> None:
        """
        Mock the `get` method of the repository mock to return a specific repository object.

        :param repository_mock: Mocked repository instance.
        :param repo_obj: The repository object to be returned by the `get` method.
        """
        if repository_mock.get.side_effect is None:
            repository_mock.get.side_effect = [repo_obj]
        else:
            repo_objs = list(repository_mock.get.side_effect)
            repo_objs.append(repo_obj)
            repository_mock.get.side_effect = repo_objs

    @staticmethod
    def mock_get_breadcrumbs(repository_mock: Mock, breadcrumbs_obj: Union[BreadcrumbsGetSchema, None]) -> None:
        """
        Mock the `get_breadcrumbs` method of the repository mock to return a specific repository
        object

        :param repository_mock: Mocked repository instance.
        :param breadcrumbs_obj: The breadcrumbs object be returned by the `get_breadcrumbs` method.
        """
        if repository_mock.get_breadcrumbs.side_effect is None:
            repository_mock.get_breadcrumbs.side_effect = [breadcrumbs_obj]

    @staticmethod
    def mock_list(
        repository_mock: Mock,
        repo_objs: List[
            Union[
                CatalogueCategoryOut,
                CatalogueItemOut,
                ItemOut,
                SystemOut,
            ]
        ],
    ) -> None:
        """
        Mock the `list` method of the repository mock to return a specific list of repository objects.
        objects.

        :param repository_mock: Mocked repository instance.
        :param repo_objs: The list of repository objects to be returned by the `list` method.
        """
        repository_mock.list.return_value = repo_objs

    @staticmethod
    def mock_update(
        repository_mock: Mock,
        repo_obj: Union[
            CatalogueCategoryOut,
            CatalogueItemOut,
            ItemOut,
            SystemOut,
        ],
    ) -> None:
        """
        Mock the `update` method of the repository mock to return a repository object.

        :param repository_mock: Mocked repository instance.
        :param repo_obj: The repository object to be returned by the `update` method.
        """

        repository_mock.update.return_value = repo_obj


@pytest.fixture(name="test_helpers")
def fixture_test_helpers() -> Type[ServiceTestHelpers]:
    """
    Fixture to provide a TestHelpers class.
    """
    return ServiceTestHelpers
