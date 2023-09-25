"""
Unit tests for the `ManufacturerRepo` repository.
"""

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DuplicateRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut, AddressProperty


def test_create_manufacturer(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer.

    Verify that the `create` method properly handles the manufacturer to be created, checks that there is not a
    duplicate manufacturer, and creates the manufacturer.
    """

    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        url="testUrl.co.uk",
        address=AddressProperty(
            name="Manufacturer A",
            street_name="1 Example street",
            city="Oxford",
            post_code="OX1 2AB",
            country="United Kingdom",
        ),
    )
    # Mock 'count documents' to return 0 (no duplicates found)
    test_helpers.mock_count_documents(database_mock.manufacturer, 0)
    # Mock 'insert one' to return object for inserted manufacturer
    test_helpers.mock_insert_one(database_mock.manufacturer, CustomObjectId(manufacturer.id))
    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturer,
        {
            "_id": CustomObjectId(manufacturer.id),
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
        },
    )
    created_manufacturer = manufacturer_repository.create(
        ManufacturerIn(
            name=manufacturer.name,
            url=manufacturer.url,
            address=manufacturer.address,
        )
    )

    database_mock.manufacturer.insert_one.assert_called_once_with(
        {
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
        }
    )
    database_mock.manufacturer.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer.id)})
    assert created_manufacturer == manufacturer


def test_create_manufacturer_with_duplicate_url(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer with a duplicate url

    Verify that the `create` method properly handles a manufacturer with a duplicate name, finds that there is a
    duplicate manufacturer, and does not create the manufacturer.
    """
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer B",
        url="duplicate.co.uk",
        address=AddressProperty(
            name="Manufacturer B",
            street_name="street B",
            city="City B",
            post_code="Post Code B",
            country="United Kingdom",
        ),
    )

    # Mock count_documents to return 1 (duplicat manufacturer found)
    test_helpers.mock_count_documents(database_mock.manufacturer, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.create(
            ManufacturerIn(
                name=manufacturer.name,
                url=manufacturer.url,
                address=manufacturer.address,
            )
        )

    assert str(exc.value) == "Duplicate manufacturer found"
