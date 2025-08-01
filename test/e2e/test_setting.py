"""
End-to-End tests involving settings.
"""

# Expect some duplicate code inside tests as the tests for the different entities can be very similar
# pylint: disable=duplicate-code
# pylint: disable=too-many-ancestors

from test.e2e.conftest import E2ETestHelpers
from test.e2e.test_catalogue_item import GetDSL as CatalogueItemGetDSL
from test.e2e.test_item import DeleteDSL as ItemDeleteDSL
from test.mock_data import (
    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES,
    CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES,
    ITEM_DATA_REQUIRED_VALUES_ONLY,
    SETTING_SPARES_DEFINITION_IN_DATA_STORAGE,
    SETTING_SPARES_DEFINITION_IN_DATA_STORAGE_OR_OPERATIONAL,
    SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
    SYSTEM_TYPE_GET_DATA_OPERATIONAL,
    SYSTEM_TYPE_GET_DATA_STORAGE,
)
from typing import Optional

import pytest
from httpx import Response
from pymongo.database import Database

from inventory_management_system_api.core.database import get_database


class SparesDefinitionDSL(ItemDeleteDSL, CatalogueItemGetDSL):
    """Base class for spares definition tests."""

    _database: Database
    _system_type_map: dict[str, str]
    _catalogue_item_ids: list[str]
    _post_responses_catalogue_items: list[Response]

    @pytest.fixture(autouse=True)
    def setup_spares_definition_dsl(self):
        """Setup fixtures"""

        self._database = get_database()

    def set_spares_definition(self, spares_definition_in_data: dict) -> None:
        """
        Sets the spares definition inside the database.

        :param spares_definition_in_data: Dictionary containing the spares definition data to insert into the database.
        """

        self._database.settings.update_one(
            {"_id": spares_definition_in_data["_id"]}, {"$set": spares_definition_in_data}, upsert=True
        )

    def post_system_with_type_id(self, type_id: str) -> Optional[str]:
        """
        Utility method that posts a system with a specified type ID.

        :param type_id: Type ID of the system to create.
        """

        system_id = self.post_system(
            {
                **SYSTEM_POST_DATA_REQUIRED_VALUES_ONLY,
                # Avoid duplicate error
                "name": f"System {len(self._system_type_map)}",
                "type_id": type_id,
            }
        )
        self._system_type_map[type_id] = system_id
        return system_id

    def post_item_in_system_with_type_id(self, system_type_id: str) -> Optional[str]:
        """
        Utility method that posts an item inside a system with the specified type ID.

        :param system_type_id: The type ID of the system the item should be in.
        :return: ID of the created item (or `None` if not successful).
        """

        # First ensure there is a system to place the item in
        system_id = self._system_type_map.get(system_type_id)
        if not system_id:
            system_id = self.post_system_with_type_id(system_type_id)

        # Create an item in the chosen system and current catalogue category
        self.system_id = system_id
        return self.post_item(ITEM_DATA_REQUIRED_VALUES_ONLY)

    def post_items_and_prerequisites_with_system_types(self, system_type_ids_lists: list[list[str]]) -> None:
        """
        Utility method that posts a series of catalogue items and items as well as their prerequisite manufacturer,
        catalogue category and units where the items are within systems with a given series of system types.

        :param system_type_ids_lists: List containing a list of system type IDs. Each outer list represents a separate
                                      catalogue item to create and each value in the inner represents an item to create
                                      and gives the system type ID of the system in which the item should be placed.
        """

        self._system_type_map: dict[str, str] = {}
        self._catalogue_item_ids = []
        self._post_responses_catalogue_items = []

        # Create one catalogue item for each list in `system_type_ids_lists`
        for i, system_type_ids in enumerate(system_type_ids_lists):
            # Create the catalogue item, but ensure only posting the pre-requisites once
            if i == 0:
                catalogue_item_id = self.post_catalogue_item_and_prerequisites_with_properties(
                    CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES
                )
            else:
                catalogue_item_id = self.post_catalogue_item(CATALOGUE_ITEM_DATA_WITH_ALL_PROPERTIES)
            self._catalogue_item_ids.append(catalogue_item_id)
            self._post_responses_catalogue_items.append(self._post_response_catalogue_item)

            # Create one item for each system type ID in system_type_ids
            for system_type_id in system_type_ids:
                self.post_item_in_system_with_type_id(system_type_id)

    def patch_item_system_id_to_one_with_type_id(self, item_id: str, system_type_id: str) -> None:
        """
        Utility method that patches an item's `system_id` to one that has the specified type ID.

        :param item_id: ID of the item to patch.
        :param system_type_id: Type ID of the system the item should be put in.
        """

        # First ensure there is a system to place the item in
        system_id = self._system_type_map.get(system_type_id)
        if not system_id:
            system_id = self.post_system_with_type_id(system_type_id)
        self.patch_item(item_id, {"system_id": system_id})

    def check_catalogue_item_spares(self, expected_number_of_spares_list: list[Optional[int]]) -> None:
        """
        Checks that the catalogue items created via `post_items_and_prerequisites_with_system_types` have specific
        expected `number_of_spares` values.

        :param expected_number_of_spares_list: List of the expected values of the `number_of_spares` field, one for each
                                               catalogue item that was created.
        """

        for i, (catalogue_item_id, expected_number_of_spares) in enumerate(
            zip(self._catalogue_item_ids, expected_number_of_spares_list)
        ):
            self.get_catalogue_item(catalogue_item_id)
            self.check_get_catalogue_item_success(
                {**CATALOGUE_ITEM_GET_DATA_WITH_ALL_PROPERTIES, "number_of_spares": expected_number_of_spares}
            )

            # Also ensure the created and modified times are not changed
            E2ETestHelpers.check_created_and_modified_times_not_updated(
                self._post_responses_catalogue_items[i], self._get_response_catalogue_item
            )


class TestSparesDefinitionDSL(SparesDefinitionDSL):
    """Tests for spares definition."""

    def test_create_catalogue_item_after_spares_definition_set(self):
        """Test creating a catalogue item after the spares definition is set."""

        self.set_spares_definition(SETTING_SPARES_DEFINITION_IN_DATA_STORAGE)

        # Create a single catalogue item with no items, spares should be 0
        self.post_items_and_prerequisites_with_system_types([[]])
        self.check_catalogue_item_spares([0])

    def test_create_item_after_spares_definition_set(self):
        """Test creating an item after the spares definition is set."""

        self.set_spares_definition(SETTING_SPARES_DEFINITION_IN_DATA_STORAGE)

        # Create two catalogue items, the first with one item (no spares) and the second with two items (one spare)
        self.post_items_and_prerequisites_with_system_types(
            [
                [SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]],
                [SYSTEM_TYPE_GET_DATA_STORAGE["id"], SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]],
            ]
        )
        self.check_catalogue_item_spares([0, 1])

        # Add one new item to the second catalogue item and ensure only it is updated
        self.post_item_in_system_with_type_id(SYSTEM_TYPE_GET_DATA_STORAGE["id"])
        self.check_catalogue_item_spares([0, 2])

    def test_create_item_after_spares_definition_set_with_multiple_types(self):
        """Test creating an item after the spares definition is set to one with multiple system type IDs in it.
        (This test is not repeated for update/delete as the logic used is the same)"""

        self.set_spares_definition(SETTING_SPARES_DEFINITION_IN_DATA_STORAGE_OR_OPERATIONAL)

        # Create two catalogue items, the first with one item (no spares) and the second with two items (one spare)
        self.post_items_and_prerequisites_with_system_types(
            [
                [SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]],
                [SYSTEM_TYPE_GET_DATA_STORAGE["id"], SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]],
            ]
        )
        self.check_catalogue_item_spares([1, 2])

        # Add one new item to the second catalogue item and ensure only it is updated
        self.post_item_in_system_with_type_id(SYSTEM_TYPE_GET_DATA_STORAGE["id"])
        self.check_catalogue_item_spares([1, 3])

    def test_update_item_system_id_after_spares_definition_set(self):
        """Test updating an item's system ID after the spares definition is set."""

        self.set_spares_definition(SETTING_SPARES_DEFINITION_IN_DATA_STORAGE)

        # Create two catalogue items, the first with one item (no spares) and the second with two items (one spare)
        self.post_items_and_prerequisites_with_system_types(
            [[SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]], [SYSTEM_TYPE_GET_DATA_STORAGE["id"]]]
        )
        item_id = self.post_item_in_system_with_type_id(SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"])
        self.check_catalogue_item_spares([0, 1])

        # Update the item's `system_id` so it becomes a spare and ensure only its catalogue item is updated
        self.patch_item_system_id_to_one_with_type_id(item_id, SYSTEM_TYPE_GET_DATA_STORAGE["id"])
        self.check_catalogue_item_spares([0, 2])

    def test_delete_item_after_spares_definition_set(self):
        """Test deleting an item after the spares definition is set."""

        self.set_spares_definition(SETTING_SPARES_DEFINITION_IN_DATA_STORAGE)

        # Create two catalogue items, the first with one item (no spares) and the second with two items (both spare)
        self.post_items_and_prerequisites_with_system_types(
            [[SYSTEM_TYPE_GET_DATA_OPERATIONAL["id"]], [SYSTEM_TYPE_GET_DATA_STORAGE["id"]]]
        )
        item_id = self.post_item_in_system_with_type_id(SYSTEM_TYPE_GET_DATA_STORAGE["id"])
        self.check_catalogue_item_spares([0, 2])

        # Delete the second spare item and ensure only its catalogue item is updated
        self.delete_item(item_id)
        self.check_catalogue_item_spares([0, 1])
