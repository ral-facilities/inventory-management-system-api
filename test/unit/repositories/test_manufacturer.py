"""
Unit tests for the `ManufacturerRepo` repository.
"""

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut


def test_create_manufacturer(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer.

    Verify that the `create` method properly handles the manufacturer to be created, checks that there is not a
    duplicate manufacturer, and creates the manufacturer.
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
    # pylint: disable=duplicate-code
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
    # pylint: enable=duplicate-code
    database_mock.manufacturer.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer.id)})
    assert created_manufacturer == manufacturer


def test_create_manufacturer_duplicate(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer with a duplicate code

    Verify that the `create` method properly handles a manufacturer with a duplicate name, finds that there is a
    duplicate manufacturer, and does not create the manufacturer.
    """
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer B",
        code="manufacturer-b",
        url="http://duplicate.co.uk",
        address="street B",
    )

    # Mock count_documents to return 1 (duplicat manufacturer found)
    test_helpers.mock_count_documents(database_mock.manufacturer, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.create(
            # pylint: disable=duplicate-code
            ManufacturerIn(
                name=manufacturer.name,
                code=manufacturer.code,
                url=manufacturer.url,
                address=manufacturer.address,
            )
        )
    # pylint: enable=duplicate-code
    assert str(exc.value) == "Duplicate manufacturer found"


def test_list(test_helpers, database_mock, manufacturer_repository):
    """Test getting all manufacturers"""
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


def test_list_when_no_manufacturers(test_helpers, database_mock, manufacturer_repository):
    """Test trying to get all manufacturers when there are none in the databse"""
    test_helpers.mock_find(database_mock.manufacturer, [])
    retrieved_manufacturers = manufacturer_repository.list()

    assert retrieved_manufacturers == []


def test_get_manufacturer_by_id(test_helpers, database_mock, manufacturer_repository):
    """
    Test getting a manufacturer by id
    """
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )
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
    retrieved_manufacturer = manufacturer_repository.get(manufacturer.id)
    database_mock.manufacturer.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer.id)})
    assert retrieved_manufacturer == manufacturer


def test_get_with_invalid_id(manufacturer_repository):
    """
    Test getting a manufacturer with an Invalid ID
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        manufacturer_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_nonexistent_id(test_helpers, database_mock, manufacturer_repository):
    """
    Test getting a manufacturer with an ID that does not exist
    """
    manufacturer_id = str(ObjectId())
    test_helpers.mock_find_one(database_mock.manufacturer, None)
    retrieved_manufacturer = manufacturer_repository.get(manufacturer_id)

    assert retrieved_manufacturer is None
    database_mock.manufacturer.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer_id)})


def test_update(test_helpers, database_mock, manufacturer_repository):
    """Test updating a manufacturer"""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )
    # pylint: enable=duplicate-code
    test_helpers.mock_count_documents(database_mock.manufacturer, 0)

    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturer,
        {
            "_id": CustomObjectId(manufacturer.id),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": "2 Example Street",
        },
    )
    test_helpers.mock_count_documents(database_mock.manufacturer, 0)

    test_helpers.mock_update_one(database_mock.manufacturer)
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

    # pylint: disable=duplicate-code

    updated_manufacturer = manufacturer_repository.update(
        manufacturer.id,
        ManufacturerIn(
            name=manufacturer.name,
            code=manufacturer.code,
            url=manufacturer.url,
            address=manufacturer.address,
        ),
    )
    # pylint: enable=duplicate-code

    database_mock.manufacturer.update_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)},
        {
            "$set": {
                "name": manufacturer.name,
                "code": manufacturer.code,
                "url": manufacturer.url,
                "address": manufacturer.address,
            }
        },
    )

    assert updated_manufacturer == manufacturer


def test_update_with_invalid_id(manufacturer_repository):
    """Test trying to update with an invalid ID"""
    updated_manufacturer = ManufacturerIn(
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )

    manufactuer_id = "invalid"
    with pytest.raises(InvalidObjectIdError) as exc:
        manufacturer_repository.update(manufactuer_id, updated_manufacturer)
    assert str(exc.value) == "Invalid ObjectId value"


def test_update_with_nonexistent_id(test_helpers, database_mock, manufacturer_repository):
    """Test trying to update with a non-existent ID"""
    updated_manufacturer = ManufacturerIn(
        name="Manufacturer B",
        code="manufacturer-b",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )
    test_helpers.mock_count_documents(database_mock.manufacturer, 0)
    test_helpers.mock_find_one(database_mock.manufacturer, None)
    manufacturer_id = str(ObjectId())

    with pytest.raises(MissingRecordError) as exc:
        manufacturer_repository.update(manufacturer_id, updated_manufacturer)
    assert str(exc.value) == "The specified manufacturer does not exist"


def test_update_duplicate_name(test_helpers, database_mock, manufacturer_repository):
    """Test trying to update a mnaufactuer using a duplicate name"""

    # pylint: disable=duplicate-code
    updated_manufacturer = ManufacturerIn(
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address="1 Example street",
    )
    # pylint: enable=duplicate-code
    test_helpers.mock_count_documents(database_mock.manufacturer, 0)
    manufacturer_id = str(ObjectId())
    test_helpers.mock_find_one(
        database_mock.manufacturer,
        {
            "_id": CustomObjectId(manufacturer_id),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": "2 Example Street",
        },
    )
    test_helpers.mock_count_documents(database_mock.manufacturer, 1)
    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.update(manufacturer_id, updated_manufacturer)
    assert str(exc.value) == "Duplicate manufacturer found"