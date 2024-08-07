"""
Unit tests for the `UsageStatusRepo` repository
"""

from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from test.unit.repositories.test_item import FULL_ITEM_INFO
from unittest.mock import MagicMock, call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateRecordError,
    InvalidObjectIdError,
    MissingRecordError,
    PartOfItemError,
)
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut


def test_create(test_helpers, database_mock, usage_status_repository):
    """
    Test creating a usage status.

    Verify that the `create` method properly handles the usage status to be created,
    checks that there is not a duplicate usage status, and creates the usage status.
    """
    # pylint: disable=duplicate-code
    usage_status_in = UsageStatusIn(value="New", code="new")
    usage_status_info = usage_status_in.model_dump()
    usage_status_out = UsageStatusOut(
        **usage_status_info,
        id=str(ObjectId()),
    )
    session = MagicMock()
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate usage statuses found
    test_helpers.mock_find_one(database_mock.usage_statuses, None)
    # Mock 'insert one' to return object for inserted usage status
    test_helpers.mock_insert_one(database_mock.usage_statuses, CustomObjectId(usage_status_out.id))
    # Mock 'find_one' to return the inserted usage status document
    test_helpers.mock_find_one(
        database_mock.usage_statuses,
        {
            **usage_status_info,
            "_id": CustomObjectId(usage_status_out.id),
        },
    )

    created_usage_status = usage_status_repository.create(usage_status_in, session=session)

    database_mock.usage_statuses.insert_one.assert_called_once_with(usage_status_info, session=session)
    database_mock.usage_statuses.find_one.assert_has_calls(
        [
            call(
                {
                    "code": usage_status_out.code,
                    "_id": {"$ne": None},
                },
                session=session,
            ),
            call({"_id": CustomObjectId(usage_status_out.id)}, session=session),
        ]
    )
    assert created_usage_status == usage_status_out


def test_create_usage_status_duplicate(test_helpers, database_mock, usage_status_repository):
    """
    Test creating a usage status with a duplicate code

    Verify that the `create` method properly handles a usage status with a duplicate name,
    finds that there is a duplicate usage status, and does not create the usage.
    """
    usage_status_in = UsageStatusIn(value="New", code="new")
    usage_status_info = usage_status_in.model_dump()
    usage_status_out = UsageStatusOut(
        **usage_status_info,
        id=str(ObjectId()),
    )

    # Mock `find_one` to return duplicate usage statuses found
    test_helpers.mock_find_one(
        database_mock.usage_statuses,
        {
            **usage_status_info,
            "_id": CustomObjectId(usage_status_out.id),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        usage_status_repository.create(usage_status_out)
    assert str(exc.value) == "Duplicate usage status found"


def test_list(test_helpers, database_mock, usage_status_repository):
    """Test getting all usage statuses"""
    usage_status_1 = UsageStatusOut(**MOCK_CREATED_MODIFIED_TIME, id=str(ObjectId()), value="New", code="new")

    usage_status_2 = UsageStatusOut(**MOCK_CREATED_MODIFIED_TIME, id=str(ObjectId()), value="Used", code="used")

    session = MagicMock()
    test_helpers.mock_find(
        database_mock.usage_statuses,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(usage_status_1.id),
                "code": usage_status_1.code,
                "value": usage_status_1.value,
            },
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(usage_status_2.id),
                "code": usage_status_2.code,
                "value": usage_status_2.value,
            },
        ],
    )

    retrieved_usage_statuses = usage_status_repository.list(session=session)

    database_mock.usage_statuses.find.assert_called_once()
    assert retrieved_usage_statuses == [
        usage_status_1,
        usage_status_2,
    ]


def test_list_when_no_usage_statuses(test_helpers, database_mock, usage_status_repository):
    """Test trying to get all usage statuses when there are none in the database"""
    test_helpers.mock_find(database_mock.usage_statuses, [])
    retrieved_usage_statuses = usage_status_repository.list()

    assert retrieved_usage_statuses == []


def test_get(test_helpers, database_mock, usage_status_repository):
    """
    Test getting a usage status by id
    """
    usage_status = UsageStatusOut(**MOCK_CREATED_MODIFIED_TIME, id=str(ObjectId()), value="New", code="new")
    session = MagicMock()
    test_helpers.mock_find_one(
        database_mock.usage_statuses,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(usage_status.id),
            "code": usage_status.code,
            "value": usage_status.value,
        },
    )
    retrieved_usage_status = usage_status_repository.get(usage_status.id, session=session)
    database_mock.usage_statuses.find_one.assert_called_once_with(
        {"_id": CustomObjectId(usage_status.id)}, session=session
    )
    assert retrieved_usage_status == usage_status


def test_get_with_invalid_id(usage_status_repository):
    """
    Test getting a usage status with an Invalid ID
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        usage_status_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_non_existent_id(test_helpers, database_mock, usage_status_repository):
    """
    Test getting a usage status with an ID that does not exist
    """
    usage_status_id = str(ObjectId())
    session = MagicMock()
    test_helpers.mock_find_one(database_mock.usage_statuses, None)
    retrieved_usage_status = usage_status_repository.get(usage_status_id, session=session)

    assert retrieved_usage_status is None
    database_mock.usage_statuses.find_one.assert_called_once_with(
        {"_id": CustomObjectId(usage_status_id)}, session=session
    )


def test_delete(test_helpers, database_mock, usage_status_repository):
    """Test trying to delete a usage status"""
    usage_status_id = str(ObjectId())
    session = MagicMock()

    test_helpers.mock_delete_one(database_mock.usage_statuses, 1)

    # Mock `find_one` to return no child catalogue item document
    test_helpers.mock_find_one(database_mock.items, None)

    usage_status_repository.delete(usage_status_id, session=session)

    database_mock.usage_statuses.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(usage_status_id)}, session=session
    )


def test_delete_with_an_invalid_id(usage_status_repository):
    """Test trying to delete a usage status with an invalid ID"""
    usage_status_id = "invalid"
    session = MagicMock()

    with pytest.raises(InvalidObjectIdError) as exc:
        usage_status_repository.delete(usage_status_id, session=session)
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_delete_with_a_non_existent_id(test_helpers, database_mock, usage_status_repository):
    """Test trying to delete a usage status with a non-existent ID"""
    usage_status_id = str(ObjectId())

    test_helpers.mock_delete_one(database_mock.usage_statuses, 0)
    # Mock `find_one` to return no child catalogue item document
    test_helpers.mock_find_one(database_mock.items, None)

    with pytest.raises(MissingRecordError) as exc:
        usage_status_repository.delete(usage_status_id)
    assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"
    database_mock.usage_statuses.delete_one.assert_called_once_with(
        {"_id": CustomObjectId(usage_status_id)}, session=None
    )


def test_delete_usage_status_that_is_part_of_a_catalogue_item(test_helpers, database_mock, usage_status_repository):
    """Test trying to delete a usage status that is part of a Catalogue Item"""
    usage_status_id = str(ObjectId())

    catalogue_category_id = str(ObjectId())

    # pylint: disable=duplicate-code
    # Mock `find_one` to return the child catalogue item document
    test_helpers.mock_find_one(
        database_mock.items,
        {
            **FULL_ITEM_INFO,
            "_id": CustomObjectId(str(ObjectId())),
            "catalogue_category_id": CustomObjectId(catalogue_category_id),
            "usage_status_id": CustomObjectId(usage_status_id),
            "usage_status": "New",
            "system_id": CustomObjectId(str(ObjectId())),
        },
    )
    # pylint: enable=duplicate-code
    with pytest.raises(PartOfItemError) as exc:
        usage_status_repository.delete(usage_status_id)
    assert str(exc.value) == f"The usage status with ID {str(usage_status_id)} is a part of an Item"
