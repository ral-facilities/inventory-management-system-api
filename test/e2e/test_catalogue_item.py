# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue item router.
"""
from test.conftest import add_ids_to_properties
from test.e2e.mock_schemas import (
    CATALOGUE_CATEGORY_POST_ALLOWED_VALUES,
    CATALOGUE_ITEM_POST_ALLOWED_VALUES,
    CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED,
    CREATED_MODIFIED_VALUES_EXPECTED,
    SYSTEM_POST_A,
    USAGE_STATUS_POST_A,
    USAGE_STATUS_POST_B,
)
from test.e2e.test_item import ITEM_POST
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
    ],
}
# pylint: enable=duplicate-code

CATALOGUE_CATEGORY_POST_B = {
    "name": "Category B",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "boolean", "mandatory": True},
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

CATALOGUE_ITEM_POST_A_EXPECTED = {
    **CATALOGUE_ITEM_POST_A,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "cost_to_rework_gbp": None,
    "days_to_rework": None,
    "drawing_number": None,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "notes": None,
    "properties": [
        {"name": "Property A", "value": 20, "unit": "mm"},
        {"name": "Property B", "value": False, "unit": None},
        {"name": "Property C", "value": "20x15x10", "unit": "cm"},
    ],
}

CATALOGUE_ITEM_POST_B = {
    "name": "Catalogue Item B",
    "description": "This is Catalogue Item B",
    "cost_gbp": 300.00,
    "cost_to_rework_gbp": 120.99,
    "days_to_replace": 1.5,
    "days_to_rework": 3.0,
    "drawing_number": "789xyz",
    "is_obsolete": False,
    "notes": "Some extra information",
    "properties": [{"name": "Property A", "value": True}],
}
# pylint: enable=duplicate-code

CATALOGUE_ITEM_POST_B_EXPECTED = {
    **CATALOGUE_ITEM_POST_B,
    **CREATED_MODIFIED_VALUES_EXPECTED,
    "id": ANY,
    "drawing_link": None,
    "item_model_number": None,
    "obsolete_reason": None,
    "obsolete_replacement_catalogue_item_id": None,
    "properties": [{"name": "Property A", "value": True, "unit": None}],
}


def test_create_catalogue_item(test_client):
    """
    Test creating a catalogue item.
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

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }

    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
        ),
    }


def test_create_catalogue_item_with_invalid_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with an invalid catalogue category id.
    """
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": "invalid",
        "manufacturer_id": str(ObjectId()),
        "properties": add_ids_to_properties(None, CATALOGUE_ITEM_POST_A["properties"]),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category does not exist"


def test_create_catalogue_item_with_non_existent_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with a non-existent catalogue category id.
    """
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": str(ObjectId()),
        "manufacturer_id": str(ObjectId()),
        "properties": add_ids_to_properties(None, CATALOGUE_ITEM_POST_A["properties"]),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category does not exist"


def test_create_catalogue_item_with_non_existent_manufacturer_id(test_client):
    """
    Test creating a catalogue item with a non-existent manufacturer id
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": response.json()["id"],
        "manufacturer_id": str(ObjectId()),
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_create_catalogue_item_with_an_invalid_manufacturer_id(test_client):
    """
    Test creating a catalogue item with an invalid manufacturer id
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": response.json()["id"],
        "manufacturer_id": "invalid",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_create_catalogue_item_in_non_leaf_catalogue_category(test_client):
    """
    Test creating a catalogue item in a non-leaf catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": response.json()["id"],
        "manufacturer_id": str(ObjectId()),
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


def test_create_catalogue_item_with_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test creating a catalogue item with an obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)
    catalogue_item_a_id = response.json()["id"]

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
        ),
    }


def test_create_catalogue_item_with_invalid_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test creating a catalogue item with an non-existent obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": "invalid",
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item does not exist"


def test_create_catalogue_item_with_non_existent_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test creating a catalogue item with an non-existent obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": str(ObjectId()),
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item does not exist"


def test_create_catalogue_item_without_properties(test_client):
    """
    Test creating a catalogue item in leaf catalogue category that does not have catalogue item properties.
    """
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "catalogue_item_properties": []}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": [],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": [],
    }


def test_create_catalogue_item_with_missing_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [CATALOGUE_ITEM_POST_A["properties"][0], CATALOGUE_ITEM_POST_A["properties"][2]],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert response.json()["detail"] == f"Missing mandatory catalogue item property with ID: '{prop_id}'"


def test_create_catalogue_item_with_mandatory_properties_given_none(test_client):
    """
    Test creating a catalogue item with mandatory catalogue item properties given as None
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                CATALOGUE_ITEM_POST_A["properties"][0],
                {**CATALOGUE_ITEM_POST_A["properties"][1], "value": None},
                {**CATALOGUE_ITEM_POST_A["properties"][2], "value": None},
            ],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert response.json()["detail"] == f"Mandatory catalogue item property with ID '{prop_id}' cannot be None."
    # pylint: enable=duplicate-code


def test_create_catalogue_item_with_missing_non_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing non-mandatory catalogue item properties.
    """

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

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"][-2:]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "unit": "mm", "value": None}, *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:]],
        ),
    }


def test_create_catalogue_item_with_non_mandatory_properties_given_none(test_client):
    """
    Test creating a catalogue item with non-mandatory catalogue item properties given as None
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
    # pylint: enable=duplicate-code

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{**CATALOGUE_ITEM_POST_A["properties"][0], "value": None}, *CATALOGUE_ITEM_POST_A["properties"][1:]],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201
    catalogue_item = response.json()
    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {**CATALOGUE_ITEM_POST_A_EXPECTED["properties"][0], "value": None},
                *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][1:],
            ],
        ),
    }


def test_create_catalogue_item_with_invalid_value_type_for_string_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a string catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": True},
            ],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][2]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: string."
    )
    # pylint: enable=duplicate-code


def test_create_catalogue_item_with_invalid_value_type_for_number_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a number catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": "20"},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "20x15x10"},
            ],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: number."
    )
    # pylint: enable=duplicate-code


def test_create_catalogue_item_with_invalid_value_type_for_boolean_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a boolean catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20},
                {"name": "Property B", "value": "False"},
                {"name": "Property C", "value": "20x15x10"},
            ],
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: boolean."
    )
    # pylint: enable=duplicate-code


def test_create_catalogue_item_with_allowed_values(test_client):
    """
    Test creating a catalogue item when using allowed_values in the properties.
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

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED["properties"]
        ),
    }


def test_create_catalogue_item_with_allowed_values_invalid_list_string(test_client):
    """
    Test creating a catalogue item when giving a string property a value that is not within
    the defined allowed_values list
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 4}, {"name": "Property B", "value": "blue"}],
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of red, green."
    )
    # pylint: enable=duplicate-code


def test_create_catalogue_item_with_allowed_values_invalid_list_number(test_client):
    """
    Test creating a catalogue item when giving a number property a value that is not within
    the defined allowed_values list
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 10}, {"name": "Property B", "value": "red"}],
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of 2, 4, 6."
    )
    # pylint: enable=duplicate-code


def test_delete_catalogue_item(test_client):
    """
    Test deleting a catalogue item.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.delete(f"/v1/catalogue-items/{catalogue_item_id}")

    assert response.status_code == 204
    response = test_client.delete(f"/v1/catalogue-items/{catalogue_item_id}")
    assert response.status_code == 404


def test_delete_catalogue_item_with_invalid_id(test_client):
    """
    Test deleting a catalogue item with an invalid ID.
    """
    response = test_client.delete("/v1/catalogue-items/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item not found"


def test_delete_catalogue_item_with_non_existent_id(test_client):
    """
    Test deleting a catalogue item with a non-existent ID.
    """
    response = test_client.delete(f"/v1/catalogue-items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item not found"


def test_delete_catalogue_item_with_child_items(test_client):
    """
    Test deleting a catalogue item with child items.
    """
    # pylint: disable=duplicate-code
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    # child
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

    response = test_client.delete(f"/v1/catalogue-items/{catalogue_item_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be deleted"


def test_get_catalogue_item(test_client):
    """
    Test getting a catalogue item.
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

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    response = test_client.get(f"/v1/catalogue-items/{catalogue_item_id}")

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item["id"] == catalogue_item_id
    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
        ),
    }


def test_get_catalogue_item_with_invalid_id(test_client):
    """
    Test getting a catalogue item with an invalid ID.
    """
    response = test_client.get("/v1/catalogue-items/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item not found"


def test_get_catalogue_item_with_non_existent_id(test_client):
    """
    Test getting a catalogue item with a non-existent ID.
    """
    response = test_client.get(f"/v1/catalogue-items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item not found"


def test_get_catalogue_items(test_client):
    """
    Test getting catalogue items.
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

    catalogue_category_a = response.json()
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_B["catalogue_item_properties"], units
            ),
        },
    )
    catalogue_category_b = response.json()
    # pylint: enable=duplicate-code

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items")

    assert response.status_code == 200

    catalogue_items = response.json()

    assert catalogue_items == [
        {
            **CATALOGUE_ITEM_POST_A_EXPECTED,
            "catalogue_category_id": catalogue_category_a["id"],
            "manufacturer_id": manufacturer_id,
            "properties": add_ids_to_properties(
                catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
            ),
        },
        {
            **CATALOGUE_ITEM_POST_B_EXPECTED,
            "catalogue_category_id": catalogue_category_b["id"],
            "manufacturer_id": manufacturer_id,
            "properties": add_ids_to_properties(
                catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
            ),
        },
    ]


def test_get_catalogue_items_with_catalogue_category_id_filter(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items", params={"catalogue_category_id": catalogue_category_b["id"]})

    assert response.status_code == 200

    catalogue_items = response.json()

    assert catalogue_items == [
        {
            **CATALOGUE_ITEM_POST_B_EXPECTED,
            "catalogue_category_id": catalogue_category_b["id"],
            "manufacturer_id": manufacturer_id,
            "properties": add_ids_to_properties(
                catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
            ),
        }
    ]


def test_get_catalogue_items_with_catalogue_category_id_filter_no_matching_results(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items", params={"catalogue_category_id": str(ObjectId())})

    assert response.status_code == 200

    catalogue_items = response.json()

    assert len(catalogue_items) == 0


def test_get_catalogue_items_with_invalid_catalogue_category_id_filter(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.get("/v1/catalogue-items", params={"catalogue_category_id": "invalid"})

    assert response.status_code == 200

    catalogue_items = response.json()

    assert len(catalogue_items) == 0


def test_partial_update_catalogue_item_when_no_child_items(test_client):
    """
    Test changing the name and description of a catalogue item when it doesn't have any child
    items
    """
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

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        **catalogue_item_patch,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_when_has_child_items(test_client):
    """
    Test updating a catalogue item which has child items.
    """
    # pylint: disable=duplicate-code
    # units
    response = test_client.post("/v1/units", json=UNIT_POST_A)
    unit_mm = response.json()

    response = test_client.post("/v1/units", json=UNIT_POST_B)
    unit_cm = response.json()

    units = [unit_mm, unit_cm]
    # Parent
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

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        **catalogue_item_patch,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_invalid_id(test_client):
    """
    Test updating a catalogue item with an invalid ID.
    """
    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}

    response = test_client.patch("/v1/catalogue-items/invalid", json=catalogue_item_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item not found"


def test_partial_update_catalogue_item_non_existent_id(test_client):
    """
    Test updating a catalogue item with a nonexistent ID.
    """
    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}

    response = test_client.patch(f"/v1/catalogue-items/{str(ObjectId())}", json=catalogue_item_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue item not found"


def test_partial_update_catalogue_item_change_catalogue_category_id(test_client):
    """
    Test moving a catalogue item to another catalogue category with the same properties without
    specifying any new properties.
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

    catalogue_category_a = response.json()
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"], units
            ),
        },
    )
    catalogue_category_b = response.json()
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_b["id"],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_change_catalogue_category_id_without_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category without supplying any catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"catalogue_category_id": catalogue_category_b_id}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Cannot move catalogue item to a category with different catalogue_item_properties without specifying the "
        "new properties"
    )


def test_partial_update_catalogue_item_change_catalogue_category_id_with_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category while supplying any new catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_b["id"],
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_change_catalogue_category_id_with_different_properties_order(test_client):
    """
    Test moving a catalogue item to another catalogue category with the same properties but in a different order
    without supplying the new catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post(
        "/v1/catalogue-categories",
        # Use the same properties but reverse the order
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "catalogue_item_properties": CATALOGUE_CATEGORY_POST_A["catalogue_item_properties"][::-1],
        },
    )
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"catalogue_category_id": catalogue_category_b_id}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Cannot move catalogue item to a category with different catalogue_item_properties without specifying the "
        "new properties"
    )


def test_partial_update_catalogue_item_change_catalogue_category_id_missing_mandatory_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category with missing mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_a["id"],
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], [CATALOGUE_ITEM_POST_B["properties"][0]]
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    prop_id = catalogue_category_a["catalogue_item_properties"][1]["id"]
    assert response.json()["detail"] == f"Missing mandatory catalogue item property with ID: '{prop_id}'"


def test_partial_update_catalogue_item_change_catalogue_category_id_missing_non_mandatory_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category with missing non-mandatory catalogue item properties.
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

    catalogue_category_a = response.json()
    response = test_client.post(
        "/v1/catalogue-categories",
        json={
            **CATALOGUE_CATEGORY_POST_B,
            "catalogue_item_properties": add_ids_to_properties(
                None, CATALOGUE_CATEGORY_POST_B["catalogue_item_properties"], units
            ),
        },
    )
    catalogue_category_b = response.json()
    # pylint: enable=duplicate-code

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_a["id"],
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"][-2:]
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"],
            [{"name": "Property A", "unit": "mm", "value": None}, *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:]],
        ),
    }


def test_partial_update_catalogue_item_change_catalogue_category_id_invalid_id(test_client):
    """
    Test changing the catalogue category ID of a catalogue item to an invalid ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "catalogue_category_id": "invalid",
        "properties": add_ids_to_properties(None, [CATALOGUE_ITEM_POST_A["properties"][0]]),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category does not exist"


def test_partial_update_catalogue_item_change_catalogue_category_id_non_existent_id(test_client):
    """
    Test changing the catalogue category ID of a catalogue item to a non-existent ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "catalogue_category_id": str(ObjectId()),
        "properties": add_ids_to_properties(None, [CATALOGUE_ITEM_POST_A["properties"][0]]),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category does not exist"


def test_partial_update_catalogue_item_change_catalogue_category_id_non_leaf_catalogue_category(test_client):
    """
    Test moving a catalogue item to a non-leaf catalogue category.
    """
    catalogue_category_post_a = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post_a)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"catalogue_category_id": catalogue_category_a_id}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


def test_partial_update_catalogue_item_change_catalogue_category_id_has_child_items(test_client):
    """
    Test moving a catalogue item with child items to another catalogue category.
    """
    # pylint: disable=duplicate-code
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_b["id"],
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]
    # child
    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "usage_status_id": usage_status_id,
        "properties": add_ids_to_properties(catalogue_category_a["catalogue_item_properties"], ITEM_POST["properties"]),
    }
    test_client.post("/v1/items", json=item_post)

    response = test_client.patch(f"/v1/catalogue-items/{catalogue_item_id}", json=catalogue_item_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test updating a catalogue item with an obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_a["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)
    catalogue_item_a_id = response.json()["id"]

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": catalogue_item_a_id}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_b["id"],
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
        "properties": add_ids_to_properties(
            catalogue_category_b["catalogue_item_properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id_invalid_id(test_client):
    """
    Test updating a catalogue item with an invalid obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": "invalid"}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item does not exist"


def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id_non_existent_id(test_client):
    """
    Test updating a catalogue item with aa non-existent obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": str(ObjectId())}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item does not exist"


def test_partial_update_catalogue_item_with_mandatory_properties_given_none(test_client):
    """
    Test updating a catalogue item's mandatory properties to have a value of None
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                CATALOGUE_ITEM_POST_A["properties"][0],
                {**CATALOGUE_ITEM_POST_A["properties"][1], "value": None},
                {**CATALOGUE_ITEM_POST_A["properties"][2], "value": None},
            ],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert response.json()["detail"] == f"Mandatory catalogue item property with ID '{prop_id}' cannot be None."
    # pylint: enable=duplicate-code


def test_partial_update_catalogue_item_with_non_mandatory_properties_given_none(test_client):
    """
    Test updating a catalogue item's non-mandatory properties to have a value of None
    """
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

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{**CATALOGUE_ITEM_POST_A["properties"][0], "value": None}, *CATALOGUE_ITEM_POST_A["properties"][1:]],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200
    catalogue_item = response.json()
    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {**CATALOGUE_ITEM_POST_A_EXPECTED["properties"][0], "value": None},
                *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][1:],
            ],
        ),
    }


def test_partial_update_catalogue_item_add_non_mandatory_property(test_client):
    """
    Test adding a non-mandatory catalogue item property and a value.
    """
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

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"][-2:]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        )
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_remove_non_mandatory_property(test_client):
    """
    Test removing a non-mandatory catalogue item property and its value..
    """
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

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"][-2:]
        )
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "unit": "mm", "value": None}, *CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:]],
        ),
    }


def test_partial_update_catalogue_item_remove_mandatory_property(test_client):
    """
    Test removing a mandatory catalogue item property and its value.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [CATALOGUE_ITEM_POST_A["properties"][0], CATALOGUE_ITEM_POST_A["properties"][2]],
        )
    }

    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert response.status_code == 422
    assert response.json()["detail"] == f"Missing mandatory catalogue item property with ID: '{prop_id}'"


def test_partial_update_catalogue_item_change_value_for_string_property_invalid_type(test_client):
    """
    Test changing the value of a string catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": True},
            ],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][2]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: string."
    )
    # pylint: enable=duplicate-code


def test_partial_update_catalogue_item_change_value_for_number_property_invalid_type(test_client):
    """
    Test changing the value of a number catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": "20"},
                {"name": "Property B", "value": False},
                {"name": "Property C", "value": "20x15x10"},
            ],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: number."
    )


def test_partial_update_catalogue_item_change_value_for_boolean_property_invalid_type(test_client):
    """
    Test changing the value of a boolean catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [
                {"name": "Property A", "value": 20},
                {"name": "Property B", "value": "False"},
                {"name": "Property C", "value": "20x15x10"},
            ],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value type for catalogue item property with ID '{prop_id}'. Expected type: boolean."
    )
    # pylint: enable=duplicate-code


def test_partial_update_catalogue_item_change_values_with_allowed_values(test_client):
    """
    Test changing the value of properties with allowed_values defined
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

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 6}, {"name": "Property B", "value": "green"}],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES_EXPECTED,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "unit": "mm", "value": 6}, {"name": "Property B", "unit": None, "value": "green"}],
        ),
    }


def test_partial_update_catalogue_item_change_value_for_invalid_allowed_values_list_string(test_client):
    """
    Test updating a catalogue item when giving a string property a value that is not within
    the defined allowed_values list
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 4}, {"name": "Property B", "value": "blue"}],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][1]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of red, green."
    )
    # pylint: enable=duplicate-code


def test_partial_update_catalogue_item_change_value_for_invalid_allowed_values_list_number(test_client):
    """
    Test updating a catalogue item when giving a number property a value that is not within
    the defined allowed_values list
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_ALLOWED_VALUES)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_ALLOWED_VALUES,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_ALLOWED_VALUES["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"],
            [{"name": "Property A", "value": 10}, {"name": "Property B", "value": "green"}],
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    # pylint: disable=duplicate-code
    assert response.status_code == 422
    prop_id = catalogue_category["catalogue_item_properties"][0]["id"]
    assert (
        response.json()["detail"]
        == f"Invalid value for catalogue item property with ID '{prop_id}'. Expected one of 2, 4, 6."
    )
    # pylint: enable=duplicate-code


def test_partial_update_catalogue_item_properties_when_has_child_items(test_client):
    """
    Test updating the properties of a catalogue item when it has child items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_d_id = response.json()["id"]

    manufacturer_e_post = {
        **MANUFACTURER,
        "name": "Manufacturer E",
    }
    response = test_client.post("/v1/manufacturers", json=manufacturer_e_post)
    manufacturer_e_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_B)
    usage_status_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_d_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: disable=duplicate-code
    # Child
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

    catalogue_item_patch = {
        "manufacturer_id": manufacturer_e_id,
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


def test_partial_update_catalogue_item_change_manufacturer_id_when_no_child_items(test_client):
    """
    Test updating the manufacturer ID of a catalogue item when it doesn't have any child items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_d_id = response.json()["id"]

    manufacturer_e_post = {
        "name": "Manufacturer E",
        "url": "http://example.com/",
        "address": {
            "address_line": "2 Example Street",
            "town": "Oxford",
            "county": "Oxfordshire",
            "country": "United Kingdom",
            "postcode": "OX1 2AB",
        },
        "telephone": "07384723948",
    }
    response = test_client.post("/v1/manufacturers", json=manufacturer_e_post)
    manufacturer_e_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_d_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "manufacturer_id": manufacturer_e_id,
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        **catalogue_item_patch,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_e_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_B_EXPECTED["properties"]
        ),
    }


def test_partial_update_catalogue_item_change_manufacturer_id_when_has_child_items(test_client):
    """
    Test updating the manufacturer ID of a catalogue item when it has child items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    response = test_client.post("/v1/usage-statuses", json=USAGE_STATUS_POST_A)
    usage_status_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    # pylint: disable=duplicate-code
    # Child
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

    catalogue_item_patch = {
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_A["properties"]
        ),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


def test_partial_update_catalogue_item_change_manufacturer_id_invalid_id(test_client):
    """
    Test changing the manufacturer ID of a catalogue item to an invalid ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "manufacturer_id": "invalid",
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer does not exist"


def test_partial_update_catalogue_item_change_manufacturer_id_nonexistent_id(test_client):
    """
    Test changing the manufacturer ID of a catalogue item to a nonexistent ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category = response.json()

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category["id"],
        "manufacturer_id": manufacturer_id,
        "properties": add_ids_to_properties(
            catalogue_category["catalogue_item_properties"], CATALOGUE_ITEM_POST_B["properties"]
        ),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "manufacturer_id": str(ObjectId()),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer does not exist"
