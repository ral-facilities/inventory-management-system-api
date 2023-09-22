# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue category router.
"""
from bson import ObjectId


def test_create_catalogue_category(test_client):
    """
    Test creating a catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 201

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == []


def test_create_catalogue_category_with_valid_parent_id(test_client):
    """
    Test creating a catalogue category with a valid parent ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "parent_id": parent_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 201

    catalogue_category = response.json()

    catalogue_category_post["catalogue_item_properties"][1]["unit"] = None
    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a/category-a"
    assert catalogue_category["parent_path"] == "/category-a"
    assert catalogue_category["parent_id"] == parent_id
    assert catalogue_category["catalogue_item_properties"] == catalogue_category_post["catalogue_item_properties"]


def test_create_catalogue_category_with_duplicate_name_within_parent(test_client):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {"name": "Category A", "is_leaf": False, "parent_id": parent_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "parent_id": parent_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_create_catalogue_category_with_invalid_parent_id(test_client):
    """
    Test creating a catalogue category with an invalid parent ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False, "parent_id": "invalid"}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_create_catalogue_category_with_nonexistent_parent_id(test_client):
    """
    Test creating a catalogue category with a nonexistent parent ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False, "parent_id": str(ObjectId())}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_create_catalogue_category_with_leaf_parent_catalogue_category(test_client):
    """
    Test creating a catalogue category in a leaf parent catalogue category.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {"name": "Category A", "is_leaf": False, "parent_id": parent_id}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue category to a leaf parent catalogue category is not allowed"


def test_create_catalogue_category_with_invalid_catalogue_item_property_type(test_client):
    """
    Test creating a catalogue category with an invalid catalogue item property type.
    """
    catalogue_category = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "invalid-type", "unit": "mm", "mandatory": False},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "value is not a valid enumeration member; permitted: 'string', 'number', 'boolean'"
    )


def test_create_catalogue_category_with_disallowed_unit_value_for_boolean_catalogue_item_property(test_client):
    """
    Test creating a catalogue category when a unit is supplied for a boolean catalogue item property.
    """
    catalogue_category = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "boolean", "unit": "mm", "mandatory": False},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Unit not allowed for boolean catalogue item property 'Property A'"


def test_create_leaf_catalogue_category_without_catalogue_item_properties(test_client):
    """
    Test creating a catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": True}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 201

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == []


def test_create_non_leaf_catalogue_category_with_catalogue_item_properties(test_client):
    """
    Test creating a non-leaf catalogue category with catalogue item properties.
    """
    catalogue_category = {
        "name": "Category A",
        "is_leaf": False,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"] == "Catalogue item properties not allowed for non-leaf catalogue category"
    )


def test_delete_catalogue_category(test_client):
    """
    Test deleting a catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    response = test_client.delete(f"/v1/catalogue-categories/{catalogue_category['id']}")

    assert response.status_code == 204
    response = test_client.get(f"/v1/catalogue-categories/{catalogue_category['id']}")
    assert response.status_code == 404


def test_delete_catalogue_category_with_invalid_id(test_client):
    """
    Test deleting a catalogue category with an invalid ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.delete("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_delete_catalogue_category_with_nonexistent_id(test_client):
    """
    Test deleting a catalogue category with a nonexistent ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.delete(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_delete_catalogue_category_with_children_catalogue_categories(test_client):
    """
    Test deleting a catalogue category with children catalogue categories.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    parent_response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = parent_response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "parent_id": parent_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.delete(f"/v1/catalogue-categories/{parent_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be deleted"


def test_delete_catalogue_category_with_children_catalogue_items(test_client):
    """
    Test deleting a catalogue category with children catalogue items.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_id = response.json()["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.delete(f"/v1/catalogue-categories/{catalogue_category_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be deleted"


def test_get_catalogue_category(test_client):
    """
    Test getting a catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "parent_id": parent_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.get(f"/v1/catalogue-categories/{response.json()['id']}")

    assert response.status_code == 200

    catalogue_category = response.json()

    catalogue_category_post["catalogue_item_properties"][1]["unit"] = None
    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a/category-a"
    assert catalogue_category["parent_path"] == "/category-a"
    assert catalogue_category["parent_id"] == parent_id
    assert catalogue_category["catalogue_item_properties"] == catalogue_category_post["catalogue_item_properties"]


def test_get_catalogue_category_with_invalid_id(test_client):
    """
    Test getting a catalogue category with an invalid ID.
    """
    response = test_client.get("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_get_catalogue_category_with_nonexistent_id(test_client):
    """
    Test getting a catalogue category with a nonexistent ID.
    """
    response = test_client.get(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_get_catalogue_categories(test_client):
    """
    Test getting catalogue categories.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {
        "name": "Category C",
        "is_leaf": True,
        "parent_id": parent_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.get("/v1/catalogue-categories")

    assert response.status_code == 200

    catalogue_categories = list(response.json())

    assert len(catalogue_categories) == 3
    assert catalogue_categories[0]["path"] == "/category-a"
    assert catalogue_categories[0]["parent_path"] == "/"
    assert catalogue_categories[1]["path"] == "/category-b"
    assert catalogue_categories[1]["parent_path"] == "/"
    assert catalogue_categories[2]["path"] == "/category-b/category-c"
    assert catalogue_categories[2]["parent_path"] == "/category-b"


def test_get_catalogue_categories_with_path_filter(test_client):
    """
    Test getting catalogue categories based on the provided parent path filter.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.get("/v1/catalogue-categories", params={"path": "/category-a"})

    assert response.status_code == 200

    catalogue_categories = list(response.json())

    assert len(catalogue_categories) == 1
    assert catalogue_categories[0]["path"] == "/category-a"
    assert catalogue_categories[0]["parent_path"] == "/"


def test_get_catalogue_categories_with_parent_path_filter(test_client):
    """
    Test getting catalogue categories based on the provided parent path filter.
    """
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {
        "name": "Category C",
        "is_leaf": True,
        "parent_id": parent_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.get("/v1/catalogue-categories", params={"parent_path": "/"})

    assert response.status_code == 200

    catalogue_categories = list(response.json())

    assert len(catalogue_categories) == 1
    assert catalogue_categories[0]["path"] == "/category-b"
    assert catalogue_categories[0]["parent_path"] == "/"


def test_get_catalogue_categories_with_path_and_parent_path_filters(test_client):
    """
    Test getting catalogue categories based on the provided path and parent path filters.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.get("/v1/catalogue-categories", params={"path": "/category-b", "parent_path": "/"})

    assert response.status_code == 200

    catalogue_categories = list(response.json())

    assert len(catalogue_categories) == 1
    assert catalogue_categories[0]["path"] == "/category-b"
    assert catalogue_categories[0]["parent_path"] == "/"


def test_get_catalogue_categories_with_path_and_parent_path_filters_no_matching_results(test_client):
    """
    Test getting catalogue categories based on the provided path and parent path filters when there is no matching
    results in the database.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    response = test_client.get("/v1/catalogue-categories", params={"path": "/category-c", "parent_path": "/"})

    assert response.status_code == 200

    catalogue_categories = list(response.json())

    assert len(catalogue_categories) == 0


def test_partial_update_catalogue_category_change_name(test_client):
    """
    Test changing the name of a catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"name": "Category B"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_patch["name"]
    assert catalogue_category["code"] == "category-b"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-b"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == []


def test_partial_update_catalogue_category_change_name_duplicate(test_client):
    """
    Test changing the name of a catalogue category to a name that already exists.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"name": "Category A"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_partial_update_catalogue_category_change_name_has_children_catalogue_categories(test_client):
    """
    Test changing the name of a catalogue category which has children catalogue categories.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]
    catalogue_category_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"name": "Category A"}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_change_name_has_children_catalogue_items(test_client):
    """
    Test changing the name of a catalogue category which has children catalogue items.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_id = response.json()["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"name": "Category B"}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf(test_client):
    """
    Test changing a catalogue category from non-leaf to leaf.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {
        "is_leaf": True,
        "catalogue_item_properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_patch["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == catalogue_category_patch["catalogue_item_properties"]


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_without_catalogue_item_properties(test_client):
    """
    Test changing a catalogue category from non-leaf to leaf without supplying any catalogue item properties.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"is_leaf": True}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_patch["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == []


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_has_children_catalogue_categories(test_client):
    """
    Test changing a catalogue category with children catalogue categories from non-leaf to leaf.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]
    catalogue_category_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {
        "is_leaf": True,
        "catalogue_item_properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf(test_client):
    """
    Test changing a catalogue category from leaf to non-leaf.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"is_leaf": False}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_patch["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == []


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_has_children_catalogue_items(test_client):
    """
    Test changing a catalogue category with children catalogue items from leaf to non-leaf.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_id = response.json()["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"is_leaf": False}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_with_catalogue_item_properties(test_client):
    """
    Test changing a catalogue category from leaf to non-leaf while also changing its catalogue item properties.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {
        "is_leaf": False,
        "catalogue_item_properties": [{"name": "Property B", "type": "boolean", "mandatory": True}],
    }
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"] == "Catalogue item properties not allowed for non-leaf catalogue category"
    )


def test_partial_update_catalogue_category_change_parent_id(test_client):
    """
    Test moving a catalogue category to another parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]

    catalogue_category_post = {
        "name": "Category B",
        "is_leaf": True,
        "parent_id": catalogue_category_a_id,
        "catalogue_item_properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]

    catalogue_category_patch = {"parent_id": None}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-b"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-b"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] == catalogue_category_patch["parent_id"]
    assert catalogue_category["catalogue_item_properties"] == catalogue_category_post["catalogue_item_properties"]


def test_partial_update_catalogue_category_change_parent_id_has_children_catalogue_categories(test_client):
    """
    Test moving a catalogue category with children categories to another parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]
    catalogue_category_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_a_id}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]
    catalogue_category_post = {"name": "Category C", "is_leaf": False, "parent_id": catalogue_category_b_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": None}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_change_parent_id_has_children_catalogue_items(test_client):
    """
    Test moving a catalogue category with children items to another parent catalogue category.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]
    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]
    catalogue_category_post = {
        "name": "Category C",
        "is_leaf": True,
        "parent_id": catalogue_category_b_id,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_c_id = response.json()["id"]

    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_c_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"parent_id": catalogue_category_a_id}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_change_parent_id_duplicate_name(test_client):
    """
    Test moving a catalogue category to another parent catalogue category in which a category with the same name already
    exists.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]

    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]

    catalogue_category_post = {"name": "Category A", "is_leaf": False, "parent_id": catalogue_category_b_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": catalogue_category_b_id}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_a_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_partial_update_catalogue_category_change_parent_id_leaf_parent_catalogue_category(test_client):
    """
    Test moving a catalogue category to a leaf parent catalogue category.
    """
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_a_id = response.json()["id"]

    catalogue_category_post = {"name": "Category B", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_b_id = response.json()["id"]

    catalogue_category_patch = {"parent_id": catalogue_category_a_id}
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
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_partial_update_catalogue_category_change_parent_id_nonexistent_id(test_client):
    """
    Test changing the parent ID of a catalogue category to a nonexistent ID.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"parent_id": str(ObjectId())}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_partial_update_catalogue_category_add_catalogue_item_property(test_client):
    """
    Test adding a catalogue item property.
    """
    catalogue_item_properties = [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": catalogue_item_properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_item_properties.append({"name": "Property B", "type": "boolean", "mandatory": True})
    catalogue_category_patch = {"catalogue_item_properties": catalogue_item_properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    catalogue_item_properties[1]["unit"] = None
    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == catalogue_item_properties


def test_partial_update_catalogue_category_remove_catalogue_item_property(test_client):
    """
    Test removing a catalogue item property.
    """
    catalogue_item_properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": catalogue_item_properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_item_properties.pop(0)
    catalogue_category_patch = {"catalogue_item_properties": catalogue_item_properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    catalogue_item_properties[0]["unit"] = None
    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == catalogue_item_properties


def test_partial_update_catalogue_category_modify_catalogue_item_property(test_client):
    """
    Test modifying a catalogue item property.
    """
    catalogue_item_properties = [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
    ]
    catalogue_category_post = {
        "name": "Category A",
        "is_leaf": True,
        "catalogue_item_properties": catalogue_item_properties,
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_item_properties[1]["name"] = "Property C"
    catalogue_category_patch = {"catalogue_item_properties": catalogue_item_properties}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200

    catalogue_category = response.json()

    catalogue_item_properties[1]["unit"] = None
    assert catalogue_category["name"] == catalogue_category_post["name"]
    assert catalogue_category["code"] == "category-a"
    assert catalogue_category["is_leaf"] == catalogue_category_post["is_leaf"]
    assert catalogue_category["path"] == "/category-a"
    assert catalogue_category["parent_path"] == "/"
    assert catalogue_category["parent_id"] is None
    assert catalogue_category["catalogue_item_properties"] == catalogue_item_properties


def test_partial_update_catalogue_category_change_catalogue_item_properties_has_children_catalogue_items(test_client):
    """
    Test changing the catalogue item properties when a catalogue category has children catalogue items.
    """
    catalogue_category_post = {
        "name": "Category C",
        "is_leaf": True,
        "parent_id": None,
        "catalogue_item_properties": [
            {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
            {"name": "Property B", "type": "boolean", "mandatory": True},
        ],
    }
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]

    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {
        "catalogue_item_properties": [{"name": "Property B", "type": "string", "mandatory": False}]
    }
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has children elements and cannot be updated"


def test_partial_update_catalogue_category_invalid_id(test_client):
    """
    Test updating a catalogue category with an invalid ID.
    """
    catalogue_category_patch = {"name": "Category A", "is_leaf": False}

    response = test_client.patch("/v1/catalogue-categories/invalid", json=catalogue_category_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_partial_update_catalogue_category_nonexistent_id(test_client):
    """
    Test updating a catalogue category with a nonexistent ID.
    """
    catalogue_category_patch = {"name": "Category A", "is_leaf": False}

    response = test_client.patch(f"/v1/catalogue-categories/{str(ObjectId())}", json=catalogue_category_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"
