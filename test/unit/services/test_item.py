# pylint: disable=too-many-lines
"""
Unit tests for the `ItemService` service.
"""

from datetime import datetime, timedelta, timezone
from test.conftest import add_ids_to_properties
from test.unit.services.conftest import MODEL_MIXINS_FIXED_DATETIME_NOW
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    InvalidActionError,
    InvalidPropertyTypeError,
    InvalidObjectIdError,
    MissingRecordError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut
from inventory_management_system_api.models.item import ItemIn, ItemOut
from inventory_management_system_api.models.system import SystemOut
from inventory_management_system_api.models.usage_status import UsageStatusOut
from inventory_management_system_api.schemas.item import ItemPatchSchema, ItemPostSchema

# pylint: disable=duplicate-code
FULL_CATALOGUE_CATEGORY_A_INFO = {
    "name": "Category A",
    "code": "category-a",
    "is_leaf": True,
    "parent_id": None,
    "properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
        {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
        {"name": "Property D", "type": "string", "unit": None, "mandatory": False},
    ],
    "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
}

FULL_CATALOGUE_ITEM_A_INFO = {
    "name": "Catalogue Item A",
    "description": "This is Catalogue Item A",
    "cost_gbp": 129.99,
    "cost_to_rework_gbp": None,
    "days_to_replace": 2.0,
    "days_to_rework": None,
    "drawing_link": "https://drawing-link.com/",
    "drawing_number": None,
    "item_model_number": "abc123",
    "is_obsolete": False,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "notes": None,
    "properties": [
        {"name": "Property A", "value": 20, "unit": "mm"},
        {"name": "Property B", "value": False, "unit": None},
        {"name": "Property C", "value": "20x15x10", "unit": "cm"},
    ],
    "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
}

ITEM_INFO = {
    "is_defective": False,
    "warranty_end_date": datetime(2015, 11, 15, 23, 59, 59, 0, tzinfo=timezone.utc),
    "serial_number": "xyz123",
    "delivered_date": datetime(2012, 12, 5, 12, 0, 0, 0, tzinfo=timezone.utc),
    "notes": "Test notes",
    "properties": [{"name": "Property A", "value": 21}],
}

FULL_ITEM_INFO = {
    **ITEM_INFO,
    "purchase_order_number": None,
    "asset_number": None,
    "properties": [
        {"name": "Property A", "value": 21, "unit": "mm"},
        {"name": "Property B", "value": False, "unit": None},
        {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        {"name": "Property D", "value": None, "unit": None},
    ],
    "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
}

FULL_SYSTEM_INFO = {
    "name": "Test name a",
    "code": "test-name-a",
    "location": "Test location",
    "owner": "Test owner",
    "importance": "low",
    "description": "Test description",
    "parent_id": None,
    "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
}
USAGE_STATUS_A = {
    "value": "New",
    "code": "new",
    "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
}
USAGE_STATUS_B = {
    "value": "Used",
    "code": "used",
    "created_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
    "modified_time": MODEL_MIXINS_FIXED_DATETIME_NOW,
}


# pylint: enable=duplicate-code


def test_create(
    test_helpers,
    item_repository_mock,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    usage_status_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    item_service,
):  # pylint: disable=too-many-arguments
    """
    Test creating an item.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{**FULL_ITEM_INFO, "properties": item_properties},
    )
    # pylint: enable=duplicate-code

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": add_ids_to_properties(
                    item_properties,
                    FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
                ),
            },
        ),
    )
    # pylint: enable=duplicate-code
    # Mock `create` to return the created item
    test_helpers.mock_create(item_repository_mock, item)
    # Mock `get` to return the usage status
    test_helpers.mock_get(
        usage_status_repository_mock,
        UsageStatusOut(id=item.usage_status_id, **USAGE_STATUS_A),
    )

    created_item = item_service.create(
        ItemPostSchema(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status_id=item.usage_status_id,
            **{
                **ITEM_INFO,
                "properties": [{"id": prop["id"], "value": prop["value"]} for prop in item_properties],
            },
        )
    )

    catalogue_item_repository_mock.get.assert_called_once_with(item.catalogue_item_id)
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)
    item_repository_mock.create.assert_called_once_with(
        ItemIn(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status_id=item.usage_status_id,
            usage_status=item.usage_status,
            **{
                **FULL_ITEM_INFO,
                "properties": item_properties,
            },
        )
    )
    assert created_item == item


def test_create_with_non_existent_catalogue_item_id(
    test_helpers, item_repository_mock, catalogue_item_repository_mock, item_service
):
    """
    Test creating an item with a non-existent catalogue item ID.
    """
    catalogue_item_id = str(ObjectId())

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(catalogue_item_repository_mock, None)

    with pytest.raises(MissingRecordError) as exc:
        item_service.create(
            ItemPostSchema(
                catalogue_item_id=catalogue_item_id,
                usage_status_id=str(ObjectId()),
                system_id=str(ObjectId()),
                **{
                    **ITEM_INFO,
                    "properties": add_ids_to_properties(None, ITEM_INFO["properties"]),
                },
            )
        )
    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)
    item_repository_mock.create.assert_not_called()
    assert str(exc.value) == f"No catalogue item found with ID: {catalogue_item_id}"


def test_create_with_non_existent_usage_status_id(
    test_helpers, item_repository_mock, usage_status_repository_mock, item_service
):
    """
    Test creating an item with a non-existent usage status ID.
    """
    usage_status_id = str(ObjectId())

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(usage_status_repository_mock, None)

    with pytest.raises(MissingRecordError) as exc:
        item_service.create(
            ItemPostSchema(
                catalogue_item_id=str(ObjectId()),
                usage_status_id=usage_status_id,
                system_id=str(ObjectId()),
                **{
                    **ITEM_INFO,
                    "properties": add_ids_to_properties(None, ITEM_INFO["properties"]),
                },
            )
        )
    usage_status_repository_mock.get.assert_called_once_with(usage_status_id)
    item_repository_mock.create.assert_not_called()
    assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"


def test_create_with_invalid_usage_status_id(
    test_helpers, item_repository_mock, usage_status_repository_mock, item_service
):
    """
    Test creating an item with a invalid usage status ID.
    """
    usage_status_id = "invalid"

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(usage_status_repository_mock, None)

    with pytest.raises(MissingRecordError) as exc:
        item_service.create(
            ItemPostSchema(
                catalogue_item_id=str(ObjectId()),
                usage_status_id=usage_status_id,
                system_id=str(ObjectId()),
                **{
                    **ITEM_INFO,
                    "properties": add_ids_to_properties(None, ITEM_INFO["properties"]),
                },
            )
        )
    usage_status_repository_mock.get.assert_called_once_with(usage_status_id)
    item_repository_mock.create.assert_not_called()
    assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"


def test_create_with_invalid_catalogue_category_id(
    test_helpers,
    item_repository_mock,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_service,
):
    """
    Test creating an item with an invalid catalogue category ID.
    """
    catalogue_item_id = str(ObjectId())
    catalogue_category_id = "invalid"
    manufacturer_id = str(ObjectId())

    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        InvalidObjectIdError(f"Invalid ObjectId value '{catalogue_category_id}'"),
    )

    with pytest.raises(DatabaseIntegrityError) as exc:
        item_service.create(
            ItemPostSchema(
                catalogue_item_id=catalogue_item_id,
                system_id=str(ObjectId()),
                usage_status_id=str(ObjectId()),
                **{
                    **ITEM_INFO,
                    "properties": [{"id": prop["id"], "value": prop["value"]} for prop in item_properties],
                },
            )
        )
    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)
    item_repository_mock.create.assert_not_called()
    assert str(exc.value) == f"Invalid ObjectId value '{catalogue_category_id}'"


def test_create_with_non_existent_catalogue_category_id_in_catalogue_item(
    test_helpers,
    item_repository_mock,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_service,
):
    """
    Test creating an item with a non-existent catalogue category ID in a catalogue item.
    """
    catalogue_item_id = str(ObjectId())
    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to not return a catalogue category
    test_helpers.mock_get(catalogue_category_repository_mock, None)

    with pytest.raises(DatabaseIntegrityError) as exc:
        item_service.create(
            ItemPostSchema(
                catalogue_item_id=catalogue_item_id,
                system_id=str(ObjectId()),
                usage_status_id=str(ObjectId()),
                **{
                    **ITEM_INFO,
                    "properties": [{"id": prop["id"], "value": prop["value"]} for prop in item_properties],
                },
            )
        )
    catalogue_item_repository_mock.get.assert_called_once_with(catalogue_item_id)
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)
    item_repository_mock.create.assert_not_called()
    assert str(exc.value) == f"No catalogue category found with ID: {catalogue_category_id}"


def test_create_without_properties(
    test_helpers,
    item_repository_mock,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    usage_status_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    item_service,
):  # pylint: disable=too-many-arguments
    """
    Testing creating an item without properties.
    """
    # pylint: disable=duplicate-code
    catalogue_category_properties = add_ids_to_properties(None, FULL_CATALOGUE_CATEGORY_A_INFO["properties"])

    properties = add_ids_to_properties(catalogue_category_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{**FULL_ITEM_INFO, "properties": properties},
    )
    # pylint: enable=duplicate-code

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())
    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": properties,
            },
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": catalogue_category_properties,
            },
        ),
    )
    # Mock `create` to return the created item
    test_helpers.mock_create(item_repository_mock, item)
    # Mock `get` to return the usage status
    test_helpers.mock_get(
        usage_status_repository_mock,
        UsageStatusOut(id=item.usage_status_id, **USAGE_STATUS_A),
    )

    item_post = {
        **ITEM_INFO,
        "catalogue_item_id": item.catalogue_item_id,
        "system_id": item.system_id,
        "usage_status_id": item.usage_status_id,
    }
    del item_post["properties"]
    created_item = item_service.create(ItemPostSchema(**item_post))

    catalogue_item_repository_mock.get.assert_called_once_with(item.catalogue_item_id)
    catalogue_category_repository_mock.get.assert_called_once_with(catalogue_category_id)
    item_repository_mock.create.assert_called_once_with(
        ItemIn(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status_id=item.usage_status_id,
            usage_status=item.usage_status,
            **{
                **FULL_ITEM_INFO,
                "properties": [
                    *properties,
                    *add_ids_to_properties(
                        catalogue_category_properties,
                        [FULL_ITEM_INFO["properties"][-1]],
                    ),
                ],
            },
        )
    )
    assert created_item == item


def test_delete(item_repository_mock, item_service):
    """
    Test deleting item.

    Verify that the `delete` method properly handles the deletion of item by ID.
    """
    item_id = str(ObjectId())

    item_service.delete(item_id)

    item_repository_mock.delete.assert_called_once_with(item_id)


def test_get(test_helpers, item_repository_mock, item_service):
    """
    Test getting an item.

    Verify that the `get` method properly handles the retrieval of the item by ID.
    """
    item_id = str(ObjectId())
    item = MagicMock()

    # Mock `get` to return an item
    test_helpers.mock_get(item_repository_mock, item)

    retrieved_item = item_service.get(item_id)

    item_repository_mock.get.assert_called_once_with(item_id)
    assert retrieved_item == item


def test_get_with_non_existent_id(test_helpers, item_repository_mock, item_service):
    """
    Test getting an item with a non-existent ID.

    Verify the `get` method properly handles the retrieval of an item with a non-existent ID.
    """
    item_id = str(ObjectId())

    # Mock get to not return an item
    test_helpers.mock_get(item_repository_mock, None)

    retrieved_item = item_service.get(item_id)

    assert retrieved_item is None
    item_repository_mock.get.assert_called_once_with(item_id)


def test_list(item_repository_mock, item_service):
    """
    Test listing items.

    Verify that the `list` method properly calls the repository function
    """
    result = item_service.list(None, None)

    item_repository_mock.list.assert_called_once_with(None, None)
    assert result == item_repository_mock.list.return_value


def test_update(
    test_helpers,
    item_repository_mock,
    usage_status_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    item_service,
):
    """
    Test updating an item,

    Verify that the `update` method properly handles the item to be updated.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="Used",
        **{
            **FULL_ITEM_INFO,
            "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "is_defective": True,
                "usage_status": item.usage_status,
                "usage_status_id": item.usage_status_id,
                "modified_time": item.created_time,
                "properties": item_properties,
            }
        ),
    )
    # Mock `update` to return the updated item
    test_helpers.mock_update(item_repository_mock, item)
    # Mock `get` to return the usage status
    test_helpers.mock_get(
        usage_status_repository_mock,
        UsageStatusOut(id=item.usage_status_id, **USAGE_STATUS_B),
    )
    updated_item = item_service.update(
        item.id,
        ItemPatchSchema(is_defective=item.is_defective, usage_status_id=item.usage_status_id),
    )

    item_repository_mock.update.assert_called_once_with(
        item.id,
        ItemIn(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status_id=item.usage_status_id,
            usage_status=item.usage_status,
            **{
                **FULL_ITEM_INFO,
                "created_time": item.created_time,
                "properties": item_properties,
            },
        ),
    )
    assert updated_item == item


def test_update_with_non_existent_id(test_helpers, item_repository_mock, item_service):
    """
    Test updating an item with a non-existent ID.

    Verify that the `update` method properly handles the item to be updated with a non-existent ID.
    """
    # Mock `get` to return an item
    test_helpers.mock_get(item_repository_mock, None)

    item_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        item_service.update(item_id, ItemPatchSchema(properties=[]))
    item_repository_mock.update.assert_not_called()
    assert str(exc.value) == f"No item found with ID: {item_id}"


def test_update_change_catalogue_item_id(test_helpers, item_repository_mock, item_service):
    """
    Test updating an item with a catalogue item ID.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "catalogue_item_id": str(ObjectId()),
                "properties": item_properties,
            }
        ),
    )

    catalogue_item_id = str(ObjectId())
    with pytest.raises(InvalidActionError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(catalogue_item_id=catalogue_item_id),
        )
    item_repository_mock.update.assert_not_called()
    assert str(exc.value) == "Cannot change the catalogue item the item belongs to"


def test_update_change_system_id(
    test_helpers,
    item_repository_mock,
    system_repository_mock,
    usage_status_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    item_service,
    # pylint: disable=too-many-arguments
):
    """
    Test updating system id to an existing id
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "system_id": str(ObjectId()),
                "modified_time": item.created_time,
                "properties": item_properties,
            }
        ),
    )

    # Mock `get` to return a system
    test_helpers.mock_get(
        system_repository_mock,
        SystemOut(
            id=item.system_id,
            **FULL_SYSTEM_INFO,
        ),
    )

    # Mock `get` to return the usage status
    test_helpers.mock_get(
        usage_status_repository_mock,
        UsageStatusOut(id=item.usage_status_id, **USAGE_STATUS_A),
    )

    # Mock `update` to return the updated item
    test_helpers.mock_update(item_repository_mock, item)

    updated_item = item_service.update(
        item.id,
        ItemPatchSchema(system_id=item.system_id),
    )

    item_repository_mock.update.assert_called_once_with(
        item.id,
        ItemIn(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status=item.usage_status,
            usage_status_id=item.usage_status_id,
            **{
                **FULL_ITEM_INFO,
                "created_time": item.created_time,
                "properties": item_properties,
            },
        ),
    )
    assert updated_item == item


def test_update_with_non_existent_system_id(test_helpers, system_repository_mock, item_repository_mock, item_service):
    """
    Test updating an item with a non-existent system ID.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "system_id": str(ObjectId()),
                "properties": item_properties,
            }
        ),
    )

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(system_repository_mock, None)

    system_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(system_id=system_id),
        )
    item_repository_mock.update.assert_not_called()
    assert str(exc.value) == f"No system found with ID: {system_id}"


def test_update_with_non_existent_usage_status(
    test_helpers, usage_status_repository_mock, item_repository_mock, item_service
):
    """
    Test updating an item with a non-existent usage status ID.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "usage_status_id": str(ObjectId()),
                "properties": item_properties,
            }
        ),
    )

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(usage_status_repository_mock, None)

    usage_status_id = str(ObjectId())
    with pytest.raises(MissingRecordError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(usage_status_id=usage_status_id),
        )
    item_repository_mock.update.assert_not_called()
    assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"


def test_update_with_invalid_usage_status(
    test_helpers, usage_status_repository_mock, item_repository_mock, item_service
):
    """
    Test updating an item with a invalid usage status ID.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "usage_status_id": str(ObjectId()),
                "properties": item_properties,
            }
        ),
    )

    # Mock `get` to not return a catalogue item
    test_helpers.mock_get(usage_status_repository_mock, None)

    usage_status_id = "invalid"
    with pytest.raises(MissingRecordError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(usage_status_id=usage_status_id),
        )
    item_repository_mock.update.assert_not_called()
    assert str(exc.value) == f"No usage status found with ID: {usage_status_id}"


def test_update_change_property_value(
    test_helpers,
    catalogue_item_repository_mock,
    catalogue_category_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    item_service,
):  # pylint: disable=too-many-arguments
    """
    Test updating a value of a property
    """
    item_properties = add_ids_to_properties(
        None,
        [
            {"name": "Property A", "value": 1, "unit": "mm"},
            *FULL_ITEM_INFO["properties"][-3:],
        ],
    )
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
            "properties": item_properties,
        },
    )

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "properties": item_properties,
                "modified_time": item.created_time,
            }
        ),
    )

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": add_ids_to_properties(
                    item_properties,
                    FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
                ),
            },
        ),
    )
    # pylint: enable=duplicate-code

    # Mock `update` to return the updated item
    test_helpers.mock_update(item_repository_mock, item)

    updated_item = item_service.update(
        item.id,
        ItemPatchSchema(properties=[{"id": prop.id, "value": prop.value} for prop in item.properties]),
    )

    item_repository_mock.update.assert_called_once_with(
        item.id,
        ItemIn(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status_id=item.usage_status_id,
            usage_status=item.usage_status,
            **{
                **FULL_ITEM_INFO,
                "created_time": item.created_time,
                "properties": item_properties,
            },
        ),
    )
    assert updated_item == item


def test_update_with_missing_existing_properties(
    test_helpers,
    catalogue_item_repository_mock,
    catalogue_category_repository_mock,
    item_repository_mock,
    model_mixins_datetime_now_mock,  # pylint: disable=unused-argument
    item_service,
):  # pylint: disable=too-many-arguments
    """
    Test updating properties with missing properties
    """
    item_properties = add_ids_to_properties(
        None,
        [
            FULL_CATALOGUE_ITEM_A_INFO["properties"][0],
            *FULL_ITEM_INFO["properties"][-3:],
        ],
    )
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "created_time": FULL_ITEM_INFO["created_time"] - timedelta(days=5),
            "properties": item_properties,
        },
    )

    # Mock `get` to return an item
    test_helpers.mock_get(
        item_repository_mock,
        ItemOut(
            **{
                **item.model_dump(),
                "properties": add_ids_to_properties(None, FULL_ITEM_INFO["properties"]),
                "modified_time": item.created_time,
            }
        ),
    )

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    # pylint: disable=duplicate-code
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": add_ids_to_properties(
                    item_properties,
                    FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
                ),
            },
        ),
    )
    # pylint: enable=duplicate-code

    # Mock `update` to return the updated item
    test_helpers.mock_update(item_repository_mock, item)

    updated_item = item_service.update(
        item.id,
        ItemPatchSchema(properties=[{"id": prop.id, "value": prop.value} for prop in item.properties[-2:]]),
    )

    item_repository_mock.update.assert_called_once_with(
        item.id,
        ItemIn(
            catalogue_item_id=item.catalogue_item_id,
            system_id=item.system_id,
            usage_status_id=item.usage_status_id,
            usage_status=item.usage_status,
            **{
                **FULL_ITEM_INFO,
                "created_time": item.created_time,
                "properties": item_properties,
            },
        ),
    )
    assert updated_item == item


def test_update_change_value_for_string_property_invalid_type(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    item_service,
):
    """
    Test changing the value of a string property to an invalid type.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(item_repository_mock, item)

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": add_ids_to_properties(
                    item_properties,
                    FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
                ),
            },
        ),
    )

    properties = [{"id": prop.id, "value": prop.value} for prop in item.properties]
    properties[2]["value"] = True
    with pytest.raises(InvalidPropertyTypeError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(properties=properties),
        )
    item_repository_mock.update.assert_not_called()
    assert (
        str(exc.value) == f"Invalid value type for property with ID '{item.properties[2].id}'. Expected type: string."
    )


def test_update_change_value_for_number_property_invalid_type(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    item_service,
):
    """
    Test changing the value of a number property to an invalid type.
    """
    # pylint: disable=duplicate-code
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )
    # pylint: enable=duplicate-code

    # Mock `get` to return an item
    test_helpers.mock_get(item_repository_mock, item)

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": add_ids_to_properties(
                    item_properties,
                    FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
                ),
            },
        ),
    )

    properties = [{"id": prop.id, "value": prop.value} for prop in item.properties]
    properties[0]["value"] = "20"
    with pytest.raises(InvalidPropertyTypeError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(properties=properties),
        )
    item_repository_mock.update.assert_not_called()
    assert (
        str(exc.value) == f"Invalid value type for property with ID '{item.properties[0].id}'. Expected type: number."
    )


def test_update_change_value_for_boolean_property_invalid_type(
    test_helpers,
    catalogue_category_repository_mock,
    catalogue_item_repository_mock,
    item_repository_mock,
    item_service,
):
    """
    Test changing the value of a boolean property to an invalid type.
    """
    item_properties = add_ids_to_properties(None, FULL_ITEM_INFO["properties"])
    item = ItemOut(
        id=str(ObjectId()),
        catalogue_item_id=str(ObjectId()),
        system_id=str(ObjectId()),
        usage_status_id=str(ObjectId()),
        usage_status="New",
        **{
            **FULL_ITEM_INFO,
            "properties": item_properties,
        },
    )

    # Mock `get` to return an item
    test_helpers.mock_get(item_repository_mock, item)

    catalogue_category_id = str(ObjectId())
    manufacturer_id = str(ObjectId())

    # Mock `get` to return a catalogue item
    test_helpers.mock_get(
        catalogue_item_repository_mock,
        CatalogueItemOut(
            id=item.catalogue_item_id,
            catalogue_category_id=catalogue_category_id,
            manufacturer_id=manufacturer_id,
            **{
                **FULL_CATALOGUE_ITEM_A_INFO,
                "properties": add_ids_to_properties(item_properties, FULL_CATALOGUE_ITEM_A_INFO["properties"]),
            },
        ),
    )
    # Mock `get` to return a catalogue category
    test_helpers.mock_get(
        catalogue_category_repository_mock,
        CatalogueCategoryOut(
            id=catalogue_category_id,
            **{
                **FULL_CATALOGUE_CATEGORY_A_INFO,
                "properties": add_ids_to_properties(
                    item_properties,
                    FULL_CATALOGUE_CATEGORY_A_INFO["properties"],
                ),
            },
        ),
    )

    properties = [{"id": prop.id, "value": prop.value} for prop in item.properties]
    properties[1]["value"] = "False"
    with pytest.raises(InvalidPropertyTypeError) as exc:
        item_service.update(
            item.id,
            ItemPatchSchema(properties=properties),
        )
    item_repository_mock.update.assert_not_called()
    assert (
        str(exc.value) == f"Invalid value type for property with ID '{item.properties[1].id}'. Expected type: boolean."
    )
