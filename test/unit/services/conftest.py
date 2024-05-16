"""
Module for providing common test configuration and test fixtures.
"""

from datetime import datetime, timezone
from typing import List, Type, Union
from unittest.mock import Mock, patch

import pytest

from inventory_management_system_api.models.catalogue_category import CatalogueCategoryOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut
from inventory_management_system_api.models.item import ItemOut
from inventory_management_system_api.models.system import SystemOut
from inventory_management_system_api.models.units import UnitOut
from inventory_management_system_api.models.usage_status import UsageStatusOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.item import ItemRepo
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.repositories.system import SystemRepo
from inventory_management_system_api.repositories.unit import UnitRepo
from inventory_management_system_api.repositories.usage_status import UsageStatusRepo
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService
from inventory_management_system_api.services.catalogue_category_property import CatalogueCategoryPropertyService
from inventory_management_system_api.services.catalogue_item import CatalogueItemService
from inventory_management_system_api.services.item import ItemService
from inventory_management_system_api.services.manufacturer import ManufacturerService
from inventory_management_system_api.services.system import SystemService
from inventory_management_system_api.services.unit import UnitService
from inventory_management_system_api.services.usage_status import UsageStatusService


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


@pytest.fixture(name="unit_repository_mock")
def fixture_unit_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `UnitRepo` dependency.

    :return: Mocked UnitRepo instance.
    """
    return Mock(UnitRepo)


@pytest.fixture(name="usage_status_repository_mock")
def fixture_usage_status_repository_mock() -> Mock:
    """
    Fixture to create a mock of the `UsageStatusRepo` dependency.

    :return: Mocked UsageStatusRepo instance.
    """
    return Mock(UsageStatusRepo)


@pytest.fixture(name="catalogue_category_service")
def fixture_catalogue_category_service(
    catalogue_category_repository_mock: Mock, unit_repository_mock: Mock
) -> CatalogueCategoryService:
    """
    Fixture to create a `CatalogueCategoryService` instance with a mocked `CatalogueCategoryRepo` and `UnitRepo`
    dependency.

    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :param unit_repository_mock: Mocked `UnitRepo` instance.
    :return: `CatalogueCategoryService` instance with the mocked dependency.
    """
    return CatalogueCategoryService(catalogue_category_repository_mock, unit_repository_mock)


@pytest.fixture(name="catalogue_category_property_service")
def fixture_catalogue_category_property_service(
    catalogue_category_repository_mock: Mock, catalogue_item_repository_mock: Mock, item_repository_mock: Mock
) -> CatalogueCategoryPropertyService:
    """
    Fixture to create a `CatalogueCategoryPropertyService` instance with mocked `CatalogueCategoryRepo`,
    `CatalogueItemRepo`, and `ItemRepo` dependencies.

    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :param catalogue_item_repository_mock: Mocked `CatalogueItemRepo` instance.
    :param item_repository_mock: Mocked `ItemRepo` instance.
    :return: `CatalogueCategoryPropertyService` instance with the mocked dependencies.
    """
    return CatalogueCategoryPropertyService(
        catalogue_category_repository_mock, catalogue_item_repository_mock, item_repository_mock
    )


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
    usage_status_repository_mock: Mock,
) -> ItemService:
    """
    Fixture to create an `ItemService` instance with mocked `ItemRepo`, `CatalogueItemRepo`,
    `CatalogueCategoryRepo`, `SystemRepo` and `UsageStatusRepo` dependencies.

    :param item_repository_mock: Mocked `ItemRepo` instance.
    :param catalogue_category_repository_mock: Mocked `CatalogueCategoryRepo` instance.
    :param catalogue_item_repository_mock: Mocked `CatalogueItemRepo` instance.
    :return: `ItemService` instance with the mocked dependencies.
    """
    return ItemService(
        item_repository_mock,
        catalogue_category_repository_mock,
        catalogue_item_repository_mock,
        system_repository_mock,
        usage_status_repository_mock,
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


@pytest.fixture(name="unit_service")
def fixture_unit_service(unit_repository_mock: Mock) -> UnitService:
    """
    Fixture to create a `UnitService` instance with a mocked `UnitRepo`
    dependencies.

    :param unit_repository_mock: Mocked `UnitRepo` instance
    :return: `UnitService` instance with the mocked dependency
    """
    return UnitService(unit_repository_mock)


@pytest.fixture(name="usage_status_service")
def fixture_usage_status_service(usage_status_repository_mock: Mock) -> UsageStatusService:
    """
    Fixture to create a `UsageStatusService` instance with a mocked `UsageStatusRepo`
    dependencies.

    :param usage_status_repository_mock: Mocked `UsageStatusRepo` instance
    :return: `UsageStatusService` instance with the mocked dependency
    """
    return UsageStatusService(usage_status_repository_mock)


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
        repository_mock: Mock,
        repo_obj: Union[CatalogueCategoryOut, CatalogueItemOut, ItemOut, SystemOut, UnitOut, None],
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
        repo_objs: List[Union[CatalogueCategoryOut, CatalogueItemOut, ItemOut, SystemOut, UsageStatusOut]],
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


MODEL_MIXINS_FIXED_DATETIME_NOW = datetime(2024, 2, 16, 14, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(name="model_mixins_datetime_now_mock")
def fixture_model_mixins_datetime_now_mock():
    """
    Fixture that mocks the `datetime.now` method in the `inventory_management_system_api.models.mixins.datetime` module.
    """
    with patch("inventory_management_system_api.models.mixins.datetime") as mock_datetime:
        mock_datetime.now.return_value = MODEL_MIXINS_FIXED_DATETIME_NOW
        yield mock_datetime
