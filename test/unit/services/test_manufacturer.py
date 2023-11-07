"""
Unit tests for the `ManufacturerService` service.
"""

from bson import ObjectId
import pytest
from inventory_management_system_api.core.exceptions import MissingRecordError

from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.schemas.manufacturer import (
    AddressSchema,
    ManufacturerPatchRequestSchema,
    ManufacturerPostRequestSchema,
)


def test_create(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """
    Testing creating a manufacturer
    """
    # pylint: disable=duplicate-code

    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )
    # pylint: enable=duplicate-code

    test_helpers.mock_create(manufacturer_repository_mock, manufacturer)

    created_manufacturer = manufacturer_service.create(
        ManufacturerPostRequestSchema(
            name=manufacturer.name,
            url=manufacturer.url,
            address=manufacturer.address,
            telephone=manufacturer.telephone,
        )
    )
    manufacturer_repository_mock.create.assert_called_once_with(
        ManufacturerIn(
            name=manufacturer.name,
            code=manufacturer.code,
            url=manufacturer.url,
            address=manufacturer.address,
            telephone=manufacturer.telephone,
        )
    )
    assert created_manufacturer == manufacturer


def test_list(manufacturer_repository_mock, manufacturer_service):
    """Test getting all manufacturers"""
    # pylint: disable=duplicate-code
    manufacturer_1 = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )

    manufacturer_2 = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer B",
        code="manufacturer-b",
        url="http://example.co.uk",
        address=AddressSchema(
            building_number="2", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 3AB"
        ),
        telephone="073434394",
    )
    # pylint: enable=duplicate-code
    manufacturer_repository_mock.list.return_value = [manufacturer_1, manufacturer_2]
    retrieved_manufacturer = manufacturer_service.list()
    manufacturer_repository_mock.list.assert_called_once_with()
    assert retrieved_manufacturer == [manufacturer_1, manufacturer_2]


def test_get(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test getting a manufacturer by ID"""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )
    # pylint: enable=duplicate-code

    test_helpers.mock_get(manufacturer_repository_mock, manufacturer)

    retrieved_manufacturer = manufacturer_service.get(manufacturer.id)

    manufacturer_repository_mock.get.assert_called_once_with(manufacturer.id)
    assert retrieved_manufacturer == manufacturer


def test_get_with_nonexistent_id(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test getting a manufacturer with an non-existent ID"""
    manufactuer_id = str(ObjectId())
    test_helpers.mock_get(manufacturer_repository_mock, None)
    retrieved_manufacturer = manufacturer_service.get(manufactuer_id)

    assert retrieved_manufacturer is None

    manufacturer_repository_mock.get.assert_called_once_with(manufactuer_id)


def test_delete(manufacturer_repository_mock, manufacturer_service):
    """Test deleting a manufacturer"""
    manufacturer_id = str(ObjectId())
    manufacturer_service.delete(manufacturer_id)

    manufacturer_repository_mock.delete.assert_called_once_with(manufacturer_id)


def test_updated_with_nonexistent_id(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test updating a manufacturer with a nonexistant id"""
    # pylint: disable=duplicate-code

    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )

    # pylint: enable=duplicate-code
    test_helpers.mock_get(manufacturer_repository_mock, None)
    manufacturer_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        manufacturer_service.update(manufacturer_id, manufacturer)
    assert str(exc.value) == "No manufacturer found with ID " + manufacturer_id


def test_partial_update_of_address(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test the partial update of a manufacturer's address"""
    manufacturer_info = {
        "_id": str(ObjectId()),
        "name": "Manufacturer A",
        "code": "manufacturer-a",
        "url": "http://testUrl.co.uk",
        "address": {"building_number": "1", "street_name": "Example Street", "postcode": "AB1 2CD"},
    }

    full_manufacturer_info = {
        **manufacturer_info,
        "address": {"building_number": "1", "street_name": "test", "postcode": "AB1 2CD"},
    }

    manufacturer = ManufacturerOut(**full_manufacturer_info)

    test_helpers.mock_get(
        manufacturer_repository_mock,
        ManufacturerOut(**manufacturer_info),
    )

    test_helpers.mock_update(manufacturer_repository_mock, manufacturer)

    updated_manufacturer = manufacturer_service.update(
        manufacturer.id,
        ManufacturerPatchRequestSchema(address={"street_name": "test"}),
    )

    manufacturer_repository_mock.update.assert_called_once_with(
        manufacturer.id, ManufacturerIn(**full_manufacturer_info)
    )

    assert updated_manufacturer == manufacturer


def test_partial_update_of_manufacturer(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test the partial update of a manufacturer's name"""
    manufacturer_info = {
        "_id": str(ObjectId()),
        "name": "Manufacturer A",
        "code": "manufacturer-a",
        "url": "http://testUrl.co.uk",
        "address": {"building_number": "1", "street_name": "Example Street", "postcode": "AB1 2CD"},
    }

    full_manufacturer_info = {**manufacturer_info, "name": "test", "code": "test"}

    manufacturer = ManufacturerOut(**full_manufacturer_info)

    test_helpers.mock_get(
        manufacturer_repository_mock,
        ManufacturerOut(**manufacturer_info),
    )

    test_helpers.mock_update(manufacturer_repository_mock, manufacturer)

    updated_manufacturer = manufacturer_service.update(manufacturer.id, ManufacturerPatchRequestSchema(name="test"))

    manufacturer_repository_mock.update.assert_called_once_with(
        manufacturer.id, ManufacturerIn(**full_manufacturer_info)
    )

    assert updated_manufacturer == manufacturer
