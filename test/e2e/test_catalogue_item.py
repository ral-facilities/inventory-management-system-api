"""
End-to-End tests for the catalogue item router.
"""
from typing import Dict

from bson import ObjectId


CATALOGUE_CATEGORY_POST_A = {  # pylint: disable=duplicate-code
    "name": "Category A",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
        {"name": "Property C", "type": "string", "unit": "cm", "mandatory": True},
    ],
}

CATALOGUE_CATEGORY_POST_B = {
    "name": "Category B",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "boolean", "mandatory": True},
    ],
}


def get_catalogue_item_a_dict(catalogue_category_id: str) -> Dict:
    """
    Creates a dictionary representing catalogue item A.

    :param catalogue_category_id: The ID of the catalogue category.
    :return: A dictionary representing catalogue item A.
    """
    return {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [
            {"name": "Property A", "value": 20},
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }


def get_catalogue_item_b_dict(catalogue_category_id: str) -> Dict:
    """
    Creates a dictionary representing catalogue item B.

    :param catalogue_category_id: The ID of the catalogue category.
    :return: A dictionary representing catalogue item B.
    """
    return {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item B",
        "description": "This is Catalogue Item B",
        "properties": [
            {"name": "Property A", "value": True},
        ],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }


def test_create_catalogue_item(test_client):
    """
    Test creating a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    catalogue_item_post["properties"][0]["unit"] = "mm"
    catalogue_item_post["properties"][1]["unit"] = None
    catalogue_item_post["properties"][2]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_post["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_create_catalogue_item_with_duplicate_name_within_catalogue_category(test_client):
    """
    Test creating a catalogue item with a duplicate name within the catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 409
    assert (
        response.json()["detail"] == "A catalogue item with the same name already exists within the catalogue category"
    )


def test_create_catalogue_item_with_invalid_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with an invalid catalogue category id.
    """
    catalogue_item_post = get_catalogue_item_a_dict("invalid")
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist in the database"


def test_create_catalogue_item_with_nonexistent_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with a nonexistent catalogue category id.
    """
    catalogue_item_post = get_catalogue_item_a_dict(str(ObjectId()))
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist in the database"


def test_create_catalogue_item_in_non_leaf_catalogue_category(test_client):
    """
    Test creating a catalogue item in a non-leaf catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


def test_create_catalogue_item_without_properties(test_client):
    """
    Test creating a catalogue item in leaf catalogue category that does not have catalogue item properties.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": True}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]

    catalogue_item_post = get_catalogue_item_b_dict(catalogue_category_id)
    del catalogue_item_post["properties"]
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == []
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_create_catalogue_item_with_missing_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    del catalogue_item_post["properties"][1]
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_create_catalogue_item_with_missing_non_mandatory_properties(test_client):
    """
    Test creating a catalogue item with missing non-mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)
    del catalogue_item_post["properties"][0]
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 201

    catalogue_item = response.json()

    catalogue_item_post["properties"][0]["unit"] = None
    catalogue_item_post["properties"][1]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_post["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_create_catalogue_item_with_invalid_value_type_for_string_property(test_client):
    """
    Test creating a catalogue item with invalid value type for a string catalogue item property.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    catalogue_item_post["properties"][2]["value"] = True
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
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    catalogue_item_post["properties"][0]["value"] = "20"
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
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    catalogue_item_post["properties"][1]["value"] = "False"
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
    )


def test_get_catalogue_item(test_client):
    """
    Test getting a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.get(f"/v1/catalogue-items/{response.json()['id']}")

    assert response.status_code == 200

    catalogue_item = response.json()

    catalogue_item_post["id"] = catalogue_item["id"]
    catalogue_item_post["properties"][0]["unit"] = "mm"
    catalogue_item_post["properties"][1]["unit"] = None
    catalogue_item_post["properties"][2]["unit"] = "cm"
    assert catalogue_item == catalogue_item_post


def test_get_catalogue_item_with_invalid_id(test_client):
    """
    Test getting a catalogue item with an invalid ID.
    """
    response = test_client.get("/v1/catalogue-items/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested catalogue item was not found"


def test_get_catalogue_item_with_nonexistent_id(test_client):
    """
    Test getting a catalogue item with a nonexistent ID.
    """
    response = test_client.get(f"/v1/catalogue-items/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested catalogue item was not found"


def test_get_catalogue_items(test_client):
    """
    Test getting catalogue items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post_a = get_catalogue_item_a_dict(catalogue_category_a["id"])
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = get_catalogue_item_b_dict(catalogue_category_b["id"])
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items")

    assert response.status_code == 200

    catalogue_items = response.json()

    catalogue_item_post_a["id"] = catalogue_items[0]["id"]
    catalogue_item_post_a["properties"][0]["unit"] = "mm"
    catalogue_item_post_a["properties"][1]["unit"] = None
    catalogue_item_post_a["properties"][2]["unit"] = "cm"
    catalogue_item_post_b["id"] = catalogue_items[1]["id"]
    catalogue_item_post_b["properties"][0]["unit"] = None
    assert catalogue_items == [catalogue_item_post_a, catalogue_item_post_b]


def test_get_catalogue_items_with_catalogue_category_id_filter(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post_a = get_catalogue_item_a_dict(catalogue_category_a["id"])
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = get_catalogue_item_b_dict(catalogue_category_b["id"])
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_b)

    response = test_client.get("/v1/catalogue-items", params={"catalogue_category_id": catalogue_category_b["id"]})

    assert response.status_code == 200

    catalogue_items = response.json()

    catalogue_item_post_b["id"] = catalogue_items[0]["id"]
    catalogue_item_post_b["properties"][0]["unit"] = None
    assert catalogue_items == [catalogue_item_post_b]


def test_get_catalogue_items_with_catalogue_category_id_filter_no_matching_results(test_client):
    """
    Test getting catalogue items based on the provided catalogue category ID filter.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post_a = get_catalogue_item_a_dict(catalogue_category_a["id"])
    test_client.post("/v1/catalogue-items", json=catalogue_item_post_a)

    catalogue_item_post_b = get_catalogue_item_b_dict(catalogue_category_b["id"])
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
