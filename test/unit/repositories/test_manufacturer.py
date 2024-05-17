"""
Unit tests for the `ManufacturerRepo` repository.
"""

from unittest.mock import MagicMock, call
from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from test.unit.repositories.test_catalogue_item import FULL_CATALOGUE_ITEM_A_INFO
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


def test_create(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer.

    Verify that the `create` method properly handles the manufacturer to be created, checks that there is not a
    duplicate manufacturer, and creates the manufacturer.
    """
    # pylint: disable=duplicate-code
    manufacturer_in = ManufacturerIn(
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
    )
    manufacturer_info = manufacturer_in.model_dump()
    manufacturer_out = ManufacturerOut(
        **manufacturer_info,
        id=str(ObjectId()),
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate manufacturers found
    test_helpers.mock_find_one(database_mock.manufacturers, None)
    # Mock 'insert one' to return object for inserted manufacturer
    test_helpers.mock_insert_one(database_mock.manufacturers, CustomObjectId(manufacturer_out.id))
    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **manufacturer_info,
            "_id": CustomObjectId(manufacturer_out.id),
        },
    )

    created_manufacturer = manufacturer_repository.create(manufacturer_in, session=session)

    database_mock.manufacturers.insert_one.assert_called_once_with(manufacturer_in.model_dump(), session=session)
    database_mock.manufacturers.find_one.assert_has_calls(
        [
            call({"code": manufacturer_out.code}, session=session),
            call({"_id": CustomObjectId(manufacturer_out.id)}, session=session),
        ]
    )
    assert created_manufacturer == manufacturer_out


def test_create_manufacturer_duplicate(test_helpers, database_mock, manufacturer_repository):
    """
    Test creating a manufacturer with a duplicate code

    Verify that the `create` method properly handles a manufacturer with a duplicate name, finds that there is a
    duplicate manufacturer, and does not create the manufacturer.
    """
    manufacturer_in = ManufacturerIn(
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
    )
    manufacturer_info = manufacturer_in.model_dump()
    manufacturer_out = ManufacturerOut(
        **manufacturer_info,
        id=str(ObjectId()),
    )

    # Mock `find_one` to return duplicate manufacturer found
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **manufacturer_info,
            "_id": CustomObjectId(manufacturer_out.id),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.create(manufacturer_out)
    assert str(exc.value) == "Duplicate manufacturer found"


def test_list(test_helpers, database_mock, manufacturer_repository):
    """Test getting all manufacturers"""
    manufacturer_1 = ManufacturerOut(
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
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
    )

    manufacturer_2 = ManufacturerOut(
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        name="Manufacturer B",
        code="manufacturer-b",
        url="http://example.co.uk",
        address=AddressSchema(
            address_line="2 Example Street",
            town="Oxford",
            county="Oxfordshire",
            postcode="OX1 3AB",
            country="United Kingdom",
        ),
        telephone="073434394",
    )
    session = MagicMock()

    test_helpers.mock_find(
        database_mock.manufacturers,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(manufacturer_1.id),
                "code": manufacturer_1.code,
                "name": manufacturer_1.name,
                "url": manufacturer_1.url,
                "address": manufacturer_1.address,
                "telephone": manufacturer_1.telephone,
            },
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(manufacturer_2.id),
                "code": manufacturer_2.code,
                "name": manufacturer_2.name,
                "url": manufacturer_2.url,
                "address": manufacturer_2.address,
                "telephone": manufacturer_2.telephone,
            },
        ],
    )

    retrieved_manufacturers = manufacturer_repository.list(session=session)

    database_mock.manufacturers.find.assert_called_once_with(session=session)
    assert retrieved_manufacturers == [manufacturer_1, manufacturer_2]


def test_list_when_no_manufacturers(test_helpers, database_mock, manufacturer_repository):
    """Test trying to get all manufacturers when there are none in the databse"""
    test_helpers.mock_find(database_mock.manufacturers, [])
    retrieved_manufacturers = manufacturer_repository.list()

    assert retrieved_manufacturers == []


def test_get(test_helpers, database_mock, manufacturer_repository):
    """
    Test getting a manufacturer by id
    """
    manufacturer = ManufacturerOut(
        id=str(ObjectId()),
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
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()

    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer.id),
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
            "telephone": manufacturer.telephone,
        },
    )
    retrieved_manufacturer = manufacturer_repository.get(manufacturer.id, session=session)
    database_mock.manufacturers.find_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)}, session=session
    )
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
    database_mock.manufacturers.find_one.assert_called_once_with({"_id": CustomObjectId(manufacturer_id)}, session=None)


def test_update_change_captialistion_of_name(test_helpers, database_mock, manufacturer_repository):
    """Test updating a manufacturer when the code is the same and the captialisation of the name has changed."""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        id=str(ObjectId()),
        name="MaNuFaCtUrEr A",
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
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock 'find_one' to return the existing manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer.id),
            "code": "manufacturer-a",
            "name": "Manufacturer A",
            "url": "http://testUrl.co.uk",
            "address": {
                "address_line": "1 Example Street",
                "town": "Oxford",
                "county": "Oxfordshire",
                "postcode": "OX1 2AB",
                "country": "United Kingdom",
            },
            "telephone": "0932348348",
        },
    )

    # Mock `find_one` to return a duplicate manufacturer but with the same id as the one being updated
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer.id),
            "code": "manufacturer-a",
            "name": "Manufacturer A",
            "url": "http://testUrl.co.uk",
            "address": {
                "address_line": "1 Example Street",
                "town": "Oxford",
                "county": "Oxfordshire",
                "postcode": "OX1 2AB",
                "country": "United Kingdom",
            },
            "telephone": "0932348348",
        },
    )

    test_helpers.mock_update_one(database_mock.manufacturers)
    # Mock 'find_one' to return the inserted manufacturer document
    manufacturer_in = ManufacturerIn(**manufacturer.model_dump())
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **manufacturer_in.model_dump(),
            "_id": CustomObjectId(manufacturer.id),
        },
    )

    # pylint: disable=duplicate-code
    updated_manufacturer = manufacturer_repository.update(manufacturer.id, manufacturer_in, session=session)
    # pylint: enable=duplicate-code

    database_mock.manufacturers.update_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)}, {"$set": manufacturer_in.model_dump()}, session=session
    )

    assert updated_manufacturer == ManufacturerOut(id=manufacturer.id, **manufacturer_in.model_dump())


def test_update(test_helpers, database_mock, manufacturer_repository):
    """Test updating a manufacturer"""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        id=str(ObjectId()),
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
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock 'find_one' to return the existing manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer.id),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": {
                "address_line": "2 Test Street",
                "town": "Newbury",
                "county": "Berkshire",
                "postcode": "QW2 4DF",
                "country": "United Kingdom",
            },
            "telephone": "0348343897",
        },
    )

    # Mock `find_one` to return no duplicate manufacturers found
    test_helpers.mock_find_one(database_mock.manufacturers, None)

    test_helpers.mock_update_one(database_mock.manufacturers)
    # Mock 'find_one' to return the inserted manufacturer document
    manufacturer_in = ManufacturerIn(**manufacturer.model_dump())
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **manufacturer_in.model_dump(),
            "_id": CustomObjectId(manufacturer.id),
        },
    )

    # pylint: disable=duplicate-code
    updated_manufacturer = manufacturer_repository.update(manufacturer.id, manufacturer_in, session=session)
    # pylint: enable=duplicate-code

    database_mock.manufacturers.update_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)}, {"$set": manufacturer_in.model_dump()}, session=session
    )

    assert updated_manufacturer == ManufacturerOut(id=manufacturer.id, **manufacturer_in.model_dump())


def test_update_with_invalid_id(manufacturer_repository):
    """Test trying to update with an invalid ID"""

    updated_manufacturer = MagicMock()
    manufactuer_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        manufacturer_repository.update(manufactuer_id, updated_manufacturer)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_update_with_duplicate_name(test_helpers, database_mock, manufacturer_repository):
    """Testing trying to update a manufacturer's name to one that already exists in the database"""

    updated_manufacturer = ManufacturerIn(
        **MOCK_CREATED_MODIFIED_TIME,
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
    )

    manufacturer_id = str(ObjectId())

    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer_id),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": {
                "address_line": "2 Example Street",
                "town": "Newbury",
                "county": "Berkshire",
                "postcode": "QW2 4DF",
                "country": "United Kingdom",
            },
            "telephone": "0348343897",
            **MOCK_CREATED_MODIFIED_TIME,
        },
    )

    # Mock `find_one` to return duplicate manufacturer found
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            "_id": ObjectId(),
            "code": "manufacturer-b",
            "name": "Manufacturer B",
            "url": "http://example.com",
            "address": {
                "address_line": "2 Example Street",
                "town": "Newbury",
                "county": "Berkshire",
                "postcode": "QW2 4DF",
                "country": "United Kingdom",
            },
            "telephone": "0348343897",
            **MOCK_CREATED_MODIFIED_TIME,
        },
    )

    # Mock `find_one` to return no child catalogue item document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    with pytest.raises(DuplicateRecordError) as exc:
        manufacturer_repository.update(manufacturer_id, updated_manufacturer)

    assert str(exc.value) == "Duplicate manufacturer found"


def test_partial_update_address(test_helpers, database_mock, manufacturer_repository):
    """Test partially updating a manufacturer address"""
    # pylint: disable=duplicate-code
    manufacturer = ManufacturerOut(
        id=str(ObjectId()),
        name="Manufacturer A",
        code="manufacturer-a",
        url="http://testurl.co.uk/",
        address=AddressSchema(
            address_line="1 Example Street",
            town="Oxford",
            county="Oxfordshire",
            postcode="OX1 2AB",
            country="United Kingdom",
        ),
        telephone="0932348348",
        **MOCK_CREATED_MODIFIED_TIME,
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return the existing manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer.id),
            "name": "Manufacturer A",
            "code": "manufacturer-a",
            "url": "http://testurl.co.uk/",
            "address": {"address_line": "100 Test Street", "postcode": "test", "country": "test"},
            "telephone": "0932348348",
        },
    )

    # Mock `find_one` to return no child catalogue item document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    test_helpers.mock_update_one(database_mock.manufacturers)

    # Mock 'find_one' to return the inserted manufacturer document
    test_helpers.mock_find_one(
        database_mock.manufacturers,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(manufacturer.id),
            "code": manufacturer.code,
            "name": manufacturer.name,
            "url": manufacturer.url,
            "address": manufacturer.address,
            "telephone": manufacturer.telephone,
        },
    )

    manufacturer_in = ManufacturerIn(
        name=manufacturer.name,
        code=manufacturer.code,
        url=manufacturer.url,
        address=AddressSchema(address_line="100 Test Street", postcode="test", country="test"),
        telephone=manufacturer.telephone,
    )

    updated_manufacturer = manufacturer_repository.update(manufacturer.id, manufacturer_in, session=session)

    database_mock.manufacturers.update_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer.id)},
        {
            "$set": manufacturer_in.model_dump(),
        },
        session=session,
    )
    assert updated_manufacturer == manufacturer


def test_delete(test_helpers, database_mock, manufacturer_repository):
    """Test trying to delete a manufacturer"""
    manufacturer_id = str(ObjectId())
    session = MagicMock()

    test_helpers.mock_delete_one(database_mock.manufacturers, 1)

    # Mock `find_one` to return no child catalogue item document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    manufacturer_repository.delete(manufacturer_id, session=session)

    database_mock.manufacturers.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer_id)}, session=session
    )


def test_delete_with_an_invalid_id(manufacturer_repository):
    """Test trying to delete a manufacturer with an invalid ID"""
    manufacturer_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        manufacturer_repository.delete(manufacturer_id)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_a_non_existent_id(test_helpers, database_mock, manufacturer_repository):
    """Test trying to delete a manufacturer with a non-existent ID"""
    manufacturer_id = str(ObjectId())

    test_helpers.mock_delete_one(database_mock.manufacturers, 0)
    # Mock `find_one` to return no child catalogue item document
    test_helpers.mock_find_one(database_mock.catalogue_items, None)

    with pytest.raises(MissingRecordError) as exc:
        manufacturer_repository.delete(manufacturer_id)
    assert str(exc.value) == f"No manufacturer found with ID: {manufacturer_id}"
    database_mock.manufacturers.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(manufacturer_id)}, session=None
    )


def test_delete_manufacturer_that_is_part_of_a_catalogue_item(test_helpers, database_mock, manufacturer_repository):
    """Test trying to delete a manufacturer that is part of a Catalogue Item"""
    manufacturer_id = str(ObjectId())

    catalogue_category_id = str(ObjectId())

    # pylint: disable=duplicate-code
    # Mock `find_one` to return the child catalogue item document
    test_helpers.mock_find_one(
        database_mock.catalogue_items,
        {
            **FULL_CATALOGUE_ITEM_A_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_category_id": CustomObjectId(catalogue_category_id),
        },
    )
    # pylint: enable=duplicate-code
    with pytest.raises(PartOfCatalogueItemError) as exc:
        manufacturer_repository.delete(manufacturer_id)
    assert str(exc.value) == f"The manufacturer with id {str(manufacturer_id)} is a part of a Catalogue Item"
