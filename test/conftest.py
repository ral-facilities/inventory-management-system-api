"""
Module for providing pytest testing configuration.
"""

from typing import Optional

from bson import ObjectId


def add_ids_to_properties(properties_with_ids: Optional[list], properties_without_ids: list):
    """
    A tests method for adding the IDs from the properties in `properties_with_ids` as the IDs to the properties in
    `properties_without_ids` based on matching names. Unique IDs are generated for each property if no
    `properties_with_ids` are provided. Additionally, unique IDs are generated for each unit if the unit value
    is not None.

    :param properties_with_ids: The list of properties with IDs. These are typically the catalogue category properties.
    :param properties_without_ids: The list of properties without IDs. These can be catalogue category, catalogue item
                                   or item properties.
    :return: The list of properties with the added IDs.
    """
    properties = []
    for property_without_id in properties_without_ids:
        prop_id = None
        unit_id = None

        if properties_with_ids:
            # Match up property and unit IDs
            for property_with_id in properties_with_ids:
                if property_with_id["name"] == property_without_id["name"]:
                    prop_id = property_with_id["id"]

                if property_with_id.get("unit") == property_without_id.get("unit"):
                    unit_id = property_with_id["unit_id"]
        else:
            # Generate a new property id and lookup the unit id from the units list
            prop_id = str(ObjectId())

            if property_without_id.get("unit") is not None:
                if property_without_id.get("unit_id") is None:
                    unit_id = str(ObjectId())
                else:
                    unit_id = property_without_id["unit_id"]

        properties.append({**property_without_id, "id": prop_id, "unit_id": unit_id})

    return properties
