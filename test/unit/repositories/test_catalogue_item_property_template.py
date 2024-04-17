"""
Unit tests for the `CatalogueItemPropertyTemplateRepo` repository
"""

from test.unit.repositories.mock_models import MOCK_CREATED_MODIFIED_TIME
from unittest.mock import call

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import DuplicateRecordError, InvalidObjectIdError
from inventory_management_system_api.models.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateIn,
    CatalogueItemPropertyTemplateOut,
)


def test_create(test_helpers, database_mock, catalogue_item_property_template_repository):
    """
    Test creating a catalogue item property template.

    Verify that the `create` method properly handles the catalogue item property template to be created,
    checks that there is not a duplicate catalogue item property template, and creates the catalogue
    item property template.
    """
    # pylint: disable=duplicate-code
    catalogue_item_property_template_in = CatalogueItemPropertyTemplateIn(
        name="Diameter", code="diameter", type="number", unit="mm", mandatory=True
    )
    catalogue_item_property_template_info = catalogue_item_property_template_in.model_dump()
    catalogue_item_property_template_out = CatalogueItemPropertyTemplateOut(
        **catalogue_item_property_template_info,
        id=str(ObjectId()),
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate catalogue item property templates found
    test_helpers.mock_find_one(database_mock.catalogue_item_property_templates, None)
    # Mock 'insert one' to return object for inserted catalogue item property template
    test_helpers.mock_insert_one(
        database_mock.catalogue_item_property_templates, CustomObjectId(catalogue_item_property_template_out.id)
    )
    # Mock 'find_one' to return the inserted catalogue item property template document
    test_helpers.mock_find_one(
        database_mock.catalogue_item_property_templates,
        {
            **catalogue_item_property_template_info,
            "_id": CustomObjectId(catalogue_item_property_template_out.id),
        },
    )

    created_catalogue_item_property_template = catalogue_item_property_template_repository.create(
        catalogue_item_property_template_in
    )

    database_mock.catalogue_item_property_templates.insert_one.assert_called_once_with(
        catalogue_item_property_template_in.model_dump()
    )
    database_mock.catalogue_item_property_templates.find_one.assert_has_calls(
        [
            call({"code": catalogue_item_property_template_out.code}),
            call({"_id": CustomObjectId(catalogue_item_property_template_out.id)}),
        ]
    )
    assert created_catalogue_item_property_template == catalogue_item_property_template_out


def test_create_with_allowed_values(test_helpers, database_mock, catalogue_item_property_template_repository):
    """
    Test creating a catalogue item property template with allowed values.

    Verify that the `create` method properly handles the catalogue item property template to be created,
    checks that there is not a duplicate catalogue item property template, and creates the catalogue
    item property template.
    """
    # pylint: disable=duplicate-code
    catalogue_item_property_template_in = CatalogueItemPropertyTemplateIn(
        name="Material",
        code="material",
        type="string",
        unit=None,
        mandatory=False,
        allowed_values={"type": "list", "values": ["Fused Silica", "(N)BK-7", "KzFS", "SF6"]},
    )
    catalogue_item_property_template_info = catalogue_item_property_template_in.model_dump()
    catalogue_item_property_template_out = CatalogueItemPropertyTemplateOut(
        **catalogue_item_property_template_info,
        id=str(ObjectId()),
    )
    # pylint: enable=duplicate-code

    # Mock `find_one` to return no duplicate catalogue item property templates found
    test_helpers.mock_find_one(database_mock.catalogue_item_property_templates, None)
    # Mock 'insert one' to return object for inserted catalogue item property template
    test_helpers.mock_insert_one(
        database_mock.catalogue_item_property_templates, CustomObjectId(catalogue_item_property_template_out.id)
    )
    # Mock 'find_one' to return the inserted catalogue item property template document
    test_helpers.mock_find_one(
        database_mock.catalogue_item_property_templates,
        {
            **catalogue_item_property_template_info,
            "_id": CustomObjectId(catalogue_item_property_template_out.id),
        },
    )

    created_catalogue_item_property_template = catalogue_item_property_template_repository.create(
        catalogue_item_property_template_in
    )

    database_mock.catalogue_item_property_templates.insert_one.assert_called_once_with(
        catalogue_item_property_template_in.model_dump()
    )
    database_mock.catalogue_item_property_templates.find_one.assert_has_calls(
        [
            call({"code": catalogue_item_property_template_out.code}),
            call({"_id": CustomObjectId(catalogue_item_property_template_out.id)}),
        ]
    )
    assert created_catalogue_item_property_template == catalogue_item_property_template_out


def test_create_catalogue_item_property_template_duplicate(
    test_helpers, database_mock, catalogue_item_property_template_repository
):
    """
    Test creating a catalogue item property template with a duplicate code

    Verify that the `create` method properly handles a catalogue item property template with a duplicate name,
    finds that there is a duplicate catalogue item property template, and does not create the catalogue item
    property template.
    """
    catalogue_item_property_template_in = CatalogueItemPropertyTemplateIn(
        name="Diameter", code="diameter", type="number", unit="mm", mandatory=True
    )
    catalogue_item_property_template_info = catalogue_item_property_template_in.model_dump()
    catalogue_item_property_template_out = CatalogueItemPropertyTemplateOut(
        **catalogue_item_property_template_info,
        id=str(ObjectId()),
    )

    # Mock `find_one` to return duplicate manufacturer found
    # Mock `find_one` to return no duplicate catalogue item property templates found
    test_helpers.mock_find_one(
        database_mock.catalogue_item_property_templates,
        {
            **catalogue_item_property_template_info,
            "_id": CustomObjectId(catalogue_item_property_template_out.id),
        },
    )

    with pytest.raises(DuplicateRecordError) as exc:
        catalogue_item_property_template_repository.create(catalogue_item_property_template_out)
    assert str(exc.value) == "Duplicate catalogue item property template found"


def test_list(test_helpers, database_mock, catalogue_item_property_template_repository):
    """Test getting all catalogue item property templates"""
    catalogue_item_property_template_1 = CatalogueItemPropertyTemplateOut(
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        name="Diameter",
        code="diameter",
        type="number",
        unit="mm",
        mandatory=True,
    )

    catalogue_item_property_template_2 = CatalogueItemPropertyTemplateOut(
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        name="Material",
        code="material",
        type="string",
        unit=None,
        mandatory=False,
        allowed_values={"type": "list", "values": ["Fused Silica", "(N)BK-7", "KzFS", "SF6"]},
    )

    test_helpers.mock_find(
        database_mock.catalogue_item_property_templates,
        [
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_item_property_template_1.id),
                "code": catalogue_item_property_template_1.code,
                "name": catalogue_item_property_template_1.name,
                "unit": catalogue_item_property_template_1.unit,
                "type": catalogue_item_property_template_1.type,
                "mandatory": catalogue_item_property_template_1.mandatory,
                "allowed_values": catalogue_item_property_template_1.allowed_values,
            },
            {
                **MOCK_CREATED_MODIFIED_TIME,
                "_id": CustomObjectId(catalogue_item_property_template_2.id),
                "code": catalogue_item_property_template_2.code,
                "name": catalogue_item_property_template_2.name,
                "unit": catalogue_item_property_template_2.unit,
                "type": catalogue_item_property_template_2.type,
                "mandatory": catalogue_item_property_template_2.mandatory,
                "allowed_values": catalogue_item_property_template_2.allowed_values,
            },
        ],
    )

    retrieved_catalogue_item_property_templates = catalogue_item_property_template_repository.list()

    database_mock.catalogue_item_property_templates.find.assert_called_once()
    assert retrieved_catalogue_item_property_templates == [
        catalogue_item_property_template_1,
        catalogue_item_property_template_2,
    ]


def test_list_when_no_catalogue_item_property_templates(
    test_helpers, database_mock, catalogue_item_property_template_repository
):
    """Test trying to get all catalogue item property templates when there are none in the database"""
    test_helpers.mock_find(database_mock.catalogue_item_property_templates, [])
    retrieved_catalogue_item_property_templates = catalogue_item_property_template_repository.list()

    assert retrieved_catalogue_item_property_templates == []


def test_get(test_helpers, database_mock, catalogue_item_property_template_repository):
    """
    Test getting a catalogue item property template by id
    """
    catalogue_item_property_template = CatalogueItemPropertyTemplateOut(
        **MOCK_CREATED_MODIFIED_TIME,
        id=str(ObjectId()),
        name="Diameter",
        code="diameter",
        type="number",
        unit="mm",
        mandatory=True,
    )

    test_helpers.mock_find_one(
        database_mock.catalogue_item_property_templates,
        {
            **MOCK_CREATED_MODIFIED_TIME,
            "_id": CustomObjectId(catalogue_item_property_template.id),
            "code": catalogue_item_property_template.code,
            "name": catalogue_item_property_template.name,
            "unit": catalogue_item_property_template.unit,
            "type": catalogue_item_property_template.type,
            "mandatory": catalogue_item_property_template.mandatory,
            "allowed_values": catalogue_item_property_template.allowed_values,
        },
    )
    retrieved_catalogue_item_property_template = catalogue_item_property_template_repository.get(
        catalogue_item_property_template.id
    )
    database_mock.catalogue_item_property_templates.find_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_item_property_template.id)}
    )
    assert retrieved_catalogue_item_property_template == catalogue_item_property_template


def test_get_with_invalid_id(catalogue_item_property_template_repository):
    """
    Test getting a catalogue item property template with an Invalid ID
    """
    with pytest.raises(InvalidObjectIdError) as exc:
        catalogue_item_property_template_repository.get("invalid")
    assert str(exc.value) == "Invalid ObjectId value 'invalid'"


def test_get_with_nonexistent_id(test_helpers, database_mock, catalogue_item_property_template_repository):
    """
    Test getting a catalogue item property template with an ID that does not exist
    """
    catalogue_item_property_template_id = str(ObjectId())
    test_helpers.mock_find_one(database_mock.catalogue_item_property_templates, None)
    retrieved_catalogue_item_property_template = catalogue_item_property_template_repository.get(
        catalogue_item_property_template_id
    )

    assert retrieved_catalogue_item_property_template is None
    database_mock.catalogue_item_property_templates.find_one.assert_called_once_with(
        {"_id": CustomObjectId(catalogue_item_property_template_id)}
    )
