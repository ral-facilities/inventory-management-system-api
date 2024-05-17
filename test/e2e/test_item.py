# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue item router.
"""
from test.conftest import add_ids_to_properties
from test.e2e.mock_schemas import (
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    CATALOGUE_ITEM_POST_ALLOWED_VALUES,
    CREATED_MODIFIED_VALUES_EXPECTED,
    ITEM_POST_ALLOWED_VALUES,
    ITEM_POST_ALLOWED_VALUES_EXPECTED,
    SYSTEM_POST_A,
    SYSTEM_POST_B,
    USAGE_STATUS_POST_A,
)
from test.e2e.test_unit import UNIT_POST_A, UNIT_POST_B
from unittest.mock import ANY

from bson import ObjectId

# pylint: disable=duplicate-code
CATALOGUE_CATEGORY_POST_A = {
    "name": "Category A",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
        {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
        {"name": "Property D", "type": "string", "mandatory": False},
    ],
}

CATALOGUE_ITEM_POST_A = {
    "name": "Catalogue Item A",
    "description": "This is Catalogue Item A",
    "cost_gbp": 129.99,
    "days_to_replace": 2.0,
    "drawing_link": "https://drawing-link.com/",
    "item_model_number": "abc123",
    "is_obsolete": False,
    "properties": [
        {"name": "Property A", "value": 20},
        {"name": "Property B", "value": False},
        {"name": "Property C", "value": "20x15x10"},
    ],
}

MANUFACTURER_POST = {
    "name": "Manufacturer A",
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

ITEM_POST = {
    "is_defective": False,
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "serial_number": "xyz123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
    "properties": [{"name": "Property A", "value": 21}],
}

ITEM_POST_EXPECTED = {
    **ITEM_POST,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "purchase_order_number": None,
    "asset_number": None,
    "properties": [
        {"name": "Property A", "value": 21, "unit": "mm"},
        {"name": "Property B", "value": False, "unit": None},
        {"name": "Property C", "value": "20x15x10", "unit": "cm"},
        {"name": "Property D", "value": None, "unit": None},
    ],
}


def test_create_item(test_client):
    """
    Test creating an item.
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: disable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)
    # pylint: enable=duplicate-code

    assert response.status_code == 201

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_EXPECTED["properties"],
        ),
    }


def test_create_item_with_invalid_catalogue_item_id(test_client):
    """
    Test creating an item with an invalid catalogue item ID.
    """
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": "invalid",
        "system_id": str(ObjectId()),
        "usage_status_id": str(ObjectId()),
        "properties": add_ids_to_properties(None, ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue item does not exist"


def test_create_item_with_non_existent_catalogue_item_id(test_client):
    """
    Test creating an item with a non-existent catalogue item ID.
    """
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": str(ObjectId()),
        "system_id": str(ObjectId()),
        "usage_status_id": str(ObjectId()),
        "properties": add_ids_to_properties(None, ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue item does not exist"


def test_create_item_with_invalid_system_id(test_client):
    """
    Test creating an item with an invalid system ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": "invalid",
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified system does not exist"


def test_create_item_with_non_existent_system_id(test_client):
    """
    Test creating an item with a non-existent system ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": str(ObjectId()),
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified system does not exist"


def test_create_with_missing_existing_properties(test_client):
    """Test creating an item when not all properties defined in the catalogue item are supplied"""
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "25x10x5"},
            ],
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 201

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20, "unit": "mm"},
                {"name": "Property B", "unit": None, "value": False},
                {"name": "Property C", "unit": "cm", "value": "25x10x5"},
                {"name": "Property D", "unit": None, "value": None},
            ],
        ),
    }


def test_create_with_mandatory_properties_given_none(test_client):
    """
    Test creating an item when a mandatory property is given a value of None
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property B", "value": None},
                {"name": "Property C", "value": None},
            ],
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/items", json=item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert response.json()["detail"] == f"Mandatory catalogue item property with ID '{prop_id}' cannot be None."
    # pylint: enable=duplicate-code


def test_create_with_non_mandatory_properties_given_none(test_client):
    """
    Test creating an item when non-mandatory properties are given a value of None
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": None},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "25x10x5"},
                {"name": "Property D", "value": None},
            ],
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 201
    item = response.json()
    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "unit": "mm", "value": None},
                {"name": "Property B", "unit": None, "value": False},
                {"name": "Property C", "unit": "cm", "value": "25x10x5"},
                {"name": "Property D", "unit": None, "value": None},
            ],
        ),
    }


def test_create_item_without_properties(test_client):
    """
    Testing creating an item without properties.
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
    }
    # pylint: enable=duplicate-code
    del item_post["properties"]
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 201

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 20, "unit": "mm"}] + ITEM_POST_EXPECTED["properties"][-3:],
        ),
    }


def test_create_item_with_invalid_usage_status_id(test_client):
    """
    Test creating an item with invalid usage status.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": "Invalid",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property C", "value": True}],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified usage status does not exist"


def test_create_item_with_non_existent_usage_status_id(test_client):
    """
    Test creating an item with non existent usage status.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": str(ObjectId()),
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property C", "value": True}],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified usage status does not exist"


def test_create_item_with_invalid_value_type_for_string_property(test_client):
    """
    Test creating an item with invalid value type for a string catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property C", "value": True}],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][2]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: string."
    )
    # pylint: enable=duplicate-code


def test_create_item_with_invalid_value_type_for_number_property(test_client):
    """
    Test creating an item with invalid value type for a number catalogue item property.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": "20"}],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: number."
    )
    # pylint: enable=duplicate-code


def test_create_item_with_invalid_value_type_for_boolean_property(test_client):
    """
    Test creating an item with invalid value type for a boolean catalogue item property.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property B", "value": "False"}],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: boolean."
    )
    # pylint: enable=duplicate-code


def test_create_item_with_allowed_values(test_client):
    """
    Test creating an item when using allowed_values in the properties.
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    units = [unit_mm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES["catalogue_item_properties"], units
            ),
        },
    )
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    # pylint: enable=duplicate-code

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST_ALLOWED_VALUES,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 201

    item = response.json()

    assert item == {
        **ITEM_POST_ALLOWED_VALUES_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_ALLOWED_VALUES_EXPECTED["properties"],
        ),
    }


def test_create_item_with_allowed_values_invalid_list_string(test_client):
    """
    Test creating an item when giving a string property a value that is not within the defined allowed_values
    list
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST_ALLOWED_VALUES,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 4},
                {"name": "Property B", "value": "blue"},
            ],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of red, green."
    )
    # pylint: enable=duplicate-code


def test_create_item_with_allowed_values_invalid_list_number(test_client):
    """
    Test creating an item when giving a number property a value that is not within the defined allowed_values
    list
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST_ALLOWED_VALUES,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 10},
                {"name": "Property B", "value": "red"},
            ],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of 2, 4, 6."
    )
    # pylint: enable=duplicate-code


def test_delete(test_client):
    """
    Test deleting an item
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }

    # pylint: enable=duplicate-code
    response = test_client.post("/v1/items", json=item_post)

    item_id = response.json()["id"]

    response = test_client.delete(f"/v1/items/{item_id}")

    assert response.status_code == 204
    response = test_client.delete(f"/v1/items/{item_id}")
    assert response.status_code == 404


def test_delete_with_invalid_id(test_client):
    """
    Test deleting an item with an invalid ID.
    """
    response = test_client.delete("v1/items/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_delete_catalogue_item_with_nonexistent_id(test_client):
    """
    Test deleting an item with a nonexistent ID.
    """
    response = test_client.delete(f"/v1/items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_get_item(test_client):
    """
    Test getting an item by its ID.
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    # pylint: enable=duplicate-code

    response = test_client.post("/v1/items", json=item_post)

    item_id = response.json()["id"]
    response = test_client.get(f"/v1/items/{item_id}")

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_EXPECTED["properties"],
        ),
    }


def test_get_item_with_nonexistent_id(test_client):
    """
    Test getting an item with a nonexistent_id
    """
    response = test_client.get(f"/v1/items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "An item with such ID was not found"


def test_get_item_with_invalid_id(test_client):
    """
    Test getting an item with a nonexistent_id
    """
    response = test_client.get("/v1/items/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "An item with such ID was not found"


def test_get_items(test_client):
    """
    Test getting items
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id_a = response.json()["id"]
    response = test_client.post("/v1/systems", json=SYSTEM_POST_B)
    system_id_b = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post_a = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id_a,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }

    item_post_b = {**item_post_a, "system_id": system_id_b}

    test_client.post("/v1/items", json=item_post_a)
    test_client.post("/v1/items", json=item_post_b)

    response = test_client.get("/v1/items")

    assert response.status_code == 200

    items = response.json()

    properties_expected = add_ids_to_properties(
        catalogue_category["catalogue_item_properties"],
        ITEM_POST_EXPECTED["properties"],
    )
    assert items == [
        {
            **ITEM_POST_EXPECTED,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id_a,
            "usage_status_id": usage_status_id,
            "usage_status": "New",
            "properties": properties_expected,
        },
        {
            **ITEM_POST_EXPECTED,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id_b,
            "usage_status_id": usage_status_id,
            "usage_status": "New",
            "properties": properties_expected,
        },
    ]


def test_get_items_with_system_id_filters(test_client):
    """
    Test getting items with system id filter
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post_a = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": None,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }

    item_post_b = {**item_post_a, "system_id": system_id}

    test_client.post("/v1/items", json=item_post_a)
    test_client.post("/v1/items", json=item_post_b)

    response = test_client.get("/v1/items", params={"system_id": system_id})

    assert response.status_code == 200

    items = response.json()

    assert items == [
        {
            **ITEM_POST_EXPECTED,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
            "usage_status_id": usage_status_id,
            "usage_status": "New",
            "properties": add_ids_to_properties(
                catalogue_category["catalogue_item_properties"],
                ITEM_POST_EXPECTED["properties"],
            ),
        }
    ]


def test_get_items_with_catalogue_id_filters(test_client):
    """
    Test getting items with catalogue item id filter
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code

    # pylint: disable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    test_client.post("/v1/items", json=item_post)
    # pylint: enable=duplicate-code

    response = test_client.get("/v1/items", params={"catalogue_item_id": catalogue_item_id})

    assert response.status_code == 200

    items = response.json()

    assert items == [
        {
            **ITEM_POST_EXPECTED,
            "catalogue_item_id": catalogue_item_id,
            "system_id": system_id,
            "usage_status_id": usage_status_id,
            "usage_status": "New",
            "properties": add_ids_to_properties(
                catalogue_category["catalogue_item_properties"],
                ITEM_POST_EXPECTED["properties"],
            ),
        }
    ]


def test_get_items_with_no_matching_filters(test_client):
    """
    Test getting items with neither filter having matching results
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    # pylint: disable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    # pylint: enable=duplicate-code

    test_client.post("/v1/items", json=item_post)
    test_client.post("/v1/items", json=item_post)

    response = test_client.get(
        "/v1/items",
        params={"system_id": str(ObjectId()), "catalogue_item_id": str(ObjectId())},
    )

    assert response.status_code == 200

    items = response.json()

    assert not items


def test_get_items_with_invalid_system_id_filter(test_client):
    """
    Test getting items with an invalid system id filter
    """
    response = test_client.get("/v1/items", params={"system_id": "Invalid"})

    assert response.status_code == 200
    assert response.json() == []


def test_get_items_with_invalid_catalogue_item_id_filter(test_client):
    """
    Test getting items with an invalid catalogue item id filter
    """
    response = test_client.get("/v1/items", params={"catalogue_item_id": "Invalid"})

    assert response.status_code == 200
    assert response.json() == []


def test_partial_update_item(test_client):
    """
    Test changing 'usage_status' and 'is_defective' in an item
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {"usage_status": "Used", "is_defective": True}
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        **item_patch,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_EXPECTED["properties"],
        ),
    }


def test_partial_update_item_invalid_id(test_client):
    """
    Test updating an item with an invalid ID.
    """

    item_patch = {"usage_status_id": str(ObjectId()), "is_defective": True}

    response = test_client.patch("/v1/items/invalid", json=item_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_partial_update_item_non_existent_id(test_client):
    """
    Test updating an item with a non-existent ID.
    """
    item_patch = {"usage_status_id": str(ObjectId()), "is_defective": True}

    response = test_client.patch(f"/v1/items/{str(ObjectId())}", json=item_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_partial_update_change_catalogue_item_id(test_client):
    """
    Test moving an item to another catalogue item
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {"catalogue_item_id": str(ObjectId())}
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot change the catalogue item of an item"


def test_partial_update_change_system_id(test_client):
    """
    Test changing the system ID of an item
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id_a = response.json()["id"]

    response = test_client.post("/v1/systems", json=SYSTEM_POST_B)
    system_id_b = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id_a,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {"system_id": system_id_b}
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        **item_patch,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id_b,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_EXPECTED["properties"],
        ),
    }


def test_partial_update_change_non_existent_system_id(test_client):
    """
    Test updating system ID which is non-existent
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {"system_id": str(ObjectId())}
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified system does not exist"


def test_partial_update_change_non_existent_usage_status_id(test_client):
    """
    Test updating usage status ID which is non-existent
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {"usage_status_id": str(ObjectId())}
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified usage status does not exist"


def test_partial_update_change_invalid_usage_status_id(test_client):
    """
    Test updating usage status ID which is invalid
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {"usage_status_id": "invalid"}
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified usage status does not exist"


def test_partial_update_property_values(test_client):
    """
    Test updating property values
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 12},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "20x15x10"},
            ],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 12, "unit": "mm"}] + ITEM_POST_EXPECTED["properties"][-3:],
        ),
    }


def test_partial_update_property_values_with_mandatory_properties_given_none(
    test_client,
):
    """
    Test updating a item's mandatory properties to have a value of None
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property B", "value": None},
                {"name": "Property C", "value": None},
            ],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert response.json()["detail"] == f"Mandatory catalogue item property with ID '{prop_id}' cannot be None."
    # pylint: enable=duplicate-code


def test_partial_update_property_values_with_non_mandatory_properties_given_none(
    test_client,
):
    """
    Test updating a item's mandatory properties to have a value of None
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": None},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "20x15x10"},
                {"name": "Property D", "value": None},
            ],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "unit": "mm", "value": None},
                {"name": "Property B", "unit": None, "value": False},
                {"name": "Property C", "unit": "cm", "value": "20x15x10"},
                {"name": "Property D", "unit": None, "value": None},
            ],
        ),
    }


def test_partial_update_property_values_with_allowed_values(test_client):
    """
    Test updating property values when using allowed_values in the catalogue category properties
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    units = [unit_mm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_ALLOWED_VALUES["catalogue_item_properties"], units
            ),
        },
    )
    # pylint: enable=duplicate-code
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST_ALLOWED_VALUES,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 2},
                {"name": "Property B", "value": "red"},
            ],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "unit": "mm", "value": 2},
                {"name": "Property B", "value": "red", "unit": None},
            ],
        ),
    }


def test_partial_update_property_values_with_allowed_values_invalid_list_string(
    test_client,
):
    """
    Test updating property values when giving a string property a value that is not within the defined
    allowed_values
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST_ALLOWED_VALUES,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property B", "value": "blue"}],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of red, green."
    )
    # pylint: enable=duplicate-code


def test_partial_update_property_values_with_allowed_values_invalid_list_number(
    test_client,
):
    """
    Test updating property values when giving a number property a value that is not within the defined
    allowed_values
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST_ALLOWED_VALUES,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            ITEM_POST_ALLOWED_VALUES["properties"],
        ),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 10}],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of 2, 4, 6."
    )
    # pylint: enable=duplicate-code


def test_partial_update_with_missing_existing_properties(test_client):
    """
    Test updating an item when not all properties defined in the catalogue item are supplied
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]

    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_A,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "25x10x5"},
            ],
        ),
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    assert response.status_code == 200

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "usage_status": "New",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20, "unit": "mm"},
                {"name": "Property B", "unit": None, "value": False},
                {"name": "Property C", "unit": "cm", "value": "25x10x5"},
                {"name": "Property D", "unit": None, "value": None},
            ],
        ),
    }


def test_partial_update_item_change_value_for_string_property_invalid_type(test_client):
    """
    Test changing the value of a string item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property C", "value": 21}],
        )
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][2]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: string."
    )
    # pylint: enable=duplicate-code


def test_partial_update_item_change_value_for_number_property_invalid_type(test_client):
    """
    Test changing the value of a string item property to an invalid type.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": "21"}],
        )
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: number."
    )
    # pylint: enable=duplicate-code


def test_partial_update_item_change_value_for_boolean_property_invalid_type(
    test_client,
):
    """
    Test changing the value of a string item property to an invalid type.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]
    # pylint: enable=duplicate-code

    # pylint: disable=duplicate-code
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            CATALOGUE_ITEM_POST_A["properties"],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    # pylint: enable=duplicate-code
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    response = test_client.post("/v1/items", json=item_post)

    item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property B", "value": 21}],
        )
    }
    response = test_client.patch(f"/v1/items/{response.json()['id']}", json=item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: boolean."
    )
    # pylint: enable=duplicate-code
