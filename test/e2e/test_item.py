"""
End-to-End tests for the catalogue item router.
"""
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

SYSTEM_POST_A = {
    "name": "System A",
    "description": "System description",
    "location": "Test location",
    "owner": "Me",
    "importance": "low",
}
# pylint: enable=duplicate-code

ITEM_POST = {
    "is_defective": False,
    "usage_status": 0,
    "warranty_end_date": "2015-11-15T23:59:59Z",
    "serial_number": "xyz123",
    "delivered_date": "2012-12-05T12:00:00Z",
    "notes": "Test notes",
    "properties": [{"name": "Property A", "value": 21}],
}

ITEM_POST_EXPECTED = {
    **ITEM_POST,
    "id": ANY,
    "purchase_order_number": None,
    "asset_number": None,
    "properties": [
        {"name": "Property A", "value": 21, "unit": "mm"},
        {"name": "Property B", "value": False, "unit": None},
        {"name": "Property C", "value": "20x15x10", "unit": "cm"},
    ],
}


def test_create_item(test_client):
    """
    Test creating an item.
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id, "system_id": system_id}
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 201

    item = response.json()

    assert item == {**ITEM_POST_EXPECTED, "catalogue_item_id": catalogue_item_id, "system_id": system_id}


def test_create_item_with_invalid_catalogue_item_id(test_client):
    """
    Test creating an item with an invalid catalogue item ID.
    """
    item_post = {**ITEM_POST, "catalogue_item_id": "invalid", "system_id": str(ObjectId())}
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue item ID does not exist"


def test_create_item_with_non_existent_catalogue_item_id(test_client):
    """
    Test creating an item with a non-existent catalogue item ID.
    """
    item_post = {**ITEM_POST, "catalogue_item_id": str(ObjectId()), "system_id": str(ObjectId())}
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue item ID does not exist"


def test_create_item_with_invalid_system_id(test_client):
    """
    Test creating an item with an invalid system ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id, "system_id": "invalid"}
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified system ID does not exist"


def test_create_item_with_non_existent_system_id(test_client):
    """
    Test creating an item with a non-existent system ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id, "system_id": str(ObjectId())}
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified system ID does not exist"


def test_create_item_without_properties(test_client):
    """
    Testing creating an item without properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {**ITEM_POST, "catalogue_item_id": catalogue_item_id}
    del item_post["properties"]
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 201

    item = response.json()

    assert item == {
        **ITEM_POST_EXPECTED,
        "catalogue_item_id": catalogue_item_id,
        "system_id": None,
        "properties": [{"name": "Property A", "value": 20, "unit": "mm"}] + ITEM_POST_EXPECTED["properties"][-2:],
    }


def test_create_item_with_invalid_value_type_for_string_property(test_client):
    """
    Test creating an item with invalid value type for a string catalogue item property.
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "properties": [{"name": "Property C", "value": True}],
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property C'. Expected type: string."
    )


def test_create_item_with_invalid_value_type_for_number_property(test_client):
    """
    Test creating an item with invalid value type for a number catalogue item property.
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "properties": [{"name": "Property A", "value": "20"}],
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property A'. Expected type: number."
    )


def test_create_item_with_invalid_value_type_for_boolean_property(test_client):
    """
    Test creating an item with invalid value type for a boolean catalogue item property.
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    # pylint: disable=duplicate-code
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post = {
        **ITEM_POST,
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "properties": [{"name": "Property B", "value": "False"}],
    }
    response = test_client.post("/v1/items", json=item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
    )


def test_list(test_client):
    """
    Test getting items
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post_a = {"catalogue_item_id": catalogue_item_id, "system_id": None, "is_defective": False, "usage_status": 0}
    item_post_b = {
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "is_defective": False,
        "usage_status": 0,
    }

    test_client.post("/v1/items", json=item_post_a)
    test_client.post("/v1/items", json=item_post_b)

    response = test_client.get("/v1/items")

    assert response.status_code == 200

    items = list(response.json())

    assert len(items) == 2

    assert items[0]["catalogue_item_id"] == item_post_a["catalogue_item_id"]
    assert items[0]["system_id"] == item_post_a["system_id"]
    assert items[0]["is_defective"] == item_post_a["is_defective"]
    assert items[0]["usage_status"] == item_post_a["usage_status"]

    assert items[1]["catalogue_item_id"] == item_post_b["catalogue_item_id"]
    assert items[1]["system_id"] == item_post_b["system_id"]
    assert items[1]["is_defective"] == item_post_b["is_defective"]
    assert items[1]["usage_status"] == item_post_b["usage_status"]


def test_list_with_system_id_filters(test_client):
    """
    Test getting items with system id filter
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post_a = {"catalogue_item_id": catalogue_item_id, "system_id": None, "is_defective": False, "usage_status": 0}
    item_post_b = {
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "is_defective": False,
        "usage_status": 0,
    }

    test_client.post("/v1/items", json=item_post_a)
    test_client.post("/v1/items", json=item_post_b)

    response = test_client.get("/v1/items", params={"system_id": system_id})

    assert response.status_code == 200

    items = list(response.json())

    assert len(items) == 1

    assert items[0]["catalogue_item_id"] == item_post_b["catalogue_item_id"]
    assert items[0]["system_id"] == item_post_b["system_id"]
    assert items[0]["is_defective"] == item_post_b["is_defective"]
    assert items[0]["usage_status"] == item_post_b["usage_status"]


def test_list_with_catalogue_id_filters(test_client):
    """
    Test getting items with catalogue item id filter
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post_a = {"catalogue_item_id": catalogue_item_id, "system_id": None, "is_defective": False, "usage_status": 0}

    test_client.post("/v1/items", json=item_post_a)

    response = test_client.get("/v1/items", params={"catalogue_item_id": catalogue_item_id})

    assert response.status_code == 200

    items = list(response.json())

    assert len(items) == 1

    assert items[0]["catalogue_item_id"] == item_post_a["catalogue_item_id"]
    assert items[0]["system_id"] == item_post_a["system_id"]
    assert items[0]["is_defective"] == item_post_a["is_defective"]
    assert items[0]["usage_status"] == item_post_a["usage_status"]


def test_list_with_no_matching_filters(test_client):
    """
    Test getting items with neither filter having matching results
    """
    response = test_client.post("/v1/systems", json=SYSTEM_POST_A)
    system_id = response.json()["id"]
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_id = response.json()["id"]
    response = test_client.post("/v1/manufacturers", json=MANUFACTURER_POST)
    # pylint: disable=duplicate-code
    manufacturer_id = response.json()["id"]
    catalogue_item_post = {
        **CATALOGUE_ITEM_POST_A,
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
    }
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item_id = response.json()["id"]
    # pylint: enable=duplicate-code

    item_post_a = {"catalogue_item_id": catalogue_item_id, "system_id": None, "is_defective": False, "usage_status": 0}
    item_post_b = {
        "catalogue_item_id": catalogue_item_id,
        "system_id": system_id,
        "is_defective": False,
        "usage_status": 0,
    }

    test_client.post("/v1/items", json=item_post_a)
    test_client.post("/v1/items", json=item_post_b)

    response = test_client.get("/v1/items", params={"system_id": str(ObjectId()), "catalogue_item_id": str(ObjectId())})

    assert response.status_code == 200

    items = list(response.json())

    assert not items


def test_list_with_invalid_system_id_filter(test_client):
    """
    Test getting items with an invalid system id filter
    """
    response = test_client.get("/v1/items", params={"system_id": "Invalid"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_with_invalid_catalogue_item_id_filter(test_client):
    """
    Test getting items with an invalid catalogue item id filter
    """
    response = test_client.get("/v1/items", params={"catalogue_item_id": "Invalid"})

    assert response.status_code == 200
    assert response.json() == []
