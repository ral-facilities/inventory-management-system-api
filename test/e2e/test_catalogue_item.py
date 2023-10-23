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
            "url": "https://www.manufacturer-a.co.uk",
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
            "url": "https://www.manufacturer-a.co.uk",
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


def test_create_catalogue_item_with_invalid_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with an invalid catalogue category id.
    """
    catalogue_item_post = get_catalogue_item_a_dict("invalid")
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


def test_create_catalogue_item_with_nonexistent_catalogue_category_id(test_client):
    """
    Test creating a catalogue item with a nonexistent catalogue category id.
    """
    catalogue_item_post = get_catalogue_item_a_dict(str(ObjectId()))
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


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


def test_delete_catalogue_item(test_client):
    """
    Test deleting a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_item_post = get_catalogue_item_a_dict(response.json()["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)
    catalogue_item = response.json()

    response = test_client.delete(f"/v1/catalogue-items/{catalogue_item['id']}")

    assert response.status_code == 204
    response = test_client.delete(f"/v1/catalogue-items/{catalogue_item['id']}")
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


def test_delete_catalogue_item_with_children_items():
    """
    Test deleting a catalogue item with children items.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant item logic is implemented


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


def test_partial_update_catalogue_item(test_client):
    """
    Test changing the name and description of a catalogue item.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"name": "Catalogue Item B", "description": "This is Catalogue Item B"}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    catalogue_item_post["properties"][0]["unit"] = "mm"
    catalogue_item_post["properties"][1]["unit"] = None
    catalogue_item_post["properties"][2]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_patch["name"]
    assert catalogue_item["description"] == catalogue_item_patch["description"]
    assert catalogue_item["properties"] == catalogue_item_post["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


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


def test_partial_update_catalogue_item_has_children_items():
    """
    Test updating a catalogue item which has children items.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant item logic is implemented. Extra test cases may be needed.


def test_partial_update_catalogue_item_change_catalogue_category_id(test_client):
    """
    Test moving a catalogue item to another catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_a["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_b["id"],
        "properties": [{"name": "Property A", "value": True}],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    catalogue_item_patch["properties"][0]["unit"] = None
    assert catalogue_item["catalogue_category_id"] == catalogue_item_patch["catalogue_category_id"]
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_patch["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_partial_update_catalogue_item_change_catalogue_category_id_without_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category without supplying any catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_a["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"catalogue_category_id": catalogue_category_b["id"]}
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
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post = get_catalogue_item_b_dict(catalogue_category_b["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_a["id"],
        "properties": [{"name": "Property A", "value": 20}],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_partial_update_catalogue_item_change_catalogue_category_id_missing_non_mandatory_properties(test_client):
    """
    Test moving a catalogue item to another catalogue category with missing non-mandatory catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post = get_catalogue_item_b_dict(catalogue_category_b["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": catalogue_category_a["id"],
        "properties": [
            {"name": "Property B", "value": False},
            {"name": "Property C", "value": "20x15x10"},
        ],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    catalogue_item = response.json()

    catalogue_item_patch["properties"][0]["unit"] = None
    catalogue_item_patch["properties"][1]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_item_patch["catalogue_category_id"]
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_patch["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_partial_update_catalogue_item_change_catalogue_category_id_invalid_id(test_client):
    """
    Test changing the catalogue category ID of a catalogue item to an invalid ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    catalogue_item_post = get_catalogue_item_a_dict(response.json()["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": "invalid",
        "properties": [{"name": "Property A", "value": 20}],
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified catalogue category ID does not exist"


def test_partial_update_catalogue_item_change_catalogue_category_id_nonexistent_id(test_client):
    """
    Test changing the catalogue category ID of a catalogue item to a nonexistent ID.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    catalogue_item_post = get_catalogue_item_a_dict(response.json()["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "catalogue_category_id": str(ObjectId()),
        "properties": [{"name": "Property A", "value": 20}],
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
    catalogue_category_a = response.json()
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category_b = response.json()

    catalogue_item_post = get_catalogue_item_b_dict(catalogue_category_b["id"])
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"catalogue_category_id": catalogue_category_a["id"]}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue item to a non-leaf catalogue category is not allowed"


def test_partial_update_catalogue_item_change_catalogue_category_id_has_children_items():
    """
    Test moving a catalogue item with children items to another catalogue category.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant item logic is implemented.


def test_partial_update_catalogue_item_add_non_mandatory_property(test_client):
    """
    Test adding a non-mandatory catalogue item property and a value.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)
    catalogue_item_properties = catalogue_item_post["properties"].copy()

    # Delete the non-mandatory property so that the catalogue item is created without it
    del catalogue_item_post["properties"][0]
    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {"properties": catalogue_item_properties}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    catalogue_item_patch["properties"][0]["unit"] = "mm"
    catalogue_item_patch["properties"][1]["unit"] = None
    catalogue_item_patch["properties"][2]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_patch["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_partial_update_catalogue_item_remove_non_mandatory_property(test_client):
    """
    Test removing a non-mandatory catalogue item property and its value..
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    # Delete the non-mandatory property
    del catalogue_item_post["properties"][0]
    catalogue_item_patch = {"properties": catalogue_item_post["properties"]}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200

    catalogue_item = response.json()

    catalogue_item_patch["properties"][0]["unit"] = None
    catalogue_item_patch["properties"][1]["unit"] = "cm"
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_patch["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_post["manufacturer"]


def test_partial_update_catalogue_item_remove_mandatory_property(test_client):
    """
    Test removing a mandatory catalogue item property and its value.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    del catalogue_item_post["properties"][1]
    catalogue_item_patch = {"properties": catalogue_item_post["properties"]}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "Missing mandatory catalogue item property: 'Property B'"


def test_partial_update_catalogue_item_change_value_for_string_property_invalid_type(test_client):
    """
    Test changing the value of a string catalogue item property to an invalid type.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_post["properties"][2]["value"] = True
    catalogue_item_patch = {"properties": catalogue_item_post["properties"]}
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
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_post["properties"][0]["value"] = "20"
    catalogue_item_patch = {"properties": catalogue_item_post["properties"]}
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
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_a_dict(catalogue_category_id)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_post["properties"][1]["value"] = "False"
    catalogue_item_patch = {"properties": catalogue_item_post["properties"]}
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Invalid value type for catalogue item property 'Property B'. Expected type: boolean."
    )


def test_partial_update_catalogue_item_change_manufacturer(test_client):
    """
    Test updating the manufacturer details of a catalogue item.
    """
    # pylint: disable=fixme
    # TODO - Modify this test to use manufacturer ID when the relevant manufacturer logic is implemented
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)
    catalogue_category = response.json()

    catalogue_category_id = catalogue_category["id"]
    catalogue_item_post = get_catalogue_item_b_dict(catalogue_category_id)

    response = test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_item_patch = {
        "manufacturer": {
            "name": "Manufacturer B",
            "address": "1 Address, City, Country, Postcode",
            "url": "https://www.manufacturer-b.co.uk",
        }
    }
    response = test_client.patch(f"/v1/catalogue-items/{response.json()['id']}", json=catalogue_item_patch)

    assert response.status_code == 200
    catalogue_item = response.json()

    catalogue_item_post["properties"][0]["unit"] = None
    assert catalogue_item["catalogue_category_id"] == catalogue_category_id
    assert catalogue_item["name"] == catalogue_item_post["name"]
    assert catalogue_item["description"] == catalogue_item_post["description"]
    assert catalogue_item["properties"] == catalogue_item_post["properties"]
    assert catalogue_item["manufacturer"] == catalogue_item_patch["manufacturer"]


def test_partial_update_catalogue_item_change_manufacturer_id_invalid_id():
    """
    Test changing the manufacturer ID of a catalogue item to an invalid ID.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant manufacturer logic is implemented


def test_partial_update_catalogue_item_change_manufacturer_id_nonexistent_id():
    """
    Test changing the manufacturer ID of a catalogue item to a nonexistent ID.
    """
    # pylint: disable=fixme
    # TODO - Implement this test when the relevant manufacturer logic is implemented
