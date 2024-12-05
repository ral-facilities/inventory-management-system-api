"""
Mock data for use in tests.

Names should ideally be descriptive enough to recognise what they are without looking at the data itself.
Letters may be appended in places to indicate the data is of the same type, but has different specific values
to others.

_POST_DATA - Is for a `PostSchema` schema.
_IN_DATA - Is for an `In` model.
_GET_DATA - Is for an entity schema - Used in assertions for e2e tests. May have IDs missing where they are possible
            to be known e.g. `manufacturer_id` in a catalogue item.
_DATA - Is none of the above - likely to be used in post requests as they are likely identical, only with some ids
        missing so that they can be added later e.g. for pairing up units that aren't known before hand.
"""

from unittest.mock import ANY

from bson import ObjectId

from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.models.usage_status import UsageStatusIn, UsageStatusOut

# ---------------------------- GENERAL -----------------------------

# Used for _GET_DATA's as when comparing these will not be possible to know at runtime
CREATED_MODIFIED_GET_DATA_EXPECTED = {"created_time": ANY, "modified_time": ANY}

# ---------------------------- AUTHENTICATION -----------------------------

VALID_ACCESS_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InVzZXJuYW1lIiwiZXhwIjoyNTM0MDIzMDA3OTl9.bagU2Wix8wKzydVU_L3Z"
    "ZuuMAxGxV4OTuZq_kS2Fuwm839_8UZOkICnPTkkpvsm1je0AWJaIXLGgwEa5zUjpG6lTrMMmzR9Zi63F0NXpJqQqoOZpTBMYBaggsXqFkdsv-yAKUZ"
    "8MfjCEyk3UZ4PXZmEcUZcLhKcXZr4kYJPjio2e5WOGpdjK6q7s-iHGs9DQFT_IoCnw9CkyOKwYdgpB35hIGHkNjiwVSHpyKbFQvzJmIv5XCTSRYqq0"
    "1fldh-QYuZqZeuaFidKbLRH610o2-1IfPMUr-yPtj5PZ-AaX-XTLkuMqdVMCk0_jeW9Os2BPtyUDkpcu1fvW3_S6_dK3nQ"
)

VALID_ACCESS_TOKEN_MISSING_USERNAME = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjI1MzQwMjMwMDc5OX0.h4Hv_sq4-ika1rpuRx7k3pp0cF_BZ65WVSbIHS7oh9SjPpGHt"
    "GhVHU1IJXzFtyA9TH-68JpAZ24Dm6bXbH6VJKoc7RCbmJXm44ufN32ga7jDqXH340oKvi_wdhEHaCf2HXjzsHHD7_D6XIcxU71v2W5_j8Vuwpr3SdX"
    "6ea_yLIaCDWynN6FomPtUepQAOg3c7DdKohbJD8WhKIDV8UKuLtFdRBfN4HEK5nNs0JroROPhcYM9L_JIQZpdI0c83fDFuXQC-cAygzrSnGJ6O4DyS"
    "cNL3VBNSmNTBtqYOs1szvkpvF9rICPgbEEJnbS6g5kmGld3eioeuDJIxeQglSbxog"
)

EXPIRED_ACCESS_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InVzZXJuYW1lIiwiZXhwIjotNjIxMzU1OTY4MDB9.G_cfC8PNYE5yERyyQNRk"
    "9mTmDusU_rEPgm7feo2lWQF6QMNnf8PUN-61FfMNRVE0QDSvAmIMMNEOa8ma0JHZARafgnYJfn1_FSJSoRxC740GpG8EFSWrpM-dQXnoD263V9FlK-"
    "On6IbhF-4Rh9MdoxNyZk2Lj7NvCzJ7gbgbgYM5-sJXLxB-I5LfMfuYM3fx2cRixZFA153l46tFzcMVBrAiBxl_LdyxTIOPfHF0UGlaW2UtFi02gyBU"
    "4E4wTOqPc4t_CSi1oBSbY7h9O63i8IU99YsOCdvZ7AD3ePxyM1xJR7CFHycg9Z_IDouYnJmXpTpbFMMl7SjME3cVMfMrAQ"
)

INVALID_ACCESS_TOKEN = VALID_ACCESS_TOKEN + "1"

# ---------------------------- USAGE STATUSES -----------------------------

# New
USAGE_STATUS_POST_DATA_NEW = {"value": "New"}

USAGE_STATUS_IN_DATA_NEW = {
    **USAGE_STATUS_POST_DATA_NEW,
    "code": "new",
}

USAGE_STATUS_OUT_DATA_NEW = UsageStatusOut(
    **UsageStatusIn(**USAGE_STATUS_IN_DATA_NEW).model_dump(), _id=str(ObjectId())
).model_dump()

USAGE_STATUS_GET_DATA_NEW = {
    **USAGE_STATUS_POST_DATA_NEW,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "code": "new",
    "id": ANY,
}

# In Use
USAGE_STATUS_POST_DATA_IN_USE = {"value": "In Use"}

USAGE_STATUS_IN_DATA_IN_USE = {**USAGE_STATUS_POST_DATA_IN_USE, "code": "in-use"}

# Used
USAGE_STATUS_POST_DATA_USED = {"value": "Used"}

USAGE_STATUS_IN_DATA_USED = {
    **USAGE_STATUS_POST_DATA_USED,
    "code": "used",
}

USAGE_STATUS_OUT_DATA_USED = UsageStatusOut(
    **UsageStatusIn(**USAGE_STATUS_IN_DATA_USED).model_dump(), _id=str(ObjectId())
).model_dump()

USAGE_STATUS_GET_DATA_USED = {
    **USAGE_STATUS_POST_DATA_USED,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "code": "used",
    "id": ANY,
}

# --------------------------------- UNITS ---------------------------------

# mm
UNIT_POST_DATA_MM = {"value": "mm"}

UNIT_IN_DATA_MM = {**UNIT_POST_DATA_MM, "code": "mm"}

UNIT_GET_DATA_MM = {**UNIT_IN_DATA_MM, **CREATED_MODIFIED_GET_DATA_EXPECTED, "id": ANY}

# cm
UNIT_POST_DATA_CM = {"value": "cm"}

UNIT_IN_DATA_CM = {**UNIT_POST_DATA_CM, "code": "cm"}

UNIT_GET_DATA_CM = {**UNIT_POST_DATA_CM, **CREATED_MODIFIED_GET_DATA_EXPECTED, "id": ANY, "code": "cm"}


# --------------------------------- CATALOGUE CATEGORY PROPERTIES ---------------------------------

# Boolean, Mandatory, No unit

CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY = {
    "name": "Mandatory Boolean Property Without Unit",
    "type": "boolean",
    "mandatory": True,
}

CATALOGUE_CATEGORY_PROPERTY_IN_DATA_BOOLEAN_MANDATORY = {**CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_BOOLEAN_MANDATORY = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY,
    "id": ANY,
    "unit": None,
    "allowed_values": None,
}

# Number, Non Mandatory, mm unit

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
    "allowed_values": None,
}

# Number, Non Mandatory, No unit

CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY = {
    "name": "Non Mandatory Number Property",
    "type": "number",
    "mandatory": False,
}

CATALOGUE_CATEGORY_PROPERTY_IN_DATA_NUMBER_NON_MANDATORY = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
    "unit_id": None,
}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY,
    "id": ANY,
    "allowed_values": None,
    "unit": None,
}

# Number, Non Mandatory, Allowed values list

CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST = {
    "name": "Non Mandatory Number Property With Allowed Values",
    "type": "number",
    "mandatory": False,
    "allowed_values": {"type": "list", "values": [1, 2, 3]},
}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST,
    "id": ANY,
    "unit": None,
}

# Number, Mandatory, No unit
CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_MANDATORY = {
    "name": "Mandatory Number Property",
    "type": "number",
    "mandatory": True,
}

# String, Mandatory

CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY = {
    "name": "Mandatory String Property",
    "type": "string",
    "mandatory": True,
}

CATALOGUE_CATEGORY_PROPERTY_GET_DATA_STRING_MANDATORY = {
    **CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY,
    "id": ANY,
    "allowed_values": None,
    "unit": None,
}

# String, Non Mandatory, Allowed values list

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

# Leaf, No parent, Properties, mm unit

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

# --------------------------------- PROPERTIES ---------------------------------

# Boolean, Mandatory, False
PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_BOOLEAN_MANDATORY["name"],
    "value": False,
}

PROPERTY_GET_DATA_BOOLEAN_MANDATORY_FALSE = {**PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE}

# Boolean, Mandatory, True

PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE = {
    **PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE,
    "value": True,
}

PROPERTY_GET_DATA_BOOLEAN_MANDATORY_TRUE = {**PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE}

# Number, Non Mandatory, Allowed Values List, None

PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST["name"],
    "value": None,
}

# Number, Non Mandatory, Allowed Values List, 1

PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1 = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST["name"],
    "value": 1,
}

PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1 = {
    **PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_1
}

# Number, Non Mandatory, Allowed Values List, 2

PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_2 = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST["name"],
    "value": 2,
}

PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_2 = {
    **PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_2
}

# Number, Non Mandatory, mm unit, 1

PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1 = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT["name"],
    "value": 1,
}

PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1 = {**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1}

# Number, Non Mandatory, mm unit, 42

PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42 = {
    **PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1,
    "value": 42,
}

PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42 = {**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42}

# Number, Non Mandatory, mm unit, None

PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT["name"],
    "value": None,
}

PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE = {**PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE}

# Number, Non Mandatory, No unit, None
PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_NONE = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_NUMBER_NON_MANDATORY["name"],
    "value": None,
}

# String, Mandatory, text
PROPERTY_DATA_STRING_MANDATORY_TEXT = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_MANDATORY["name"],
    "value": "text",
}

PROPERTY_GET_DATA_STRING_MANDATORY_TEXT = {**PROPERTY_DATA_STRING_MANDATORY_TEXT}

# String, Non Mandatory, Allowed Values List, value1

PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1 = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST["name"],
    "value": "value1",
}

PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1 = {
    **PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1
}

# String, Non Mandatory, Allowed Values List, value2

PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE2 = {
    **PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
    "value": "value2",
}

PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE2 = {
    **PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE2
}

# String, Non Mandatory, Allowed Values List, None

PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE = {
    "name": CATALOGUE_CATEGORY_PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST["name"],
    "value": None,
}

PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE = {
    **PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE
}

# --------------------------------- CATALOGUE ITEMS ---------------------------------

# This is the base catalogue category to be used in tests with properties
BASE_CATALOGUE_CATEGORY_DATA_WITH_PROPERTIES_MM = CATALOGUE_CATEGORY_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM
BASE_CATALOGUE_CATEGORY_IN_DATA_WITH_PROPERTIES_MM = CATALOGUE_CATEGORY_IN_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM
BASE_CATALOGUE_CATEGORY_GET_DATA_WITH_PROPERTIES_MM = CATALOGUE_CATEGORY_GET_DATA_LEAF_NO_PARENT_WITH_PROPERTIES_MM


# No properties

CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY = {
    "name": "Catalogue Item Required Values Only",
    "cost_gbp": 42,
    "days_to_replace": 7,
    "is_obsolete": False,
}

CATALOGUE_ITEM_IN_DATA_REQUIRED_VALUES_ONLY = {
    **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    "catalogue_category_id": str(ObjectId()),
    "manufacturer_id": str(ObjectId()),
    "number_of_spares": None,
}

CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY = {
    **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "description": None,
    "cost_to_rework_gbp": None,
    "days_to_rework": None,
    "expected_lifetime_days": None,
    "drawing_number": None,
    "drawing_link": None,
    "item_model_number": None,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "notes": None,
    "properties": [],
    "number_of_spares": None,
}

# Not obsolete, No properties

CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES = {
    **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    "name": "Catalogue Item Not Obsolete No Properties",
    "description": "Some description",
    "cost_to_rework_gbp": 9001,
    "days_to_rework": 3,
    "expected_lifetime_days": 3002,
    "drawing_number": "12345-1",
    "drawing_link": "http://example.com/",
    "item_model_number": "123456-1",
    "is_obsolete": False,
    "notes": "Some notes",
}

CATALOGUE_ITEM_IN_DATA_NOT_OBSOLETE_NO_PROPERTIES = {
    **CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    "catalogue_category_id": str(ObjectId()),
    "manufacturer_id": str(ObjectId()),
    "number_of_spares": None,
}

CATALOGUE_ITEM_GET_DATA_NOT_OBSOLETE_NO_PROPERTIES = {
    **CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "properties": [],
    "number_of_spares": None,
}

# Obsolete, No properties
CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES = {
    **CATALOGUE_ITEM_DATA_NOT_OBSOLETE_NO_PROPERTIES,
    "name": "Catalogue Item Obsolete No Properties",
    "is_obsolete": True,
    "obsolete_reason": "Manufacturer no longer exists",
}

CATALOGUE_ITEM_GET_DATA_OBSOLETE_NO_PROPERTIES = {
    **CATALOGUE_ITEM_DATA_OBSOLETE_NO_PROPERTIES,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "properties": [],
    "number_of_spares": None,
}

# All properties

CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES = {
    **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    "name": "Catalogue Item With All Properties",
    "properties": [
        PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE,
        PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42,
        PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
    ],
}

CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES = {
    **CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
    **CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    "properties": [
        PROPERTY_GET_DATA_BOOLEAN_MANDATORY_TRUE,
        PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_42,
        PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE1,
    ],
    "number_of_spares": None,
}

# Only mandatory properties

CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY = {
    **CATALOGUE_ITEM_DATA_REQUIRED_VALUES_ONLY,
    "name": "Catalogue Item With Mandatory Properties Only",
    "properties": [PROPERTY_DATA_BOOLEAN_MANDATORY_TRUE],
}

CATALOGUE_ITEM_GET_DATA_WITH_MANDATORY_PROPERTIES_ONLY = {
    **CATALOGUE_ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
    **CATALOGUE_ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY,
    "properties": [
        PROPERTY_GET_DATA_BOOLEAN_MANDATORY_TRUE,
        PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_NONE,
        PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_NONE,
    ],
    "number_of_spares": None,
}

# ------------------------------------- ITEMS -------------------------------------

# This is the base catalogue item to be used in tests with properties
BASE_CATALOGUE_ITEM_DATA_WITH_PROPERTIES = CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES


# Required values only

ITEM_DATA_REQUIRED_VALUES_ONLY = {
    "is_defective": False,
    "usage_status": "In Use",
}

ITEM_IN_DATA_REQUIRED_VALUES_ONLY = {
    **ITEM_DATA_REQUIRED_VALUES_ONLY,
    "catalogue_item_id": str(ObjectId()),
    "system_id": str(ObjectId()),
    "usage_status_id": str(ObjectId()),
}

ITEM_GET_DATA_REQUIRED_VALUES_ONLY = {
    **ITEM_DATA_REQUIRED_VALUES_ONLY,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "purchase_order_number": None,
    "warranty_end_date": None,
    "asset_number": None,
    "serial_number": None,
    "delivered_date": None,
    "notes": None,
    "properties": [],
}

# All values, no properties

ITEM_DATA_ALL_VALUES_NO_PROPERTIES = {
    **ITEM_DATA_REQUIRED_VALUES_ONLY,
    "purchase_order_number": "1234-123",
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "asset_number": "1234-123456",
    "serial_number": "1234-123456-123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
}

ITEM_IN_DATA_ALL_VALUES_NO_PROPERTIES = {
    **ITEM_DATA_ALL_VALUES_NO_PROPERTIES,
    "catalogue_item_id": str(ObjectId()),
    "system_id": str(ObjectId()),
    "usage_status_id": str(ObjectId()),
    "usage_status": "In Use",
}

ITEM_GET_DATA_ALL_VALUES_NO_PROPERTIES = {
    **ITEM_DATA_ALL_VALUES_NO_PROPERTIES,
    **CREATED_MODIFIED_GET_DATA_EXPECTED,
    "id": ANY,
    "properties": [],
}


# Only mandatory properties

ITEM_DATA_WITH_MANDATORY_PROPERTIES_ONLY = {
    **ITEM_DATA_REQUIRED_VALUES_ONLY,
    "properties": [PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE],
}

# All properties

ITEM_DATA_WITH_ALL_PROPERTIES = {
    **ITEM_DATA_REQUIRED_VALUES_ONLY,
    "properties": [
        PROPERTY_DATA_BOOLEAN_MANDATORY_FALSE,
        PROPERTY_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1,
        PROPERTY_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE2,
    ],
}

ITEM_GET_DATA_WITH_ALL_PROPERTIES = {
    **ITEM_GET_DATA_REQUIRED_VALUES_ONLY,
    "properties": [
        PROPERTY_GET_DATA_BOOLEAN_MANDATORY_FALSE,
        PROPERTY_GET_DATA_NUMBER_NON_MANDATORY_WITH_MM_UNIT_1,
        PROPERTY_GET_DATA_STRING_NON_MANDATORY_WITH_ALLOWED_VALUES_LIST_VALUE2,
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

# --------------------------------- SETTINGS ---------------------------------

# Spares definition, New
SETTING_SPARES_DEFINITION_DATA_NEW = {"usage_statuses": [{"value": USAGE_STATUS_POST_DATA_NEW["value"]}]}

SETTING_SPARES_DEFINITION_GET_DATA_NEW = {"usage_statuses": [USAGE_STATUS_GET_DATA_NEW]}

# Spares definition, New or Used
SETTING_SPARES_DEFINITION_DATA_NEW_USED = {
    "usage_statuses": [{"value": USAGE_STATUS_POST_DATA_NEW["value"]}, {"value": USAGE_STATUS_POST_DATA_USED["value"]}]
}

SETTING_SPARES_DEFINITION_IN_DATA_NEW_USED = {
    "usage_statuses": [{"id": USAGE_STATUS_OUT_DATA_NEW["id"]}, {"id": USAGE_STATUS_OUT_DATA_USED["id"]}]
}

SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED = {
    "_id": SparesDefinitionOut.SETTING_ID,
    "usage_statuses": [USAGE_STATUS_OUT_DATA_NEW, USAGE_STATUS_OUT_DATA_USED],
}

SETTING_SPARES_DEFINITION_GET_DATA_NEW_USED = {
    "usage_statuses": [USAGE_STATUS_GET_DATA_NEW, USAGE_STATUS_GET_DATA_USED]
}
