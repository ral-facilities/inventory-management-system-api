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
    PartOfCatalogueItemError,
)
from inventory_management_system_api.models.manufacturer import ManufacturerIn, ManufacturerOut
from inventory_management_system_api.schemas.manufacturer import AddressSchema


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
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )
    # pylint: enable=duplicate-code

    # Mock 'count documents' to return 0 (no duplicates found)
    test_helpers.mock_count_documents(database_mock.manufacturers, 0)
    # Mock 'insert one' to return object for inserted manufacturer
    test_helpers.mock_insert_one(database_mock.manufacturers, CustomObjectId(manufacturer.id))
    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer.id),
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
            "telephone": manufacturer.telephone,
        },
    )
    # pylint: disable=duplicate-code

    manufacturer_in = ManufacturerIn(**manufacturer.model_dump())
    # pylint: disable=duplicate-code
    created_manufacturer = manufacturer_repository.create(manufacturer_in)

    database_mock.manufacturer.insert_one.assert_called_once_with(manufacturer_in.model_dump())
    # pylint: enable=duplicate-code
    database_mock.manufacturers.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer.id)})
    assert created_manufacturer == manufacturer


def test_create_manufacturer_duplicate(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer with a duplicate code

    Verify that the `create` method properly handles a manufacturer with a duplicate name, finds that there is a
    duplicate manufacturer, and does not create the manufacturer.
    """
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

    # Mock count_documents to return 1 (duplicate manufacturer found)
    test_helpers.mock_count_documents(database_mock.manufacturers, 1)

    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.create(
            # pylint: disable=duplicate-code
            ManufacturerIn(
                name=manufacturer.name,
                code=manufacturer.code,
                url=manufacturer.url,
                address=manufacturer.address,
                telephone=manufacturer.telephone,
            )
        )
    # pylint: enable=duplicate-code
    assert str(exc.value) == "Duplicate manufacturer found"


def test_list(test_helpers, database_mock, manufacturer_repository):
    """Test getting all manufacturers"""
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

    test_helpers.mock_find(
        database_mock.manufacturers,
        [
            {
                "_id": CustomObjectId(manufacturer_1.id),
                "code": manufacturer_1.code,
                "name": manufacturer_1.name,
                "url": manufacturer_1.url,
                "address": manufacturer_1.address,
                "telephone": manufacturer_1.telephone,
            },
            {
                "_id": CustomObjectId(manufacturer_2.id),
                "code": manufacturer_2.code,
                "name": manufacturer_2.name,
                "url": manufacturer_2.url,
                "address": manufacturer_2.address,
                "telephone": manufacturer_2.telephone,
            },
        ],
    )

    retrieved_manufacturers = manufacturer_repository.list()

    database_mock.manufacturers.find.assert_called_once()
    assert retrieved_manufacturers == [manufacturer_1, manufacturer_2]


def test_list_when_no_manufacturers(test_helpers, database_mock, manufacturer_repository):
    """Test trying to get all manufacturers when there are none in the databse"""
    test_helpers.mock_find(database_mock.manufacturers, [])
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
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer.id),
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
            "telephone": manufacturer.telephone,
        },
    )
    retrieved_manufacturer = manufacturer_repository.get(manufacturer.id)
    database_mock.manufacturers.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer.id)})
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
    test_helpers.mock_find_one(database_mock.manufacturers, None)
    retrieved_manufacturer = manufacturer_repository.get(manufacturer_id)

    assert retrieved_manufacturer is None
    database_mock.manufacturers.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer_id)})


def test_update(test_helpers, database_mock, manufacturer_repository):
    """Test updating a manufacturer"""
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
    test_helpers.mock_count_documents(database_mock.manufacturers, 0)

    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer.id),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": {
                "building_number": "2",
                "street_name": "Test street",
                "town": "Newbury",
                "county": "Berkshire",
                "postcode": "QW2 4DF",
            },
            "telephone": "0348343897",
        },
    )

    test_helpers.mock_update_one(database_mock.manufacturers)
    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer.id),
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
            "telephone": manufacturer.telephone,
        },
    )

    manufacturer_in = ManufacturerIn(**manufacturer.model_dump())
    # pylint: disable=duplicate-code
    updated_manufacturer = manufacturer_repository.update(
        manufacturer.id,
        ManufacturerIn(**manufacturer_in.model_dump()),
    )
    # pylint: enable=duplicate-code

    database_mock.manufacturers.update_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)},
        {"$set": manufacturer_in.model_dump()},
    )

    assert updated_manufacturer == manufacturer


def test_update_with_invalid_id(manufacturer_repository):
    """Test trying to update with an invalid ID"""
    updated_manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )

    manufactuer_id = "invalid"
    with pytest.raises(InvalidObjectIdError) as exc:
        manufacturer_repository.update(manufactuer_id, updated_manufacturer)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_update_with_duplicate_name(test_helpers, database_mock, manufacturer_repository):
    """Testing trying to update a manufacturer's name to one that already exists in the database"""

    updated_manufacturer = ManufacturerOut(
        _id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testUrl.co.uk",
        address=AddressSchema(
            building_number="1", street_name="Example Street", town="Oxford", county="Oxfordshire", postcode="OX1 2AB"
        ),
        telephone="0932348348",
    )

    manufacturer_id = str(ObjectId())

    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer_id),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": {
                "building_number": "2",
                "street_name": "Test street",
                "town": "Newbury",
                "county": "Berkshire",
                "postcode": "QW2 4DF",
            },
            "telephone": "0348343897",
        },
    )
    test_helpers.mock_count_documents(database_mock.manufacturers, 1)
    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.update(manufacturer_id, updated_manufacturer)

    assert str(exc.value) == "Duplicate manufacturer found"


def test_partial_update_address(test_helpers, database_mock, manufacturer_repository):
    """Test partially updating a manufacturer address"""
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

    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer.id),
            "name": "Manufacturer A",
            "code": "manufacturer-a",
            "url": "http://testUrl.co.uk",
            "address": {"building_number": "100", "street_name": "test", "postcode": "test"},
            "telephone": "0932348348",
        },
    )

    test_helpers.mock_count_documents(database_mock.manufacturers, 0)

    test_helpers.mock_update_one(database_mock.manufacturers)

    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": CustomObjectId(manufacturer.id),
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
            "telephone": manufacturer.telephone,
        },
    )

    updated_manufacturer = manufacturer_repository.update(
        manufacturer.id,
        ManufacturerIn(
            name=manufacturer.name,
            code=manufacturer.code,
            url=manufacturer.url,
            address=AddressSchema(building_number="100", street_name="test", postcode="test"),
            telephone=manufacturer.telephone,
        ),
    )

    database_mock.manufacturers.update_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)},
        {
            "$set": {
                "name": "Manufacturer A",
                "code": "manufacturer-a",
                "url": "http://testUrl.co.uk",
                "address": {
                    "building_number": "100",
                    "street_name": "test",
                    "town": None,
                    "county": None,
                    "country": None,
                    "postcode": "test",
                },
                "telephone": "0932348348",
            },
        },
    )
    assert updated_manufacturer == manufacturer


def test_delete(test_helpers, database_mock, manufacturer_repository):
    """Test trying to delete a manufacturer"""
    manufacturer_id = str(ObjectId())

    test_helpers.mock_delete_one(database_mock.manufacturers, 1)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)
    manufacturer_repository.delete(manufacturer_id)

    database_mock.manufacturers.delete_one.assert_called_once_with({"_id": CustomObjectId(manufacturer_id)})


def test_delete_with_an_invalid_id(manufacturer_repository):
    """Test trying to delete a manufacturer with an invalid ID"""
    manufacturer_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        manufacturer_repository.delete(manufacturer_id)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_a_nonexistent_id(test_helpers, database_mock, manufacturer_repository):
    """Test trying to delete a manufacturer with a non-existent ID"""
    manufacturer_id = str(ObjectId())

    test_helpers.mock_delete_one(database_mock.manufacturers, 0)
    test_helpers.mock_count_documents(database_mock.catalogue_items, 0)

    with pytest.raises(MissingRecordError) as exc:
        manufacturer_repository.delete(manufacturer_id)
    assert str(exc.value) == f"No manufacturer found with ID: {manufacturer_id}"
    database_mock.manufacturers.delete_one.assert_called_once_with({"_id": CustomObjectId(manufacturer_id)})


def test_delete_manufacturer_that_is_part_of_a_catalogue_item(test_helpers, database_mock, manufacturer_repository):
    """Test trying to delete a manufacturer that is part of a Catalogue Item"""
    manufacturer_id = str(ObjectId())

    test_helpers.mock_count_documents(database_mock.catalogue_items, 1)

    with pytest.raises(PartOfCatalogueItemError) as exc:
        manufacturer_repository.delete(manufacturer_id)
    assert str(exc.value) == f"The manufacturer with id {str(manufacturer_id)} is a part of a Catalogue Item"
