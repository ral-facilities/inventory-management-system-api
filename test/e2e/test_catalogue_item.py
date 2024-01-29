# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue item router.
"""
from unittest.mock import ANY

from test.e2e.test_item import ITEM_POST
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
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }


def test_create_catalogue_item_with_invalid_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with an invalid catalogue category id.
    """
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": "invalid",
        "manufacturer_id": str(ObjectId()),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


def test_create_catalogue_item_with_nonexistent_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with a nonexistent catalogue category id.
    """
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": str(ObjectId()),
        "manufacturer_id": str(ObjectId()),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


def test_create_catalogue_item_with_nonexistent_manufacturer_id(test_client):
    """
    Test creating a catalogue item with a nonexistent manufacturer id
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": response.json()["id"],
        "manufacturer_id": str(ObjectId()),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer ID does not exist"


def test_create_catalogue_item_with_an_invalid_manufacturer_id(test_client):
    """
    Test creating a catalogue item with an invalid manufacturer id
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": response.json()["id"],
        "manufacturer_id": "invalid",
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer ID does not exist"


def test_create_catalogue_item_in_non_leaf_catalogue_category(test_client):
    """
    Test creating a catalogue item in a non-leaf catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": response.json()["id"],
        "manufacturer_id": str(ObjectId()),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


def test_create_catalogue_item_with_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test creating a catalogue item with an obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)
    catalogue_item_a_id = response.json()["id"]

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
    }


def test_create_catalogue_item_with_invalid_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test creating a catalogue item with an non-existent obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": "invalid",
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item ID does not exist"


def test_create_catalogue_item_with_non_existent_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test creating a catalogue item with an non-existent obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": str(ObjectId()),
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item ID does not exist"


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
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": [CATALOGUE_ITEM_POST_A["properties"][0], CATALOGUE_ITEM_POST_A["properties"][2]],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_create_catalogue_item_with_missing_non_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing non-mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": CATALOGUE_ITEM_POST_A["properties"][-2:],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:],
    }


def test_create_catalogue_item_with_invalid_value_type_for_string_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a string catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": True},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property C'. Expected type: string."
    )


def test_create_catalogue_item_with_invalid_value_type_for_number_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a number catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": [
            {"name": "Property A", "value": "20"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property A'. Expected type: number."
    )


def test_create_catalogue_item_with_invalid_value_type_for_boolean_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a boolean catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": "False"},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
    )


def test_delete_catalogue_item(test_client):
    """
    Test deleting a catalogue item.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
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
    assert response.json()["detail"] == "A catalogue item with such ID was not found"


def test_delete_catalogue_item_with_nonexistent_id(test_client):
    """
    Test deleting a catalogue item with a nonexistent ID.
    """
    response = test_client.delete(f"/v1/catalogue-items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue item with such ID was not found"


def test_delete_catalogue_item_with_child_items(test_client):
    """
    Test deleting a catalogue item with child items.
    """
    # pylint: disable=duplicate-code
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    # child
    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id}
    test_client.post("/v1/items", json=item_post)

    response = test_client.delete(f"/v1/catalogue-items/{catalogue_item_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be deleted"


def test_get_catalogue_item(test_client):
    """
    Test getting a catalogue item.
    """
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
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
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }


def test_get_catalogue_item_with_invalid_id(test_client):
    """
    Test getting a catalogue item with an invalid ID.
    """
    response = test_client.get("/v1/catalogue-items/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue item with such ID was not found"


def test_get_catalogue_item_with_nonexistent_id(test_client):
    """
    Test getting a catalogue item with a nonexistent ID.
    """
    response = test_client.get(f"/v1/catalogue-items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue item with such ID was not found"


def test_get_catalogue_items(test_client):
    """
    Test getting catalogue items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items")

    assert response.status_code == 200

    catalogue_items = response.json()

    assert catalogue_items == [
        {
            **CATALOGUE_ITEM_POST_A_EXPECTED,
            "catalogue_category_id": catalogue_category_a_id,
            "manufacturer_id": manufacturer_id,
        },
        {
            **CATALOGUE_ITEM_POST_B_EXPECTED,
            "catalogue_category_id": catalogue_category_b_id,
            "manufacturer_id": manufacturer_id,
        },
    ]


def test_get_catalogue_items_with_catalogue_category_id_filter(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items", params={"catalogue_category_id": catalogue_category_b_id})

    assert response.status_code == 200

    catalogue_items = response.json()

    assert catalogue_items == [
        {
            **CATALOGUE_ITEM_POST_B_EXPECTED,
            "catalogue_category_id": catalogue_category_b_id,
            "manufacturer_id": manufacturer_id,
        }
    ]


def test_get_catalogue_items_with_catalogue_category_id_filter_no_matching_results(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
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


def test_partial_update_catalogue_item(test_client):
    """
    Test changing the name and description of a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
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
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }


def test_partial_update_catalogue_item_invalid_id(test_client):
    """
    Test updating a catalogue item with an invalid ID.
    """
    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}

    response = test_client.patch("/v1/catalogue-items/invalid", json=catalogue_item_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue item with such ID was not found"


def test_partial_update_catalogue_item_nonexistent_id(test_client):
    """
    Test updating a catalogue item with a nonexistent ID.
    """
    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}

    response = test_client.patch(f"/v1/catalogue-items/{str(ObjectId())}", json=catalogue_item_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue item with such ID was not found"


def test_partial_update_catalogue_item_has_child_items(test_client):
    """
    Test updating a catalogue item which has child items.
    """
    # pylint: disable=duplicate-code
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    # pylint: enable=duplicate-code
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    # child
    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id}
    test_client.post("/v1/items", json=item_post)

    response = test_client.patch(f"/v1/catalogue-items/{catalogue_item_id}", json={"name": "Catalogue Item B"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


def test_partial_update_catalogue_item_change_catalogue_category_id(test_client):
    """
    Test moving a catalogue item to another catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_b_id,
        "properties": CATALOGUE_ITEM_POST_B["properties"],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
        "properties": CATALOGUE_ITEM_POST_B_EXPECTED["properties"],
    }


def test_partial_update_catalogue_item_change_catalogue_category_id_without_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category without supplying any catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"catalogue_category_id": catalogue_category_b_id}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property A'. Expected type: boolean."
    )


def test_partial_update_catalogue_item_change_catalogue_category_id_missing_mandatory_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category with missing mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_a_id,
        "properties": [CATALOGUE_ITEM_POST_B["properties"][0]],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_partial_update_catalogue_item_change_catalogue_category_id_missing_non_mandatory_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category with missing non-mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_a_id,
        "properties": CATALOGUE_ITEM_POST_A["properties"][-2:],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
        "properties": CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:],
    }


def test_partial_update_catalogue_item_change_catalogue_category_id_invalid_id(test_client):
    """
    Test changing the catalogue category ID of a catalogue item to an invalid ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "catalogue_category_id": "invalid",
        "properties": [CATALOGUE_ITEM_POST_A["properties"][0]],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


def test_partial_update_catalogue_item_change_catalogue_category_id_nonexistent_id(test_client):
    """
    Test changing the catalogue category ID of a catalogue item to a nonexistent ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "catalogue_category_id": str(ObjectId()),
        "properties": [CATALOGUE_ITEM_POST_A["properties"][0]],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


def test_partial_update_catalogue_item_change_catalogue_category_id_non_leaf_catalogue_category(test_client):
    """
    Test moving a catalogue item to a non-leaf catalogue category.
    """
    catalogue_category_post_a = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post_a)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
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
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_b_id,
        "properties": CATALOGUE_ITEM_POST_B["properties"],
    }

    # child
    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id}
    test_client.post("/v1/items", json=item_post)

    response = test_client.patch(f"/v1/catalogue-items/{catalogue_item_id}", json=catalogue_item_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue item has child elements and cannot be updated"


def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id(test_client):
    """
    Test updating a catalogue item with an obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post_a = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_a_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)
    catalogue_item_a_id = response.json()["id"]

    catalogue_item_post_b = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": catalogue_item_a_id}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_B_EXPECTED,
        "catalogue_category_id": catalogue_category_b_id,
        "manufacturer_id": manufacturer_id,
        "is_obsolete": True,
        "obsolete_replacement_catalogue_item_id": catalogue_item_a_id,
    }


def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id_invalid_id(test_client):
    """
    Test updating a catalogue item with an invalid obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": "invalid"}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item ID does not exist"


def test_partial_update_catalogue_item_change_obsolete_replacement_catalogue_item_id_non_existent_id(test_client):
    """
    Test updating a catalogue item with aa non-existent obsolete replacement catalogue item ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch_b = {"is_obsolete": True, "obsolete_replacement_catalogue_item_id": str(ObjectId())}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch_b)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified replacement catalogue item ID does not exist"


def test_partial_update_catalogue_item_add_non_mandatory_property(test_client):
    """
    Test adding a non-mandatory catalogue item property and a value.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": CATALOGUE_ITEM_POST_A["properties"][-2:],
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"properties": CATALOGUE_ITEM_POST_A["properties"]}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }


def test_partial_update_catalogue_item_remove_non_mandatory_property(test_client):
    """
    Test removing a non-mandatory catalogue item property and its value..
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {"properties": CATALOGUE_ITEM_POST_A["properties"][-2:]}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    assert catalogue_item == {
        **CATALOGUE_ITEM_POST_A_EXPECTED,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "properties": CATALOGUE_ITEM_POST_A_EXPECTED["properties"][-2:],
    }


def test_partial_update_catalogue_item_remove_mandatory_property(test_client):
    """
    Test removing a mandatory catalogue item property and its value.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    # pylint: enable=duplicate-code

    catalogue_item_patch = {
        "properties": [CATALOGUE_ITEM_POST_A["properties"][0], CATALOGUE_ITEM_POST_A["properties"][2]]
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_partial_update_catalogue_item_change_value_for_string_property_invalid_type(test_client):
    """
    Test changing the value of a string catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": True},
        ]
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property C'. Expected type: string."
    )


def test_partial_update_catalogue_item_change_value_for_number_property_invalid_type(test_client):
    """
    Test changing the value of a number catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": [
            {"name": "Property A", "value": "20"},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ]
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property A'. Expected type: number."
    )


def test_partial_update_catalogue_item_change_value_for_boolean_property_invalid_type(test_client):
    """
    Test changing the value of a boolean catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": "False"},
            {"name": "Property C", "value": "20x15x10"},
        ]
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
    )


def test_partial_update_catalogue_item_change_manufacturer_id(test_client):
    """
    Test updating the manufacturer ID of a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_id = response.json()["id"]

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
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_d_id,
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
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_e_id,
    }


def test_partial_update_catalogue_item_change_manufacturer_id_invalid_id(test_client):
    """
    Test changing the manufacturer ID of a catalogue item to an invalid ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "manufacturer_id": "invalid",
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer ID does not exist"


def test_partial_update_catalogue_item_change_manufacturer_id_nonexistent_id(test_client):
    """
    Test changing the manufacturer ID of a catalogue item to a nonexistent ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_id = response.json()["id"]

    response = test_client.post("/v1/manufacturers", json=MANUFACTURER)
    manufacturer_id = response.json()["id"]

    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_B,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "manufacturer_id": str(ObjectId()),
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified manufacturer ID does not exist"
