"""
Unit tests for the `ManufacturerRepo` repository.
"""

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DuplicateRecordError
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut


def test_create_manufacturer(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer.

    Verify that the `create` method properly handles the manufacturer to be created, checks that there is not a
    duplicate manufacturer, and creates the manufacturer.
    """

    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="testUrl.co.uk",
        address="1 Example street",
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
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
        },
    )
    created_manufacturer = manufacturer_repository.create(
        ManufacturerIn(
            name=manufacturer.name,
            code=manufacturer.code,
            url=manufacturer.url,
            address=manufacturer.address,
        )
    )

    database_mock.manufacturer.insert_one.assert_called_once_with(
        {
            "name": manufacturer.name,
            "code": manufacturer.code,
            "url": manufacturer.url,
            "address": manufacturer.address,
        }
    )
    database_mock.manufacturer.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer.id)})
    assert created_manufacturer == manufacturer


def test_create_manufacturer_duplicate(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer with a duplicate code

    Verify that the `create` method properly handles a manufacturer with a duplicate name, finds that there is a
    duplicate manufacturer, and does not create the manufacturer.
    """
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()), name="Manufacturer B", code="manufacturer-b", url="duplicate.co.uk", address="street B"
    )

    # Mock count_documents to return 1 (duplicat manufacturer found)
    test_helpers.mock_count_documents(database_mock.manufacturer, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.create(
            ManufacturerIn(
                name=manufacturer.name,
                code=manufacturer.code,
                url=manufacturer.url,
                address=manufacturer.address,
            )
        )

    assert str(exc.value) == "Duplicate manufacturer found"


def test_get_all_manufacturers(test_helpers, database_mock, manufacturer_repository):
    """Test getting all manufacturers"""
    manufacturer_1 = ManufacturerOut(
        _id=str(ObjectId()),
        code="manufacturer-a",
        name="Manufacturer A",
        url="testUrl.co.uk",
        address="1 Example street",
    )

    manufacturer_2 = ManufacturerOut(
        _id=str(ObjectId()),
        code="manufacturer-b",
        name="Manufacturer B",
        url="2ndTestUrl.co.uk",
        address="2 Example street",
    )

    test_helpers.mock_find(
        database_mock.manufacturer,
        [
            {
                "_id": CustomObjectId(manufacturer_1.id),
                "code": manufacturer_1.code,
                "name": manufacturer_1.name,
                "url": manufacturer_1.url,
                "address": manufacturer_1.address,
            },
            {
                "_id": CustomObjectId(manufacturer_2.id),
                "code": manufacturer_2.code,
                "name": manufacturer_2.name,
                "url": manufacturer_2.url,
                "address": manufacturer_2.address,
            },
        ],
    )

    retrieved_manufacturers = manufacturer_repository.list()

    database_mock.manufacturer.find.assert_called_once_with()
    assert retrieved_manufacturers == [manufacturer_1, manufacturer_2]
