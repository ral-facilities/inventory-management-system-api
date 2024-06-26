"""
Mock data for use in unit tests

Names should ideally be descriptive enough to recognise what they are without looking at the data itself.
Letters may be appended in places to indicate the data is of the same type, but has different specific values
to others.

_POST_DATA - Is for a `PostSchema` schema
_IN_DATA - Is for an `In` model
_GET_DATA - Is for an entity schema - Used in assertions for e2e tests
"""

from unittest.mock import ANY

from inventory_management_system_api.models.catalogue_category import CatalogueCategoryPropertyIn

# Used for _GET_DATA's as when comparing these will not be possible to know
# at runtime
CREATED_MODIFIED_GET_DATA_EXPECTED = {"created_time": ANY, "modified_time": ANY}

# --------------------------------- CATALOGUE CATEGORIES ---------------------------------

CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_A = {
    "name": "Category A",
    "code": "category-a",
    "is_leaf": False,
    "parent_id": None,
    "properties": [],
}

CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_B = {
    "name": "Category B",
    "code": "catagory-b",
    "is_leaf": False,
    "parent_id": None,
    "properties": [],
}

CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES = {
    "name": "Leaf Category No Parent No Properties",
    "code": "leaf-category-no-parent-no-properties",
    "is_leaf": True,
    "parent_id": None,
    "properties": [],
}

CATALOGUE_CATEGORY_PROPERTY_BOOLEAN_MANDATORY_WITHOUT_UNIT = {
    "name": "Mandatory Boolean Property Without Unit",
    "type": "boolean",
    "mandatory": True,
}

CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT = {
    "name": "Non Mandatory Number Property With Unit",
    "type": "number",
    "unit": "mm",
    "mandatory": False,
}

CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES = {
    "name": "Leaf Category No Parent With Properties",
    "code": "leaf-category-no-parent-with-properties",
    "is_leaf": True,
    "parent_id": None,
    "properties": [
        CatalogueCategoryPropertyIn(**CATALOGUE_CATEGORY_PROPERTY_BOOLEAN_MANDATORY_WITHOUT_UNIT),
        CatalogueCategoryPropertyIn(**CATALOGUE_CATEGORY_PROPERTY_NUMBER_NON_MANDATORY_WITH_UNIT),
    ],
}


# --------------------------------- SYSTEMS ---------------------------------

SYSTEM_POST_DATA_NO_PARENT_A = {
    "parent_id": None,
    "name": "Test name A",
    "description": "Test description A",
    "location": "Test location A",
    "owner": "Test owner A",
    "importance": "low",
}

SYSTEM_POST_DATA_NO_PARENT_B = {
    "parent_id": None,
    "name": "Test name B",
    "description": "Test description B",
    "location": "Test location B",
    "owner": "Test owner B",
    "importance": "low",
}

SYSTEM_IN_DATA_NO_PARENT_A = {
    **SYSTEM_POST_DATA_NO_PARENT_A,
    "code": "test-name-a",
}

SYSTEM_IN_DATA_NO_PARENT_B = {
    **SYSTEM_POST_DATA_NO_PARENT_B,
    "code": "test-name-b",
}

SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY = {
    "name": "System Test Required Values Only",
    "importance": "low",
}

SYSTEM_GET_DATA_REQUIRED_VALUES_ONLY = {
    **SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "description": None,
    "location": None,
    "owner": None,
    "code": "system-test-required-values-only",
}

SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT = {
    **SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    "name": "System Test All Values",
    "parent_id": None,
    "description": "Test description",
    "location": "Test location",
    "owner": "Test owner",
}

SYSTEM_GET_DATA_ALL_VALUES_NO_PARENT = {
    **SYSTEM_POST_DATA_ALL_VALUES_NO_PARENT,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "system-test-all-values",
}
