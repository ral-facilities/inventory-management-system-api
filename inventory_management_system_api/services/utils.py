"""
Collection of some utility functions used by services
"""

import logging
import re
from typing import Dict, List, Union

from inventory_management_system_api.core.exceptions import (
    DuplicateCatalogueCategoryPropertyNameError,
    InvalidPropertyTypeError,
    MissingMandatoryProperty,
)
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryPropertyOut
from inventory_management_system_api.schemas.catalogue_category import CatalogueCategoryPostPropertySchema
from inventory_management_system_api.schemas.catalogue_item import PropertyPostSchema

logger = logging.getLogger()


def generate_code(name: str, entity_type: str) -> str:
    """
    Generate a code for an entity based on its name. This is used to maintain uniqueness and prevent
    duplicates. (E.g. a duplicate subcategories within a category)

    The code is generated by converting the name to lowercase and replacing spaces with hyphens. Leading and
    trailing spaces are removed, and consecutive spaces are replaced with a single hyphen

    :param name: The name of the entity
    :param entity_type: Name of the entity type e.g. catalogue category/system (Used for logging)
    :return: The generated code for the entity
    """
    logger.info("Generating code for the %s based on its name", entity_type)
    name = name.lower().strip()
    return re.sub(r"\s+", "-", name)


def check_duplicate_property_names(
    properties: list[CatalogueCategoryPostPropertySchema | CatalogueCategoryPropertyOut],
) -> None:
    """
    Go through a list of properties to check for any duplicate names during creation of a catalogue
    category or an addition of a property later on.

    :param properties: The supplied properties
    :raises DuplicateCategoryPropertyName: If a duplicate property name is found.
    """
    logger.info("Checking for duplicate property names")
    seen_property_names = set()
    for prop in properties:
        property_name = prop.name.lower().strip()
        if property_name in seen_property_names:
            raise DuplicateCatalogueCategoryPropertyNameError(f"Duplicate property name: {prop.name.strip()}")
        seen_property_names.add(property_name)


def process_properties(
    defined_properties: List[CatalogueCategoryPropertyOut],
    supplied_properties: List[PropertyPostSchema],
) -> List[Dict]:
    """
    Process and validate supplied properties based on the defined properties. It checks for missing mandatory, filters
    the matching properties, adds the property units, and finally validates the property values.

    The `supplied_properties_dict` dictionary may get modified as part of the processing and validation.

    :param defined_properties: The list of defined property objects.
    :param supplied_properties: The list of supplied property objects.
    :return: A list of processed and validated supplied properties.
    """
    # Convert properties to dictionaries for easier lookups
    defined_properties_dict = _create_properties_dict(defined_properties)
    supplied_properties_dict = _create_properties_dict(supplied_properties)

    # Some mandatory properties may not have been supplied
    _check_missing_mandatory_properties(defined_properties_dict, supplied_properties_dict)
    # Some non-mandatory properties may not have been supplied
    supplied_properties_dict = _merge_non_mandatory_properties(defined_properties_dict, supplied_properties_dict)
    # Supplied properties do not have names as we can't trust they would be correct
    _add_property_names(defined_properties_dict, supplied_properties_dict)
    # Supplied properties do not have units as we can't trust they would be correct
    _add_property_units(defined_properties_dict, supplied_properties_dict)
    # The values of the supplied properties may not be of the expected types
    _validate_property_values(defined_properties_dict, supplied_properties_dict)

    return list(supplied_properties_dict.values())


def _create_properties_dict(
    properties: Union[List[CatalogueCategoryPropertyOut], List[PropertyPostSchema]]
) -> Dict[str, Dict]:
    """
    Convert a list of property objects into a dictionary where the keys are the catalogue item
    property IDs and the values are the property dictionaries.

    :param properties: The list of property objects.
    :return: A dictionary where the keys are the property IDs and the values are the catalogue item
             property dictionaries.
    """
    return {prop.id: prop.model_dump() for prop in properties}


def _add_property_names(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Add the names to the supplied properties.

    The supplied properties only contain an ID and value so the names from the defined properties in the database
    are added to the supplied properties. This means that this method modifies the `supplied_properties` dictionary.

    :param defined_properties: The defined properties stored as part of the catalogue category in the
        database.
    :param supplied_properties: The supplied properties.
    """
    logger.info("Adding the names to the supplied properties")
    for supplied_property_id, supplied_property in supplied_properties.items():
        supplied_property["name"] = defined_properties[supplied_property_id]["name"]


def _add_property_units(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Add the units to the supplied properties.

    The supplied properties only contain an ID and value so the units from the defined properties in the database
    are added to the supplied properties. This means that this method modifies the `supplied_properties` dictionary.

    :param defined_properties: The defined properties stored as part of the catalogue category in the
                               database.
    :param supplied_properties: The supplied properties.
    """
    logger.info("Adding the units to the supplied properties")
    for supplied_property_name, supplied_property in supplied_properties.items():
        supplied_property["unit_id"] = defined_properties[supplied_property_name]["unit_id"]
        supplied_property["unit"] = defined_properties[supplied_property_name]["unit"]


def _validate_property_value(defined_property: Dict, supplied_property: Dict) -> None:
    """
    Validates that a given property value a valid type and is within the defined allowed_values (if specified) and
    raises and error if it is not.

    :param defined_property: Definition of the property from the catalogue category
    :param supplied_property: Supplied property dictionary
    :raises InvalidPropertyTypeError: If the supplied property value is found to either be an
                                      invalid type, or not an allowed value
    """

    defined_property_type = defined_property["type"]
    defined_property_allowed_values = defined_property["allowed_values"]
    defined_property_mandatory = defined_property["mandatory"]

    supplied_property_id = supplied_property["id"]
    supplied_property_value = supplied_property["value"]

    # Do not type check a value of None
    if supplied_property_value is None:
        if defined_property_mandatory:
            raise InvalidPropertyTypeError(f"Mandatory property with ID '{supplied_property_id}' cannot be None.")
    else:
        if not CatalogueCategoryPostPropertySchema.is_valid_property_type(
            defined_property_type, supplied_property_value
        ):
            raise InvalidPropertyTypeError(
                f"Invalid value type for property with ID '{supplied_property_id}'. Expected type: "
                f"{defined_property_type}."
            )

        # Verify the given property is one of the allowed based on the type of allowed_values defined
        if defined_property_allowed_values is not None and defined_property_allowed_values["type"] == "list":
            values = defined_property_allowed_values["values"]
            if supplied_property_value not in values:
                raise InvalidPropertyTypeError(
                    f"Invalid value for property with ID '{supplied_property_id}'. Expected one of "
                    f"{', '.join([str(value) for value in values])}."
                )


def _validate_property_values(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Validate the values of the supplied properties against the expected property types. Raise an error if the type
    of the supplied value does not match the expected type.

    :param defined_properties: The defined properties stored as part of the catalogue category in the
                               database.
    :param supplied_properties: The supplied properties.
    :raises InvalidPropertyTypeError: If the any of the types of the supplied values does not match the
                                      expected type.
    """
    logger.info("Validating the values of the supplied properties against the expected property types")
    for supplied_property_id, supplied_property in supplied_properties.items():
        _validate_property_value(defined_properties[supplied_property_id], supplied_property)


def _check_missing_mandatory_properties(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Check for mandatory properties that are missing/have not been supplied. Raise an error as soon
    as a mandatory property is found to be missing.

    :param defined_properties: The defined properties stored as part of the catalogue category in the
        database.
    :param supplied_properties: The supplied properties.
    :raises MissingMandatoryProperty: If a mandatory property is missing/not supplied.
    """
    logger.info("Checking for missing mandatory property")
    for defined_property_id, defined_property in defined_properties.items():
        if defined_property["mandatory"] and defined_property_id not in supplied_properties:
            raise MissingMandatoryProperty(f"Missing mandatory property with ID: '{defined_property_id}'")


def _merge_non_mandatory_properties(
    defined_properties: Dict[str, Dict], supplied_properties: Dict[str, Dict]
) -> Dict[str, Dict]:
    """
    Merges in any non-mandatory properties that have not been supplied, giving them a value of None, using
    the same order as they are defined. Any extra undefined properties that get supplied will be ignored.

    :param defined_properties: The defined properties stored as part of the catalogue category in the
                               database.
    :param supplied_properties: The supplied properties.
    :return: The supplied properties combined with any unsupplied non mandatory properties (with a value of None) in
             the order they are defined.
    """
    logger.info("Merging any missing defined non-mandatory properties with the supplied properties")

    properties: Dict[str, Dict] = {}
    for defined_property_id, defined_property in defined_properties.items():
        supplied_property = supplied_properties.get(defined_property_id)
        if supplied_property is not None:
            properties[defined_property_id] = supplied_property
        elif not defined_property["mandatory"]:
            properties[defined_property_id] = {"id": defined_property_id, "value": None}
    return properties
