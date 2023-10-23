# pylint: disable=too-many-lines
"""
End-to-End tests for the catalogue category router.
"""
from unittest.mock import ANY

from bson import ObjectId

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH

CATALOGUE_CATEGORY_POST_A = {"name": "Category A", "is_leaf": False}
CATALOGUE_CATEGORY_POST_A_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_A,
    "id": ANY,
    "code": "category-a",
    "parent_id": None,
    "catalogue_item_properties": [],
}

# To be posted as a child of the above - leaf with parent
CATALOGUE_CATEGORY_POST_B = {
    "name": "Category B",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "mandatory": True},
    ],
}
CATALOGUE_CATEGORY_POST_B_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_B,
    "id": ANY,
    "code": "category-b",
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
    ],
}

# Leaf with no parent
CATALOGUE_CATEGORY_POST_C = {
    "name": "Category C",
    "is_leaf": True,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
    ],
}
CATALOGUE_CATEGORY_POST_C_EXPECTED = {
    **CATALOGUE_CATEGORY_POST_C,
    "id": ANY,
    "code": "category-c",
    "parent_id": None,
    "catalogue_item_properties": [
        {"name": "Property A", "type": "number", "unit": "mm", "mandatory": False},
        {"name": "Property B", "type": "boolean", "unit": None, "mandatory": True},
    ],
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

    (category_a, category_b, *_) = _post_nested_catalogue_categories(
        test_client, [CATALOGUE_CATEGORY_POST_A, CATALOGUE_CATEGORY_POST_B]
    )
    (category_c, *_) = _post_nested_catalogue_categories(test_client, [CATALOGUE_CATEGORY_POST_C])

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

    # Child
    response = test_client.post(
        "/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_B, "parent_id": parent_catalogue_category["id"]}
    )

    assert response.status_code == 201
    catalogue_category = response.json()
    assert catalogue_category == {**CATALOGUE_CATEGORY_POST_B_EXPECTED, "parent_id": parent_catalogue_category["id"]}


def test_create_catalogue_category_with_duplicate_name_within_parent(test_client):
    """
    Test creating a catalogue category with a duplicate name within the parent catalogue category.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    # Child - post twice as will have the same name
    response = test_client.post(
        "/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_B, "parent_id": parent_catalogue_category["id"]}
    )
    response = test_client.post(
        "/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_B, "parent_id": parent_catalogue_category["id"]}
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_create_catalogue_category_with_invalid_parent_id(test_client):
    """
    Test creating a catalogue category with an invalid parent ID.
    """
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "parent_id": "invalid"}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_create_catalogue_category_with_non_existent_parent_id(test_client):
    """
    Test creating a catalogue category with a non-existent parent ID.
    """
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "parent_id": str(ObjectId())}

    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 422
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_create_catalogue_category_with_leaf_parent_catalogue_category(test_client):
    """
    Test creating a catalogue category in a leaf parent catalogue category.
    """
    response = test_client.post("/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_C})
    catalogue_category = response.json()

    parent_id = catalogue_category["id"]
    catalogue_category_post = {**CATALOGUE_CATEGORY_POST_A, "parent_id": parent_id}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    assert response.status_code == 409
    assert response.json()["detail"] == "Adding a catalogue category to a leaf parent catalogue category is not allowed"


def test_create_catalogue_category_with_invalid_catalogue_item_property_type(test_client):
    """
    Test creating a catalogue category with an invalid catalogue item property type.
    """
    catalogue_category = {
        **CATALOGUE_CATEGORY_POST_C,
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
        **CATALOGUE_CATEGORY_POST_C,
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
    catalogue_category = {**CATALOGUE_CATEGORY_POST_C}
    del catalogue_category["catalogue_item_properties"]
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category)

    assert response.status_code == 201
    catalogue_category = response.json()
    assert catalogue_category == {**CATALOGUE_CATEGORY_POST_C_EXPECTED, "catalogue_item_properties": []}


def test_create_non_leaf_catalogue_category_with_catalogue_item_properties(test_client):
    """
    Test creating a non-leaf catalogue category with catalogue item properties.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)

    assert response.status_code == 201
    catalogue_category = response.json()
    assert catalogue_category == CATALOGUE_CATEGORY_POST_A_EXPECTED


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
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_delete_catalogue_category_with_non_existent_id(test_client):
    """
    Test deleting a catalogue category with a non-existent ID.
    """
    response = test_client.delete(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_delete_catalogue_category_with_child_catalogue_categories(test_client):
    """
    Test deleting a catalogue category with child catalogue categories.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    # Child
    response = test_client.post(
        "/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_B, "parent_id": parent_catalogue_category["id"]}
    )

    response = test_client.delete(f"/v1/catalogue-categories/{parent_catalogue_category['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be deleted"


def test_delete_catalogue_category_with_child_catalogue_items(test_client):
    """
    Test deleting a catalogue category with child catalogue items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)

    catalogue_category_id = response.json()["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    response = test_client.delete(f"/v1/catalogue-categories/{catalogue_category_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be deleted"


def test_get_catalogue_category(test_client):
    """
    Test getting a catalogue category.
    """
    # Parent
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    parent_catalogue_category = response.json()

    # Child
    response = test_client.post(
        "/v1/catalogue-categories", json={**CATALOGUE_CATEGORY_POST_B, "parent_id": parent_catalogue_category["id"]}
    )

    response = test_client.get(f"/v1/catalogue-categories/{response.json()['id']}")
    assert response.status_code == 200
    catalogue_category = response.json()
    assert catalogue_category == {**CATALOGUE_CATEGORY_POST_B_EXPECTED, "parent_id": parent_catalogue_category["id"]}


def test_get_catalogue_category_with_invalid_id(test_client):
    """
    Test getting a catalogue category with an invalid ID.
    """
    response = test_client.get("/v1/catalogue-categories/invalid")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_get_catalogue_category_with_non_existent_id(test_client):
    """
    Test getting a catalogue category with a non-existent ID.
    """
    response = test_client.get(f"/v1/catalogue-categories/{str(ObjectId())}")

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


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

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid parent_id given"


def test_get_catalogue_category_breadcrumbs_when_no_parent(test_client):
    """
    Test getting the breadcrumbs for a catalogue category with no parents
    """
    (category_c, *_) = _post_nested_catalogue_categories(test_client, [CATALOGUE_CATEGORY_POST_C])

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
    assert response.json()["detail"] == "Catalogue category with such ID was not found"


def test_get_catalogue_category_breadcrumbs_with_non_existent_id(test_client):
    """
    Test getting the breadcrumbs for a non existent catalogue category
    """
    response = test_client.get(f"/v1/catalogue-categories/{str(ObjectId())}/breadcrumbs")

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue category with such ID was not found"


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


def test_partial_update_catalogue_category_change_name_duplicate(test_client):
    """
    Test changing the name of a catalogue category to a name that already exists.
    """
    test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_A)
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_B)

    catalogue_category_patch = {"name": "Category A"}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A catalogue category with the same name already exists within the parent catalogue category"
    )


def test_partial_update_catalogue_category_change_name_has_child_catalogue_categories(test_client):
    """
    Test changing the name of a catalogue category which has child catalogue categories.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)
    catalogue_category_id = response.json()["id"]
    catalogue_category_post = {"name": "Category B", "is_leaf": False, "parent_id": catalogue_category_id}
    test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"name": "Category A"}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


def test_partial_update_catalogue_category_change_name_has_child_catalogue_items(test_client):
    """
    Test changing the name of a catalogue category which has child catalogue items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)

    catalogue_category_id = response.json()["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"name": "Category B"}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


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
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_from_non_leaf_to_leaf_without_catalogue_item_properties(test_client):
    """
    Test changing a catalogue category from non-leaf to leaf without supplying any catalogue item properties.
    """
    catalogue_category_post = {"name": "Category A", "is_leaf": False}
    response = test_client.post("/v1/catalogue-categories", json=catalogue_category_post)

    catalogue_category_patch = {"is_leaf": True}
    response = test_client.patch(f"/v1/catalogue-categories/{response.json()['id']}", json=catalogue_category_patch)

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        "id": ANY,
        "catalogue_item_properties": [],
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
        "catalogue_item_properties": [{"name": "Property A", "type": "number", "unit": "mm", "mandatory": False}],
    }
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


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
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        "id": ANY,
        "catalogue_item_properties": [],
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_from_leaf_to_non_leaf_has_child_catalogue_items(test_client):
    """
    Test changing a catalogue category with child catalogue items from leaf to non-leaf.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)

    catalogue_category_id = response.json()["id"]
    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"is_leaf": False}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


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

    assert response.status_code == 200
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        "id": ANY,
        "catalogue_item_properties": [],
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
    assert response.json() == {
        **catalogue_category_post,
        **catalogue_category_patch,
        "id": ANY,
        "code": "category-b",
    }


def test_partial_update_catalogue_category_change_parent_id_has_child_catalogue_categories(test_client):
    """
    Test moving a catalogue category with child categories to another parent catalogue category.
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
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


def test_partial_update_catalogue_category_change_parent_id_has_child_catalogue_items(test_client):
    """
    Test moving a catalogue category with child items to another parent catalogue category.
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
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {"parent_id": catalogue_category_a_id}
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_b_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


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
    assert response.json()["detail"] == "The specified parent catalogue category ID does not exist"


def test_partial_update_catalogue_category_change_parent_id_non_existent_id(test_client):
    """
    Test changing the parent ID of a catalogue category to a non-existent ID.
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
    catalogue_item_properties[1]["unit"] = None
    assert response.json() == {
        **catalogue_category_post,
        "catalogue_item_properties": catalogue_item_properties,
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


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
    catalogue_item_properties[0]["unit"] = None
    assert response.json() == {
        **catalogue_category_post,
        "catalogue_item_properties": catalogue_item_properties,
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


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
    catalogue_item_properties[1]["unit"] = None
    assert response.json() == {
        **catalogue_category_post,
        "catalogue_item_properties": catalogue_item_properties,
        "id": ANY,
        "code": "category-a",
        "parent_id": None,
    }


def test_partial_update_catalogue_category_change_catalogue_item_properties_has_child_catalogue_items(test_client):
    """
    Test changing the catalogue item properties when a catalogue category has child catalogue items.
    """
    response = test_client.post("/v1/catalogue-categories", json=CATALOGUE_CATEGORY_POST_C)
    catalogue_category_id = response.json()["id"]

    catalogue_item_post = {
        "catalogue_category_id": catalogue_category_id,
        "name": "Catalogue Item A",
        "description": "This is Catalogue Item A",
        "properties": [{"name": "Property B", "value": False}],
        "manufacturer": {
            "name": "Manufacturer A",
            "address": "1 Address, City, Country, Postcode",
            "web_url": "https://www.manufacturer-a.co.uk",
        },
    }
    test_client.post("/v1/catalogue-items", json=catalogue_item_post)

    catalogue_category_patch = {
        "catalogue_item_properties": [{"name": "Property B", "type": "string", "mandatory": False}]
    }
    response = test_client.patch(f"/v1/catalogue-categories/{catalogue_category_id}", json=catalogue_category_patch)

    assert response.status_code == 409
    assert response.json()["detail"] == "Catalogue category has child elements and cannot be updated"


def test_partial_update_catalogue_category_invalid_id(test_client):
    """
    Test updating a catalogue category with an invalid ID.
    """
    catalogue_category_patch = {"name": "Category A", "is_leaf": False}

    response = test_client.patch("/v1/catalogue-categories/invalid", json=catalogue_category_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"


def test_partial_update_catalogue_category_non_existent_id(test_client):
    """
    Test updating a catalogue category with a non-existent ID.
    """
    catalogue_category_patch = {"name": "Category A", "is_leaf": False}

    response = test_client.patch(f"/v1/catalogue-categories/{str(ObjectId())}", json=catalogue_category_patch)

    assert response.status_code == 404
    assert response.json()["detail"] == "A catalogue category with such ID was not found"
