"""
Unit tests for the `UnitRepo` repository
"""

from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from unittest.mock import MagicMock, call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfCatalogueCategoryError,
)
from inventory_management_system_api.models.unit import UnitIn, UnitOut

# pylint: disable=duplicate-code
CATALOGUE_CATEGORY_INFO = {
    "name": "Category A",
    "code": "category-a",
    "is_leaf": False,
    "parent_id": None,
    "properties": [],
}
# pylint: enable=duplicate-code


def test_create(test_helpers, database_mock, unit_repository):
    """
    Test creating a unit.

    Verify that the `create` method properly handles the unit to be created,
    checks that there is not a duplicate unit, and creates the unit.
    """
    # pylint: disable=duplicate-code
    unit_in = UnitIn(value="mm", code="mm")
    unit_info = unit_in.model_dump()
    unit_out = UnitOut(
        **unit_info,
        id=str(ObjectId()),
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate units found
    test_helpers.mock_find_one(database_mock.units, None)
    # Mock 'insert one' to return object for inserted unit
    test_helpers.mock_insert_one(database_mock.units, CustomObjectId(unit_out.id))
    # Mock 'find_one' to return the inserted unit document
    test_helpers.mock_find_one(
        database_mock.units,
        {
            **unit_info,
            "_id": CustomObjectId(unit_out.id),
        },
    )

    created_unit = unit_repository.create(unit_in, session=session)

    database_mock.units.insert_one.assert_called_once_with(unit_info, session=session)
    database_mock.units.find_one.assert_has_calls(
        [
            call(
                {
                    "code": unit_out.code,
                    "_id": {"$ne": None},
                },
                session=session,
            ),
            call({"_id": CustomObjectId(unit_out.id)}, session=session),
        ]
    )
    assert created_unit == unit_out


def test_create_unit_duplicate(test_helpers, database_mock, unit_repository):
    """
    Test creating a unit with a duplicate code

    Verify that the `create` method properly handles a unit with a duplicate name,
    finds that there is a duplicate unit, and does not create the unit.
    """
    unit_in = UnitIn(value="mm", code="mm")
    unit_info = unit_in.model_dump()
    unit_out = UnitOut(
        **unit_info,
        id=str(ObjectId()),
    )

    # Mock `find_one` to return no duplicate units found
    test_helpers.mock_find_one(
        database_mock.units,
        {
            **unit_info,
            "_id": CustomObjectId(unit_out.id),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        unit_repository.create(unit_out)
    assert str(exc.value) == "Duplicate unit found"


def test_list(test_helpers, database_mock, unit_repository):
    """Test getting all units"""

    unit_1 = UnitOut(**MOCK_CREATED_MODIFIED_TIME, id=str(ObjectId()), value="mm", code="mm")

    unit_2 = UnitOut(**MOCK_CREATED_MODIFIED_TIME, id=str(ObjectId()), value="nm", code="nm")

    session = MagicMock()

    test_helpers.mock_find(
        database_mock.units,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(unit_1.id),
                "code": unit_1.code,
                "value": unit_1.value,
            },
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(unit_2.id),
                "code": unit_2.code,
                "value": unit_2.value,
            },
        ],
    )

    retrieved_units = unit_repository.list(session=session)

    database_mock.units.find.assert_called_once()
    assert retrieved_units == [
        unit_1,
        unit_2,
    ]


def test_list_when_no_units(test_helpers, database_mock, unit_repository):
    """Test trying to get all units when there are none in the database"""

    test_helpers.mock_find(database_mock.units, [])
    retrieved_units = unit_repository.list()

    assert retrieved_units == []


def test_get(test_helpers, database_mock, unit_repository):
    """
    Test getting a unit by id
    """

    unit = UnitOut(**MOCK_CREATED_MODIFIED_TIME, id=str(ObjectId()), value="mm", code="mm")

    session = MagicMock()

    test_helpers.mock_find_one(
        database_mock.units,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(unit.id),
            "code": unit.code,
            "value": unit.value,
        },
    )
    retrieved_unit = unit_repository.get(unit.id, session=session)
    database_mock.units.find_one.assert_called_once_with({"_id": CustomObjectId(unit.id)}, session=session)
    assert retrieved_unit == unit


def test_get_with_invalid_id(unit_repository):
    """
    Test getting a unit with an Invalid ID
    """

    with pytest.raises(InvalidObjectIdError) as exc:
        unit_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_non_existent_id(test_helpers, database_mock, unit_repository):
    """
    Test getting a unit with an ID that does not exist
    """

    unit_id = str(ObjectId())
    test_helpers.mock_find_one(database_mock.units, None)
    retrieved_unit = unit_repository.get(unit_id)

    assert retrieved_unit is None
    database_mock.units.find_one.assert_called_once_with({"_id": CustomObjectId(unit_id)}, session=None)


def test_delete(test_helpers, database_mock, unit_repository):
    """Test trying to delete a unit"""
    unit_id = str(ObjectId())
    session = MagicMock()

    test_helpers.mock_delete_one(database_mock.units, 1)

    # Mock `find_one` to return no catalogue categories containing the unit
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    unit_repository.delete(unit_id, session=session)

    database_mock.units.delete_one.assert_called_once_with({"_id": CustomObjectId(unit_id)}, session=session)


def test_delete_with_an_invalid_id(unit_repository):
    """Test trying to delete a unit with an invalid ID"""
    unit_id = "invalid"

    with pytest.raises(InvalidObjectIdError) as exc:
        unit_repository.delete(unit_id)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_a_non_existent_id(test_helpers, database_mock, unit_repository):
    """Test trying to delete a manufacturer with a non-existent ID"""
    unit_id = str(ObjectId())

    test_helpers.mock_delete_one(database_mock.units, 0)

    # Mock `find_one` to return no catalogue categories containing the unit
    test_helpers.mock_find_one(database_mock.catalogue_categories, None)

    with pytest.raises(MissingRecordError) as exc:
        unit_repository.delete(unit_id)
    assert str(exc.value) == f"No unit found with ID: {unit_id}"
    database_mock.units.delete_one.assert_called_once_with({"_id": CustomObjectId(unit_id)}, session=None)


def test_delete_unit_that_is_part_of_a_catalogue_category(test_helpers, database_mock, unit_repository):
    """Test trying to delete a unit that is part of a Catalogue category"""
    unit_id = str(ObjectId())

    catalogue_category_id = str(ObjectId())

    # pylint: disable=duplicate-code
    # Mock find_one to return a catalogue category containing the unit
    test_helpers.mock_find_one(
        database_mock.catalogue_categories,
        {
            **CATALOGUE_CATEGORY_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "parent_id": catalogue_category_id,
            "properties": [
                {
                    "name": "Property A",
                    "type": "number",
                    "unit": "mm",
                    "unit_id": unit_id,
                    "mandatory": False,
                }
            ],
        },
    )
    # pylint: enable=duplicate-code
    with pytest.raises(PartOfCatalogueCategoryError) as exc:
        unit_repository.delete(unit_id)
    assert str(exc.value) == f"The unit with ID {str(unit_id)} is a part of a Catalogue category"
