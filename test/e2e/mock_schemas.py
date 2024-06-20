"""
Mock data for sharing between different e2e tests - In particular avoids circular imports between them
"""

# Leaf with allowed values in properties

from unittest.mock import ANY

CREATED_MODIFIED_VALUES_EXPECTED = {"created_time": ANY, "modified_time": ANY}

# pylint: disable=duplicate-code
CATALOGUE_CATEGORY_POST_ALLOWED_VALUES = {
    "name": "Category Allowed Values",
    "is_leaf": True,
    "properties": [
        {
            "name": "Property A",
            "type": "number",
            "unit": "mm",
            "mandatory": False,
            "allowed_values": {"type": "list", "values": [2, 4, 6]},
        },
        {
            "name": "Property B",
            "type": "string",
            "unit": None,
            "mandatory": True,
            "allowed_values": {"type": "list", "values": ["red", "green"]},
        },
    ],
}

CATALOGUE_CATEGORY_POST_ALLOWED_VALUES_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "category-allowed-values",
    "parent_id": None,
}

# To be posted on CATALOGUE_CATEGORY_POST_ALLOWED_VALUES
CATALOGUE_ITEM_POST_ALLOWED_VALUES = {
    "name": "Catalogue Item D",
    "description": "This is Catalogue Item D",
    "cost_gbp": 300.00,
    "cost_to_rework_gbp": 120.99,
    "days_to_replace": 1.5,
    "days_to_rework": 3.0,
    "drawing_number": "789xyz",
    "is_obsolete": False,
    "properties": [{"name": "Property A", "value": 4}, {"name": "Property B", "value": "red"}],
}

CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED = {
    **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "drawing_link": None,
    "item_model_number": None,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "notes": None,
    "properties": [
        {"name": "Property A", "unit": "mm", "value": 4},
        {"name": "Property B", "value": "red", "unit": None},
    ],
}

ITEM_POST_ALLOWED_VALUES = {
    "is_defective": False,
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "serial_number": "xyz123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
    "properties": [{"name": "Property A", "value": 6}, {"name": "Property B", "value": "green"}],
}

ITEM_POST_ALLOWED_VALUES_EXPECTED = {
    **ITEM_POST_ALLOWED_VALUES,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "purchase_order_number": None,
    "usage_status": "New",
    "usage_status_id": ANY,
    "asset_number": None,
    "properties": [
        {"name": "Property A", "unit": "mm", "value": 6},
        {"name": "Property B", "value": "green", "unit": None},
    ],
}

SYSTEM_POST_A = {
    "name": "System A",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
SYSTEM_POST_A_EXPECTED = {
    **SYSTEM_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "system-a",
}

# To be posted as a child of the above
SYSTEM_POST_B = {
    "name": "System B",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
SYSTEM_POST_B_EXPECTED = {
    **SYSTEM_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "system-b",
}

SYSTEM_POST_C = {
    "name": "System C",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
SYSTEM_POST_C_EXPECTED = {
    **SYSTEM_POST_C,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "system-c",
}
# pylint: enable=duplicate-code

USAGE_STATUS_POST_A = {"value": "New"}

USAGE_STATUS_POST_A_EXPECTED = {
    **USAGE_STATUS_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "new",
    "id": ANY,
}

USAGE_STATUS_POST_B = {"value": "Used"}

USAGE_STATUS_POST_B_EXPECTED = {
    **USAGE_STATUS_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "used",
    "id": ANY,
}

USAGE_STATUS_POST_C = {"value": "In Use"}

USAGE_STATUS_POST_C_EXPECTED = {
    **USAGE_STATUS_POST_C,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "in-use",
    "id": ANY,
}

USAGE_STATUS_POST_D = {"value": "Scrapped"}

USAGE_STATUS_POST_D_EXPECTED = {
    **USAGE_STATUS_POST_D,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "code": "scrapped",
    "id": ANY,
}
