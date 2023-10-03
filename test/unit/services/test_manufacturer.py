"""
Unit tests for the `ManufacturerService` service.
"""

from unittest.mock import Mock
import pytest
from bson import ObjectId

from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.schemas.manufacturer import ManufacturerPostRequestSchema
from inventory_management_system_api.services.manufacturer import ManufacturerService


@pytest.fixture(name="manufacturer_service")
def fixture_manufacturer_service(manufacturer_repository_mock: Mock) -> ManufacturerService:
    """
    Fixture to create a `ManufacturerService` instance with a mocked `ManufacturerRepo`

    :param: manufacturer_repository_mock: Mocked `ManufacturerRepo` instance.
    :return: `ManufacturerService` instance with mocked dependency
    """
    return ManufacturerService(manufacturer_repository_mock)


def test_create(manufacturer_repository_mock, manufacturer_service):
    """
    Testing creating a manufacturer
    """
     # pylint: disable=duplicate-code

    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )
     # pylint: enable=duplicate-code

    manufacturer_repository_mock.create.return_value = manufacturer

    created_manufacturer = manufacturer_service.create(
        ManufacturerPostRequestSchema(
            name=manufacturer.name,
            url=manufacturer.url,
            address=manufacturer.address,
        )
    )
    manufacturer_repository_mock.create.assert_called_once_with(
        ManufacturerIn(
            name=manufacturer.name,
            code=manufacturer.code,
            url=manufacturer.url,
            address=manufacturer.address,
        )
    )
    assert created_manufacturer == manufacturer


def test_list(manufacturer_repository_mock, manufacturer_service):
    """Test getting all manufacturers"""
    # pylint: disable=duplicate-code
    manufacturer_1 = ManufacturerOut(
        _id=str(ObjectId()),
        code="manufacturer-a",
        name="Manufacturer A",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )

    manufacturer_2 = ManufacturerOut(
        _id=str(ObjectId()),
        code="manufacturer-b",
        name="Manufacturer B",
        url="http://2ndTestUrl.co.uk",
        address="2 Example street",
    )
    # pylint: enable=duplicate-code
    manufacturer_repository_mock.list.return_value = [manufacturer_1, manufacturer_2]
    retrieved_manufacturer = manufacturer_service.list()
    manufacturer_repository_mock.list.assert_called_once_with()
    assert retrieved_manufacturer == [manufacturer_1, manufacturer_2]


def test_get(manufacturer_repository_mock, manufacturer_service):
    """Test getting a manufacturer by ID"""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        code="manufacturer-a",
        name="Manufacturer A",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )
    # pylint: enable=duplicate-code

    manufacturer_repository_mock.get.return_value = manufacturer

    retrieved_manufacturer = manufacturer_service.get(manufacturer.id)

    manufacturer_repository_mock.get.assert_called_once_with(manufacturer.id)
    assert retrieved_manufacturer == manufacturer


def test_get_with_nonexistent_id(manufacturer_repository_mock, manufacturer_service):
    """Test getting a manufacturer with an non-existent ID"""
    manufactuer_id = str(ObjectId())
    manufacturer_repository_mock.get.return_value = None
    retrieved_manufacturer = manufacturer_service.get(manufactuer_id)

    assert retrieved_manufacturer is None

    manufacturer_repository_mock.get.assert_called_once_with(manufactuer_id)
