"""
Unit tests for the `ManufacturerService` service.
"""

from datetime import timedelta
from unittest.mock import MagicMock
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import MissingRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.schemas.manufacturer import (
    AddressSchema,
    ManufacturerPatchSchema,
    ManufacturerPostSchema,
)


def test_create(
    test_helpers,
    manufacturer_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    manufacturer_service,
):
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
            address_line="1 Example Street",
            town="Oxford",
            county="Oxfordshire",
            postcode="OX1 2AB",
            country="United Kingdom",
        ),
        telephone="0932348348",
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )
    # pylint: enable=duplicate-code

    # Mock `create` to return the created manufacturer
    test_helpers.mock_create(manufacturer_repository_mock, manufacturer)

    created_manufacturer = manufacturer_service.create(
        ManufacturerPostSchema(
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


def test_delete(manufacturer_repository_mock, manufacturer_service):
    """Test deleting a manufacturer"""
    manufacturer_id = str(ObjectId())

    manufacturer_service.delete(manufacturer_id)

    manufacturer_repository_mock.delete.assert_called_once_with(manufacturer_id)


def test_get(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test getting a manufacturer by ID"""
    manufacturer_id = str(ObjectId())
    manufacturer = MagicMock()

    # Mock `get` to return a manufacturer
    test_helpers.mock_get(manufacturer_repository_mock, manufacturer)

    retrieved_manufacturer = manufacturer_service.get(manufacturer_id)

    manufacturer_repository_mock.get.assert_called_once_with(manufacturer_id)
    assert retrieved_manufacturer == manufacturer


def test_get_with_non_existent_id(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test getting a manufacturer with an non-existent ID"""
    manufacturer_id = str(ObjectId())
    test_helpers.mock_get(manufacturer_repository_mock, None)

    # Mock `get` to return a manufacturer
    retrieved_manufacturer = manufacturer_service.get(manufacturer_id)

    assert retrieved_manufacturer is None
    manufacturer_repository_mock.get.assert_called_once_with(manufacturer_id)


def test_list(manufacturer_repository_mock, manufacturer_service):
    """Test getting all manufacturers"""
    result = manufacturer_service.list()

    manufacturer_repository_mock.list.assert_called_once()
    assert result == manufacturer_repository_mock.list.return_value


def test_update_with_non_existent_id(test_helpers, manufacturer_repository_mock, manufacturer_service):
    """Test updating a manufacturer with a non-existent id"""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            address_line="1 Example Street",
            town="Oxford",
            county="Oxfordshire",
            postcode="OX1 2AB",
            country="United Kingdom",
        ),
        telephone="0932348348",
        created_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
        modified_time=MODEL_MIXINS_FIXED_DATETIME_NOW,
    )
    # pylint: enable=duplicate-code

    # Mock `get` to not return a manufacturer
    test_helpers.mock_get(manufacturer_repository_mock, None)

    manufacturer_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        manufacturer_service.update(manufacturer_id, manufacturer)
    manufacturer_repository_mock.update.assert_not_called()
    assert str(exc.value) == "No manufacturer found with ID " + manufacturer_id


def test_partial_update_of_address(
    test_helpers,
    manufacturer_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    manufacturer_service,
):
    """Test the partial update of a manufacturer's address"""
    manufacturer_info = {
        "_id": str(ObjectId()),
        "name": "Manufacturer A",
        "code": "manufacturer-a",
        "url": "http://testUrl.co.uk",
        "address": {"address_line": "1 Example Street", "postcode": "AB1 2CD", "country": "United Kingdom"},
    }
    full_manufacturer_info = {
        **manufacturer_info,
        "address": {"address_line": "test", "postcode": "AB1 2CD", "country": "United Kingdom"},
        "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
        "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    }
    manufacturer = ManufacturerOut(**full_manufacturer_info)

    # Mock `get` to return a manufacturer
    test_helpers.mock_get(
        manufacturer_repository_mock,
        ManufacturerOut(
            **{
                **manufacturer_info,
                "created_time": manufacturer.created_time,
                "modified_time": manufacturer.created_time,
            }
        ),
    )

    # Mock `get` to return the updated manufacturer
    test_helpers.mock_update(manufacturer_repository_mock, manufacturer)

    updated_manufacturer = manufacturer_service.update(
        manufacturer.id,
        ManufacturerPatchSchema(address={"address_line": "test"}),
    )

    manufacturer_repository_mock.update.assert_called_once_with(
        manufacturer.id, ManufacturerIn(**full_manufacturer_info)
    )
    assert updated_manufacturer == manufacturer


def test_partial_update_of_manufacturer(
    test_helpers,
    manufacturer_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    manufacturer_service,
):
    """Test the partial update of a manufacturer's name"""
    manufacturer_info = {
        "_id": str(ObjectId()),
        "name": "Manufacturer A",
        "code": "manufacturer-a",
        "url": "http://testUrl.co.uk",
        "address": {"address_line": "1 Example Street", "postcode": "AB1 2CD", "country": "United Kingdom"},
    }
    full_manufacturer_info = {
        **manufacturer_info,
        "name": "test",
        "code": "test",
        "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW - timedelta(days=5),
        "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    }
    manufacturer = ManufacturerOut(**full_manufacturer_info)

    # Mock `get` to return a manufacturer
    test_helpers.mock_get(
        manufacturer_repository_mock,
        ManufacturerOut(
            **{
                **manufacturer_info,
                "created_time": manufacturer.created_time,
                "modified_time": manufacturer.created_time,
            }
        ),
    )

    # Mock `get` to return the updated manufacturer
    test_helpers.mock_update(manufacturer_repository_mock, manufacturer)

    updated_manufacturer = manufacturer_service.update(manufacturer.id, ManufacturerPatchSchema(name="test"))

    manufacturer_repository_mock.update.assert_called_once_with(
        manufacturer.id, ManufacturerIn(**full_manufacturer_info)
    )
    assert updated_manufacturer == manufacturer
