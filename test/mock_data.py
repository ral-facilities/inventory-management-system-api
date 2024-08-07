"""
Mock data for use in unit tests

Names should ideally be descriptive enough to recognise what they are without looking at the data itself.
Letters may be appended in places to indicate the data is of the same type, but has different specific values
to others.

_POST_DATA - Is for a `PostSchema` schema
_IN_DATA - Is for an `In` model
_GET_DATA - Is for an entity schema - Used in assertions for e2e tests
_DATA - Is none of the above - likely to be used in post requests as they are likely identical, only
        with some ids missing so that they can be added later e.g. for pairing up units that aren't
        known before hand
"""

from unittest.mock import ANY

from bson import ObjectId

# Used for _GET_DATA's as when comparing these will not be possible to know
# at runtime
CREATED_MODIFIED_GET_DATA_EXPECTED = {"created_time": ANY, "modified_time": ANY}

# --------------------------------- UNITS ---------------------------------

UNIT_POST_DATA_MM = {"value": "mm"}

UNIT_IN_DATA_MM = {**UNIT_POST_DATA_MM, "code": "mm"}

# --------------------------------- CATALOGUE CATEGORY PROPERTIES ---------------------------------

# Boolean, No unit

CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY = {
    "name": "Mandatory Boolean Property Without Unit",
    "type": "boolean",
    "mandatory": True,
}

CATALOGUE_CATEGORY_PROPERTY_IN_DATA_BOOLEAN_MANDATORY = {**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_BOOLEAN_MANDATORY = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    "id": ANY,
    "unit_id": ANY,
    "unit": None,
    "allowed_values": None,
}

# Number, mm unit

CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT = {
    "name": "Non Mandatory Number Property With Unit",
    "type": "number",
    "unit": "mm",
    "mandatory": False,
}

CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    "unit_id": str(ObjectId()),
}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
    "id": ANY,
    "unit_id": ANY,
    "allowed_values": None,
}

# String, Allowed values list

CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST = {
    "name": "Non Mandatory String Property With Allowed Values",
    "type": "string",
    "mandatory": False,
    "allowed_values": {"type": "list", "values": ["value1", "value2", "value3"]},
}

CATALOGUE_CATEGORY_PROPERTY_IN_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    "unit_id": str(ObjectId()),
}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    "id": ANY,
    "unit_id": ANY,
    "unit": None,
}

# --------------------------------- CATALOGUE CATEGORIES ---------------------------------

# Non leaf, Required values only

CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY = {
    "name": "Non Leaf Catalogue Category Required Values Only",
    "is_leaf": False,
}

CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_REQUIRED_VALUES_ONLY = {
    **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "non-leaf-catalogue-category-required-values-only",
    "properties": [],
}

# Non leaf, No parent, No properties

CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A = {
    "name": "Category A",
    "is_leaf": False,
    "parent_id": None,
}

CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A = {
    **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    "code": "category-a",
}

CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A = {
    **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_A,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "properties": [],
}


CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B = {
    "name": "Category B",
    "is_leaf": False,
    "parent_id": None,
}

CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B = {
    **CATALOGUE_CATEGORY_POST_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    "code": "category-b",
}

CATALOGUE_CATEGORY_GET_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B = {
    **CATALOGUE_CATEGORY_IN_DATA_NON_LEAF_NO_PARENT_NO_PROPERTIES_B,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "properties": [],
}

# Leaf, No parent, No properties

CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES = {
    "name": "Leaf Category No Parent No Properties",
    "is_leaf": True,
    "parent_id": None,
}


CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_NO_PROPERTIES = {
    **CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    "code": "leaf-category-no-parent-no-properties",
    "properties": [],
}

CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_NO_PROPERTIES = {
    **CATALOGUE_CATEGORY_POST_DATA_LEAF_NO_PARENT_NO_PROPERTIES,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "code": "leaf-category-no-parent-no-properties",
    "properties": [],
}

# --------------------------------- Properties ---------------------------------

# Leaf, Required values only

CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY = {
    "name": "Leaf Catalogue Category Required Values Only",
    "is_leaf": True,
}

CATALOGUE_CATEGORY_GET_DATA_LEAF_REQUIRED_VALUES_ONLY = {
    **CATALOGUE_CATEGORY_POST_DATA_LEAF_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "leaf-catalogue-category-required-values-only",
    "properties": [],
}

# Leaf, No parent, Properties - with mm unit

# Put _MM at end to signify what units this data would require
CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM = {
    "name": "Leaf Category No Parent With Properties",
    "is_leaf": True,
    "parent_id": None,
    "properties": [
        CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
        CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
        CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    ],
}

CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM = {
    **CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    "code": "leaf-category-no-parent-with-properties",
    "properties": [
        CATALOGUE_CATEGORY_PROPERTY_IN_DATA_BOOLEAN_MANDATORY,
        CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
        CATALOGUE_CATEGORY_PROPERTY_IN_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    ],
}


CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM = {
    **CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "parent_id": None,
    "code": "leaf-category-no-parent-with-properties",
    "properties": [
        CATALOGUE_CATEGORY_PROPERTY_GET_DATA_BOOLEAN_MANDATORY,
        CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT,
        CATALOGUE_CATEGORY_PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    ],
}

# --------------------------------- MANUFACTURERS ---------------------------------

# Required values only

MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY = {
    "name": "Manufacturer Test Required Values Only",
    "address": {
        "address_line": "1 Example Street",
        "country": "United Kingdom",
        "postcode": "OX1 2AB",
    },
}

MANUFACTURER_GET_DATA_REQUIRED_VALUES_ONLY = {
    **MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "address": {**MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY["address"], "town": None, "county": None},
    "id": ANY,
    "code": "manufacturer-test-required-values-only",
    "url": None,
    "telephone": None,
}

# All values

MANUFACTURER_POST_DATA_ALL_VALUES = {
    **MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY,
    "address": {**MANUFACTURER_POST_DATA_REQUIRED_VALUES_ONLY["address"], "town": "Oxford", "county": "Oxfordshire"},
    "name": "Manufacturer Test All Values",
    "url": "http://testurl.co.uk/",
    "telephone": "0932348348",
}

MANUFACTURER_GET_DATA_ALL_VALUES = {
    **MANUFACTURER_POST_DATA_ALL_VALUES,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "code": "manufacturer-test-all-values",
}

MANUFACTURER_POST_DATA_A = {
    **MANUFACTURER_POST_DATA_ALL_VALUES,
    "name": "Manufacturer A",
}

MANUFACTURER_IN_DATA_A = {
    **MANUFACTURER_POST_DATA_A,
    "code": "manufacturer-a",
}

MANUFACTURER_POST_DATA_B = {
    **MANUFACTURER_POST_DATA_ALL_VALUES,
    "address": {**MANUFACTURER_POST_DATA_ALL_VALUES["address"], "address_line": "2 Example Street"},
    "name": "Manufacturer B",
    "url": "http://example.co.uk/",
    "telephone": "073434394",
}

MANUFACTURER_IN_DATA_B = {
    **MANUFACTURER_POST_DATA_B,
    "code": "manufacturer-b",
}

# --------------------------------- SYSTEMS ---------------------------------

# No parent, Required values only

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

# No parent, All values

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

# No parent

SYSTEM_POST_DATA_NO_PARENT_A = {
    "parent_id": None,
    "name": "Test name A",
    "description": "Test description A",
    "location": "Test location A",
    "owner": "Test owner A",
    "importance": "low",
}

SYSTEM_IN_DATA_NO_PARENT_A = {
    **SYSTEM_POST_DATA_NO_PARENT_A,
    "code": "test-name-a",
}

SYSTEM_POST_DATA_NO_PARENT_B = {
    "parent_id": None,
    "name": "Test name B",
    "description": "Test description B",
    "location": "Test location B",
    "owner": "Test owner B",
    "importance": "low",
}

SYSTEM_IN_DATA_NO_PARENT_B = {
    **SYSTEM_POST_DATA_NO_PARENT_B,
    "code": "test-name-b",
}
