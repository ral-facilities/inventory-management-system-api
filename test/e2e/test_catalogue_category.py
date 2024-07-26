# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue category router.
"""
from test.conftest import add_ids_to_properties
from test.e2e.conftest import replace_unit_values_with_ids_in_properties
from test.e2e.mock_schemas import (
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES_EXPECTED,
    CREATED_MODIFIED_VALUES_EXPECTED,
)
from test.e2e.test_unit import UNIT_POST_A
from unittest.mock import ANY

from bson import ObjectId

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH

CATALOGUE_CATEGORY_POST_A = {"name": "Category A", "is_leaf": False}
CATALOGUE_CATEGORY_POST_A_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "category-a",
    "parent_id": None,
    "properties": [],
}

# To be posted as a child of the above - leaf with parent
CATALOGUE_CATEGORY_POST_B = {
    "name": "Category B",
    "is_leaf": True,
    "properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
    ],
}
CATALOGUE_CATEGORY_POST_B_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "category-b",
    "properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False, "allowed_values": None},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True, "allowed_values": None},
    ],
}

# Leaf with no parent
CATALOGUE_CATEGORY_POST_C = {
    "name": "Category C",
    "is_leaf": True,
    "properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
    ],
}
CATALOGUE_CATEGORY_POST_C_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_C,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "code": "category-c",
    "parent_id": None,
    "properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False, "allowed_values": None},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True, "allowed_values": None},
    ],
}

# pylint: disable=duplicate-code
MANUFACTURER = {
    "name": "Manufacturer D",
    "url": "http://example.com/",
    "address": {
        "address_line": "1 Example Street",
        "town": "Oxford",
        "county": "Oxfordshire",
        "country": "United Kingdom",
        "postcode": "OX1 2AB",
    },
    "telephone": "0932348348",
}
# pylint: enable=duplicate-code

CATALOGUE_ITEM_POST_A = {
    "name": "Catalogue Item A",
    "description": "This is Catalogue Item A",
    "cost_gbp": 129.99,
    "days_to_replace": 2.0,
    "is_obsolete": False,
    "properties": [{"name": "Property B", "value": False}],
}


def _post_nested_catalogue_categories(test_client, entities: list[dict]):
    """Utility function for posting a set of mock catalogue categories where each successive entity should
    be the parent of the next"""

    categories = []
    parent_id = None
    for entity in entities:
        system = test_client.post("/v1/catalogue-categories", json={**entity, "parent_id": parent_id}).json()
        parent_id = system["id"]
        categories.append(system)

    return (*categories,)


def _post_catalogue_categories(test_client):
    """Utility function for posting all mock systems defined at the top of this file"""

    units, _ = _post_units(test_client)

    (category_a, category_b, *_) = _post_nested_catalogue_categories(
        test_client,
        [
            CATALOGUE_CATEGORY_POST_A,
            {
                **CATALOGUE_CATEGORY_POST_B,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_B["properties"], units
                ),
            },
        ],
    )
    (category_c, *_) = _post_nested_catalogue_categories(
        test_client,
        [
            {
                **CATALOGUE_CATEGORY_POST_C,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_C["properties"], units
                ),
            }
        ],
    )

    return category_a, category_b, category_c


def _post_n_catalogue_categories(test_client, number):
    """Utility function to post a given number of nested catalogue categories (all based on system A)"""
    return _post_nested_catalogue_categories(
        test_client,
        [
            {
                **CATALOGUE_CATEGORY_POST_A,
                "name": f"Category {i}",
            }
            for i in range(0, number)
        ],
    )


def _post_units(test_client):
    """Utility function for posting all mock units defined at the top of this file"""

    response = test_client.post("/v1/units", json=UNIT_POST_A)

    unit_mm = response.json()

    units = [unit_mm]

    unit_value_to_id = {unit_mm["value"]: unit_mm["id"]}
    return units, unit_value_to_id


def test_create_catalogue_category(test_client):
    """
    Test creating a catalogue category.
    """

    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    assert response.status_code == 201

    catalogue_category = response.json()

    assert catalogue_category == CATALOGUE_CATEGORY_POST_A_EXPECTED


def test_create_catalogue_category_with_valid_parent_id(test_client):
    """
    Test creating a catalogue category with a valid parent ID.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    units, _ = _post_units(test_client)

    # Child
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )

    assert response.status_code == 201
    catalogue_category = response.json()
    assert catalogue_category == {
        **CATALOGUE_CATEGORY_POST_B_EXPECTED,
        "parent_id": parent_catalogue_category["id"],
        "properties": add_ids_to_properties(
            catalogue_category["properties"],
            CATALOGUE_CATEGORY_POST_B_EXPECTED["properties"],
        ),
    }


def test_create_catalogue_category_with_duplicate_name_within_parent(test_client):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    units, _ = _post_units(test_client)

    # Child - post twice as will have the same name
    test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_create_catalogue_category_with_non_existent_unit_id(test_client):
    """
    Test creating a catalogue category with non existent unit ID.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    unit_mm = {
        "id": str(ObjectId()),
        "value": "mm",
        "code": "mm",
        **CREATED_MODIFIED_VALUES_EXPECTED,
    }
    units = [unit_mm]

    # Child
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified unit does not exist"


def test_create_catalogue_category_with_invalid_unit_id(test_client):
    """
    Test creating a catalogue category with invalid unit ID.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    unit_mm = {
        "id": "invalid",
        "value": "mm",
        "code": "mm",
        **CREATED_MODIFIED_VALUES_EXPECTED,
    }
    units = [unit_mm]

    # Child
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified unit does not exist"


def test_create_catalogue_category_with_invalid_parent_id(test_client):
    """
    Test creating a catalogue category with an invalid parent ID.
    """
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "parent_id": "invalid"}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category does not exist"


def test_create_catalogue_category_with_non_existent_parent_id(test_client):
    """
    Test creating a catalogue category with a non-existent parent ID.
    """
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "parent_id": str(ObjectId())}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category does not exist"


def test_create_catalogue_category_with_leaf_parent_catalogue_category(test_client):
    """
    Test creating a catalogue category in a leaf parent catalogue category.
    """

    units, _ = _post_units(test_client)

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_C,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_C["properties"], units),
        },
    )
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "parent_id": parent_id}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue category to a leaf parent catalogue category is not allowed"


def test_create_catalogue_category_with_invalid_property_type(test_client):
    """
    Test creating a catalogue category with an invalid property type.
    """

    _, unit_value_to_id = _post_units(test_client)

    catalogue_category = {
        **CATALOGUE_CATEGORY_POST_C,
        "properties": [
            {"name": "Property A", "type": "invalid-type", "unit_id": unit_value_to_id["mm"], "mandatory": False},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be 'string', 'number' or 'boolean'"


def test_create_catalogue_category_with_duplicate_property_names(test_client):
    """
    Test creating a catalogue category with duplicate property names.
    """

    catalogue_category = {
        **CATALOGUE_CATEGORY_POST_C,
        "properties": [
            {"name": "Duplicate", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Duplicate", "type": "boolean", "mandatory": True},
        ],
    }

    units, _ = _post_units(test_client)

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **catalogue_category,
            "properties": replace_unit_values_with_ids_in_properties(catalogue_category["properties"], units),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (f"Duplicate property name: {catalogue_category['properties'][0]['name']}")


def test_create_catalogue_category_with_disallowed_unit_value_for_boolean_property(test_client):
    """
    Test creating a catalogue category when a unit is supplied for a boolean property.
    """

    _, unit_value_to_id = _post_units(test_client)
    catalogue_category = {
        **CATALOGUE_CATEGORY_POST_C,
        "properties": [
            {"name": "Property A", "type": "boolean", "unit_id": unit_value_to_id["mm"], "mandatory": False},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Value error, Unit not allowed for boolean property 'Property A'"


def test_create_leaf_catalogue_category_without_properties(test_client):
    """
    Test creating a catalogue category.
    """
    catalogue_category = {**CATALOGUE_CATEGORY_POST_C}
    del catalogue_category["properties"]
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 201
    catalogue_category = response.json()
    assert catalogue_category == {**CATALOGUE_CATEGORY_POST_C_EXPECTED, "properties": []}


def test_create_non_leaf_catalogue_category_with_properties(test_client):
    """
    Test creating a non-leaf catalogue category with properties.
    """

    units, _ = _post_units(test_client)

    catalogue_category = {
        **CATALOGUE_CATEGORY_POST_A,
        "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 201
    catalogue_category = response.json()
    assert catalogue_category == CATALOGUE_CATEGORY_POST_A_EXPECTED


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_list_length(test_client):
    """
    Test creating a catalogue category with a number property containing an allowed_values list that is empty
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "number",
                    "mandatory": False,
                    "allowed_values": {"type": "list", "values": []},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "List should have at least 1 item after validation, not 0"


def test_create_catalogue_category_with_properties_with_allowed_values(test_client):
    """
    Test creating a catalogue category with specific allowed values given
    """

    units, _ = _post_units(test_client)

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **{
                **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES["properties"], units
                ),
            },
        },
    )

    assert response.status_code == 201
    catalogue_category = response.json()
    print(CATALOGUE_CATEGORY_POST_ALLOWED_VALUES_EXPECTED)
    assert catalogue_category == {
        **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES_EXPECTED,
        "properties": add_ids_to_properties(
            catalogue_category["properties"],
            CATALOGUE_CATEGORY_POST_ALLOWED_VALUES_EXPECTED["properties"],
        ),
    }


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_list_number(test_client):
    """
    Test creating a catalogue category with a number property containing an allowed_values list with an invalid
    number
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "number",
                    "mandatory": False,
                    "allowed_values": {"type": "list", "values": [2, "4", 6]},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself"
    )


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_list_string(test_client):
    """
    Test creating a catalogue category with a string property containing an allowed_values list with an invalid
    string
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "string",
                    "mandatory": False,
                    "allowed_values": {"type": "list", "values": ["red", "green", 6]},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself"
    )


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_list_duplicate_number(test_client):
    """
    Test creating a catalogue category with a number property containing an allowed_values list with a duplicate
    number value in it
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "number",
                    "mandatory": False,
                    "allowed_values": {"type": "list", "values": [42, 10.2, 12, 42]},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' contains a duplicate value: 42"
    )


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_list_duplicate_string(test_client):
    """
    Test creating a catalogue category with a string property containing an allowed_values list with a duplicate
    string value in it
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "string",
                    "mandatory": False,
                    "allowed_values": {"type": "list", "values": ["value1", "value2", "value3", "Value2"]},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' contains a duplicate value: Value2"
    )


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_list_boolean(test_client):
    """
    Test creating a catalogue category with a boolean property containing an allowed_values list
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "boolean",
                    "mandatory": False,
                    "allowed_values": {"type": "list", "values": ["red", "green"]},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values not allowed for a boolean property 'Property A'"
    )


def test_create_catalogue_category_with_properties_with_invalid_allowed_values_type(test_client):
    """
    Test creating a catalogue category with a property containing allowed_values with an invalid type
    """
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "properties": [
                {
                    "name": "Property A",
                    "type": "string",
                    "mandatory": False,
                    "allowed_values": {"type": "string"},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Input tag 'string' found using 'type' does not match any of the expected tags: 'list'"
    )


def test_delete_catalogue_category(test_client):
    """
    Test deleting a catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.delete(f"/v1/catalogue-categories/{catalogue_category['id']}")

    assert response.status_code == 204
    response = test_client.get(f"/v1/catalogue-categories/{catalogue_category['id']}")
    assert response.status_code == 404


def test_delete_catalogue_category_with_invalid_id(test_client):
    """
    Test deleting a catalogue category with an invalid ID.
    """
    response = test_client.delete("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_delete_catalogue_category_with_non_existent_id(test_client):
    """
    Test deleting a catalogue category with a non-existent ID.
    """
    response = test_client.delete(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_delete_catalogue_category_with_child_catalogue_categories(test_client):
    """
    Test deleting a catalogue category with child catalogue categories.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    units, _ = _post_units(test_client)

    # Child
    test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )

    response = test_client.delete(f"/v1/catalogue-categories/{parent_catalogue_category['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be deleted"


def test_delete_catalogue_category_with_child_catalogue_items(test_client):
    """
    Test deleting a catalogue category with child catalogue items.
    """
    # pylint: disable=duplicate-code

    units, _ = _post_units(test_client)

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **{
                **CATALOGUE_CATEGORY_POST_C,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_C["properties"], units
                ),
            },
        },
    )
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
    }
    # pylint: enable=duplicate-code
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.delete(f"/v1/catalogue-categories/{catalogue_category['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be deleted"


def test_get_catalogue_category(test_client):
    """
    Test getting a catalogue category.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    units, _ = _post_units(test_client)

    # Child
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
            "parent_id": parent_catalogue_category["id"],
        },
    )

    response = test_client.get(f"/v1/catalogue-categories/{response.json()['id']}")
    assert response.status_code == 200
    catalogue_category = response.json()
    assert catalogue_category == {
        **CATALOGUE_CATEGORY_POST_B_EXPECTED,
        "parent_id": parent_catalogue_category["id"],
        "properties": add_ids_to_properties(
            catalogue_category["properties"],
            CATALOGUE_CATEGORY_POST_B_EXPECTED["properties"],
        ),
    }


def test_get_catalogue_category_with_invalid_id(test_client):
    """
    Test getting a catalogue category with an invalid ID.
    """
    response = test_client.get("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_get_catalogue_category_with_non_existent_id(test_client):
    """
    Test getting a catalogue category with a non-existent ID.
    """
    response = test_client.get(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_get_catalogue_categories(test_client):
    """
    Test getting catalogue categories.
    """
    category_a, category_b, category_c = _post_catalogue_categories(test_client)

    response = test_client.get("/v1/catalogue-categories")

    assert response.status_code == 200
    assert response.json() == [category_a, category_b, category_c]


def test_get_catalogue_categories_with_parent_id_filter(test_client):
    """
    Test getting catalogue categories based on the provided parent_id filter.
    """
    _, category_b, _ = _post_catalogue_categories(test_client)

    response = test_client.get("/v1/catalogue-categories", params={"parent_id": category_b["parent_id"]})

    assert response.status_code == 200
    assert response.json() == [category_b]


def test_get_catalogue_categories_with_null_parent_id_filter(test_client):
    """
    Test getting catalogue categories when given a parent_id filter of "null"
    """
    category_a, _, category_c = _post_catalogue_categories(test_client)

    response = test_client.get("/v1/catalogue-categories", params={"parent_id": "null"})

    assert response.status_code == 200
    assert response.json() == [category_a, category_c]


def test_get_catalogue_categories_with_parent_id_filter_no_matching_results(test_client):
    """
    Test getting catalogue categories based on the provided parent_id filter when there is no matching
    results in the database.
    """
    _, _, _ = _post_catalogue_categories(test_client)

    response = test_client.get("/v1/catalogue-categories", params={"parent_id": str(ObjectId())})

    assert response.status_code == 200
    assert response.json() == []


def test_get_catalogue_categories_with_invalid_parent_id_filter(test_client):
    """
    Test getting catalogue categories when given an invalid parent_id filter
    """
    response = test_client.get("/v1/catalogue-categories", params={"parent_id": "invalid"})

    assert response.status_code == 200
    assert response.json() == []


def test_get_catalogue_category_breadcrumbs_when_no_parent(test_client):
    """
    Test getting the breadcrumbs for a catalogue category with no parents
    """

    units, _ = _post_units(test_client)

    (category_c, *_) = _post_nested_catalogue_categories(
        test_client,
        [
            {
                **CATALOGUE_CATEGORY_POST_C,
                "properties": replace_unit_values_with_ids_in_properties(
                    CATALOGUE_CATEGORY_POST_C["properties"], units
                ),
            }
        ],
    )

    response = test_client.get(f"/v1/catalogue-categories/{category_c['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {"trail": [[category_c["id"], category_c["name"]]], "full_trail": True}


def test_get_catalogue_category_when_trail_length_less_than_maximum(test_client):
    """
    Test getting the breadcrumbs for a catalogue category with less than the the maximum trail length
    """
    categories = _post_n_catalogue_categories(test_client, BREADCRUMBS_TRAIL_MAX_LENGTH - 1)

    # Get breadcrumbs for last added
    response = test_client.get(f"/v1/catalogue-categories/{categories[-1]['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {
        "trail": [[category["id"], category["name"]] for category in categories],
        "full_trail": True,
    }


def test_get_catalogue_category_when_trail_length_maximum(test_client):
    """
    Test getting the breadcrumbs for a catalogue category with the maximum trail length
    """
    categories = _post_n_catalogue_categories(test_client, BREADCRUMBS_TRAIL_MAX_LENGTH)

    # Get breadcrumbs for last added
    response = test_client.get(f"/v1/catalogue-categories/{categories[-1]['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {
        "trail": [[category["id"], category["name"]] for category in categories],
        "full_trail": True,
    }


def test_get_catalogue_category_when_trail_length_greater_than_maximum(test_client):
    """
    Test getting the breadcrumbs for a catalogue category with greater than the the maximum trail length
    """
    categories = _post_n_catalogue_categories(test_client, BREADCRUMBS_TRAIL_MAX_LENGTH + 1)

    # Get breadcrumbs for last added
    response = test_client.get(f"/v1/catalogue-categories/{categories[-1]['id']}/breadcrumbs")

    assert response.status_code == 200
    assert response.json() == {
        "trail": [[category["id"], category["name"]] for category in categories[1:]],
        "full_trail": False,
    }


def test_get_catalogue_category_breadcrumbs_with_invalid_id(test_client):
    """
    Test getting the breadcrumbs for a catalogue category when the given id is invalid
    """
    response = test_client.get("/v1/catalogue-categories/invalid/breadcrumbs")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_get_catalogue_category_breadcrumbs_with_non_existent_id(test_client):
    """
    Test getting the breadcrumbs for a non-existent catalogue category
    """
    response = test_client.get(f"/v1/catalogue-categories/{str(ObjectId())}/breadcrumbs")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_partial_update_catalogue_category_change_name(test_client):
    """
    Test changing the name of a catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    catalogue_category_patch = {"name": "Category B"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **CATALOGUE_CATEGORY_POST_A_EXPECTED,
        **catalogue_category_patch,
        "code": "category-b",
    }


def test_partial_update_catalogue_category_change_capitalisation_of_name(test_client):
    """
    Test changing the capitalisation of the name of a catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    catalogue_category_patch = {"name": "CaTeGoRy A"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **CATALOGUE_CATEGORY_POST_A_EXPECTED,
        **catalogue_category_patch,
    }


def test_partial_update_catalogue_category_change_name_duplicate(test_client):
    """
    Test changing the name of a catalogue category to a name that already exists.
    """
    test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    units, _ = _post_units(test_client)

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
        },
    )

    catalogue_category_patch = {"name": "Category A"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_partial_update_catalogue_category_change_valid_parameters_when_has_child_catalogue_categories(test_client):
    """
    Test changing valid parameters of a catalogue category which has child catalogue categories.
    """
    category_a, _, _ = _post_catalogue_categories(test_client)

    catalogue_category_patch = {"name": "Category D"}
    response = test_client.patch(f"/v1/catalogue-categories/{category_a['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **CATALOGUE_CATEGORY_POST_A_EXPECTED,
        **catalogue_category_patch,
        "code": "category-d",
    }


def test_partial_update_catalogue_category_change_valid_when_has_child_catalogue_items(test_client):
    """
    Test changing valid parameters of a catalogue category which has child catalogue items.
    """

    units, _ = _post_units(test_client)

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_C,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_B["properties"], units),
        },
    )

    catalogue_category = response.json()
    catalogue_item_post = {**CATALOGUE_ITEM_POST_A, "catalogue_category_id": catalogue_category["id"]}
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"name": "Category D"}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **CATALOGUE_CATEGORY_POST_C_EXPECTED,
        **catalogue_category_patch,
        "code": "category-d",
        "properties": add_ids_to_properties(
            catalogue_category["properties"],
            CATALOGUE_CATEGORY_POST_C_EXPECTED["properties"],
        ),
    }


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf(test_client):
    """
    Test changing a catalogue category from non-leaf to leaf.
    """

    _, unit_value_to_id = _post_units(test_client)

    catalogue_category_patch = {
        "is_leaf": True,
        "properties": [
            {
                "name": "Property A",
                "type": "number",
                "unit_id": unit_value_to_id["mm"],
                "unit": "mm",
                "mandatory": False,
                "allowed_values": None,
            }
        ],
    }

    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    catalogue_category = response.json()
    assert catalogue_category == {
        **catalogue_category_post,
        **{
            **catalogue_category_patch,
            "properties": add_ids_to_properties(
                catalogue_category["properties"],
                catalogue_category_patch["properties"],
            ),
        },
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_without_properties(test_client):
    """
    Test changing a catalogue category from non-leaf to leaf without supplying any properties.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"is_leaf": True}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "id": ANY,
        "properties": [],
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_has_child_catalogue_categories(test_client):
    """
    Test changing a catalogue category with child catalogue categories from non-leaf to leaf.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]
    catalogue_category_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {
        "is_leaf": True,
        "properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf(test_client):
    """
    Test changing a catalogue category from leaf to non-leaf.
    """
    _, unit_value_to_id = _post_units(test_client)
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": [
            {
                "name": "Property A",
                "type": "number",
                "unit": "mm",
                "unit_id": unit_value_to_id["mm"],
                "mandatory": False,
            }
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"is_leaf": False}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "id": ANY,
        "properties": [],
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_has_child_catalogue_items(test_client):
    """
    Test changing a catalogue category with child catalogue items from leaf to non-leaf.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
    }
    # pylint: enable=duplicate-code
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"is_leaf": False}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category['id']}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_with_properties(test_client):
    """
    Test changing a catalogue category from leaf to non-leaf while also changing its properties.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {
        "is_leaf": False,
        "properties": [{"name": "Property B", "type": "boolean", "mandatory": True}],
    }
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "id": ANY,
        "properties": [],
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_parent_id(test_client):
    """
    Test moving a catalogue category to another parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]

    units, _ = _post_units(test_client)

    catalogue_category_post = {
        "name": "Category B",
        "is_leaf": True,
        "parent_id": catalogue_category_a_id,
        "properties": replace_unit_values_with_ids_in_properties([CATALOGUE_CATEGORY_POST_B["properties"][0]], units),
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]

    catalogue_category_patch = {"parent_id": None}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 200
    catalogue_category = response.json()
    assert catalogue_category == {
        **{
            **catalogue_category_post,
            "properties": add_ids_to_properties(
                catalogue_category["properties"],
                [CATALOGUE_CATEGORY_POST_B_EXPECTED["properties"][0]],
            ),
        },
        **catalogue_category_patch,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "id": ANY,
        "code": "category-b",
    }


def test_partial_update_catalogue_category_change_parent_id_to_child_id(test_client):
    """
    Test updating a catalogue categories's parent_id to be the id of one of its children
    """
    nested_categories = _post_n_catalogue_categories(test_client, 4)

    # Attempt to move first into one of its children
    response = test_client.patch(
        f"/v1/catalogue-categories/{nested_categories[0]['id']}", json={"parent_id": nested_categories[3]["id"]}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot move a catalogue category to one of its own children"


def test_partial_update_catalogue_category_change_parent_id_has_child_catalogue_categories(test_client):
    """
    Test moving a catalogue category with child categories to another parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]
    catalogue_category_b_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_a_id}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_b_post)
    catalogue_category_b_id = response.json()["id"]
    catalogue_category_post = {"name": "Category C", "is_leaf": False, "parent_id": catalogue_category_b_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": None}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_b_post,
        **catalogue_category_patch,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "properties": [],
        "id": ANY,
        "code": "category-b",
    }


def test_partial_update_catalogue_category_change_parent_id_has_child_catalogue_items(test_client):
    """
    Test moving a catalogue category with child catalogue items to another parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]
    catalogue_category_b_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_b_post)
    catalogue_category_b_id = response.json()["id"]
    catalogue_category_post = {
        "name": "Category C",
        "is_leaf": True,
        "parent_id": catalogue_category_b_id,
        "properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_c_id = response.json()["id"]

    catalogue_item_post = {**CATALOGUE_ITEM_POST_A, "catalogue_category_id": catalogue_category_c_id}
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"parent_id": catalogue_category_a_id}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_b_post,
        **catalogue_category_patch,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "properties": [],
        "id": ANY,
        "code": "category-b",
    }


def test_partial_update_catalogue_category_change_parent_id_duplicate_name(test_client):
    """
    Test moving a catalogue category to another parent catalogue category in which a category with the same name already
    exists.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
    catalogue_category_c_id = response.json()["id"]

    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]

    catalogue_category_post = {"name": "Category C", "is_leaf": False, "parent_id": catalogue_category_b_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": catalogue_category_b_id}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_c_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_partial_update_catalogue_category_change_parent_id_leaf_parent_catalogue_category(test_client):
    """
    Test moving a catalogue category to a leaf parent catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
    catalogue_category_c_id = response.json()["id"]

    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]

    catalogue_category_patch = {"parent_id": catalogue_category_c_id}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue category to a leaf parent catalogue category is not allowed"


def test_partial_update_catalogue_category_change_parent_id_invalid_id(test_client):
    """
    Test changing the parent ID of a catalogue category to an invalid ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": "invalid"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category does not exist"


def test_partial_update_catalogue_category_change_parent_id_non_existent_id(test_client):
    """
    Test changing the parent ID of a catalogue category to a non-existent ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": str(ObjectId())}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category does not exist"


def test_partial_update_catalogue_category_add_property(test_client):
    """
    Test adding a property.
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {
            "name": "Property A",
            "type": "number",
            "unit": "mm",
            "unit_id": unit_value_to_id["mm"],
            "mandatory": False,
            "allowed_values": None,
        }
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties.append({"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None})
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    properties[1]["unit"] = None
    catalogue_category = response.json()
    assert catalogue_category == {
        **catalogue_category_post,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_remove_property(test_client):
    """
    Test removing a property.
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {
            "name": "Property A",
            "type": "number",
            "unit": "mm",
            "unit_id": unit_value_to_id["mm"],
            "mandatory": False,
            "allowed_values": None,
        },
        {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties.pop(0)
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    properties[0]["unit"] = None
    catalogue_category = response.json()
    assert catalogue_category == {
        **catalogue_category_post,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_modify_property(test_client):
    """
    Test modifying a property.
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {
            "name": "Property A",
            "type": "number",
            "unit": "mm",
            "unit_id": unit_value_to_id["mm"],
            "mandatory": False,
            "allowed_values": None,
        },
        {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties[1]["name"] = "Property C"
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    properties[1]["unit"] = None
    catalogue_category = response.json()
    assert catalogue_category == {
        **catalogue_category_post,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_modify_property_to_have_allowed_values_list(test_client):
    """
    Test modifying properties to have a list of allowed values
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_value_to_id["mm"], "mandatory": False},
        {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
    ]
    catalogue_category_post = {
        **CATALOGUE_CATEGORY_POST_B,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties[0]["allowed_values"] = {"type": "list", "values": [2, 4, 6]}
    properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green"]}
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    catalogue_category = response.json()
    assert catalogue_category == {
        **catalogue_category_post,
        **CREATED_MODIFIED_VALUES_EXPECTED,
        "properties": add_ids_to_properties(catalogue_category["properties"], catalogue_category_patch["properties"]),
        "id": ANY,
        "code": "category-b",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_number(
    test_client,
):
    """
    Test modifying properties to have a number property containing an allowed_values list with an
    invalid number
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_value_to_id["mm"], "mandatory": False},
        {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
    ]
    catalogue_category_post = {
        **CATALOGUE_CATEGORY_POST_B,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties[0]["allowed_values"] = {"type": "list", "values": [2, "4", 6]}
    properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green"]}
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself"
    )


def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_string(
    test_client,
):
    """
    Test modifying properties to have a string property containing an allowed_values list with an
    invalid string
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "unit_id": unit_value_to_id["mm"], "mandatory": False},
        {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
    ]
    catalogue_category_post = {
        **CATALOGUE_CATEGORY_POST_B,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties[0]["allowed_values"] = {"type": "list", "values": [2, 4, 6]}
    properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green", 6]}
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' must only contain values of the same type as the property itself"
    )


def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_duplicate_number(
    test_client,
):
    """
    Test modifying properties to have a number property containing an allowed_values list with a
    duplicate number value
    """
    properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
    ]
    catalogue_category_post = {
        **CATALOGUE_CATEGORY_POST_B,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties[0]["allowed_values"] = {"type": "list", "values": [42, 10.2, 12, 42]}
    properties[1]["allowed_values"] = {"type": "list", "values": ["red", "green"]}
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' contains a duplicate value: 42"
    )


def test_partial_update_catalogue_category_modify_property_to_have_invalid_allowed_values_list_duplicate_string(
    test_client,
):
    """
    Test modifying properties to have a string property containing an allowed_values list with a
    duplicate string value
    """
    properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "string", "unit": None, "mandatory": False},
    ]
    catalogue_category_post = {
        **CATALOGUE_CATEGORY_POST_B,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    properties[0]["allowed_values"] = {"type": "list", "values": [2, 4, 6]}
    properties[1]["allowed_values"] = {
        "type": "list",
        "values": ["value1", "value2", "value3", "value2"],
    }
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, allowed_values of type 'list' contains a duplicate value: value2"
    )


def test_partial_update_catalogue_category_change_properties_has_child_catalogue_items(test_client):
    """
    Test changing the properties when a catalogue category has child catalogue items.
    """
    # pylint: disable=duplicate-code

    units, _ = _post_units(test_client)
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_C,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_C["properties"], units),
        },
    )
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(catalogue_category["properties"], CATALOGUE_ITEM_POST_A["properties"]),
    }
    # pylint: enable=duplicate-code
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"properties": [{"name": "Property B", "type": "string", "mandatory": False}]}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category['id']}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


def test_partial_update_catalogue_category_invalid_unit_id(test_client):
    """
    Test modifying a property when there is an invalid unit ID.
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {
            "name": "Property A",
            "type": "number",
            "unit": "mm",
            "unit_id": unit_value_to_id["mm"],
            "mandatory": False,
            "allowed_values": None,
        },
        {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    # invalid unit data
    unit_cm = {
        "id": "invalid",
        "value": "cm",
        "code": "cm",
        **CREATED_MODIFIED_VALUES_EXPECTED,
    }
    properties[0]["unit_id"] = unit_cm["id"]
    properties[0]["unit"] = unit_cm["value"]
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified unit does not exist"


def test_partial_update_catalogue_category_non_existent_unit_id(test_client):
    """
    Test modifying a property when there is an non existent unit ID.
    """

    _, unit_value_to_id = _post_units(test_client)

    properties = [
        {
            "name": "Property A",
            "type": "number",
            "unit": "mm",
            "unit_id": unit_value_to_id["mm"],
            "mandatory": False,
            "allowed_values": None,
        },
        {"name": "Property B", "type": "boolean", "mandatory": True, "allowed_values": None},
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "properties": properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    # invalid unit data
    unit_cm = {
        "id": str(ObjectId()),
        "value": "cm",
        "code": "cm",
        **CREATED_MODIFIED_VALUES_EXPECTED,
    }
    properties[0]["unit_id"] = unit_cm["id"]
    properties[0]["unit"] = unit_cm["value"]
    catalogue_category_patch = {"properties": properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified unit does not exist"


def test_partial_update_catalogue_category_invalid_id(test_client):
    """
    Test updating a catalogue category with an invalid ID.
    """
    catalogue_category_patch = {"name": "Category A", "is_leaf": False}

    response = test_client.patch("/v1/catalogue-categories/invalid", json=catalogue_category_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_partial_update_catalogue_category_non_existent_id(test_client):
    """
    Test updating a catalogue category with a non-existent ID.
    """
    catalogue_category_patch = {"name": "Category A", "is_leaf": False}

    response = test_client.patch(f"/v1/catalogue-categories/{str(ObjectId())}", json=catalogue_category_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category not found"


def test_partial_update_catalogue_items_to_have_duplicate_property_names(test_client):
    """
    Test updating a catalogue category to have duplicate property names
    """

    units, unit_value_to_id = _post_units(test_client)
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_C,
            "properties": replace_unit_values_with_ids_in_properties(CATALOGUE_CATEGORY_POST_C["properties"], units),
        },
    )
    catalogue_category_id = response.json()["id"]

    catalogue_category_patch = {
        "properties": [
            {"name": "Duplicate", "type": "number", "unit_id": unit_value_to_id["mm"], "mandatory": False},
            {"name": "Duplicate", "type": "boolean", "unit": None, "mandatory": True},
        ]
    }

    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == (
        f"Duplicate property name: {catalogue_category_patch['properties'][0]['name']}"
    )
