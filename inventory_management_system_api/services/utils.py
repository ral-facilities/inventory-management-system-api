"""
Collection of some utility functions used by services
"""

import logging
import re
from typing import Dict, List, Union

from inventory_management_system_api.core.exceptions import (
    InvalidCatalogueItemPropertyTypeError,
    MissingMandatoryCatalogueItemProperty,
)
from inventory_management_system_api.models.catalogue_category import CatalogueItemProperty
from inventory_management_system_api.schemas.catalogue_category import CatalogueItemPropertySchema
from inventory_management_system_api.schemas.catalogue_item import PropertyPostRequestSchema

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


def process_catalogue_item_properties(
    defined_properties: List[CatalogueItemProperty],
    supplied_properties: List[PropertyPostRequestSchema],
) -> List[Dict]:
    """
    Process and validate supplied catalogue item properties based on defined catalogue item properties. It checks
    for missing mandatory catalogue item properties, filters the matching catalogue item properties, adds the property
    units, and finally validates the property values.

    The `supplied_properties_dict` dictionary may get modified as part of the processing and validation.

    :param defined_properties: The list of defined catalogue item property objects.
    :param supplied_properties: The list of supplied catalogue item property objects.
    :return: A list of processed and validated supplied catalogue item properties.
    """
    # Convert properties to dictionaries for easier lookups
    defined_properties_dict = _create_catalogue_item_properties_dict(defined_properties)
    supplied_properties_dict = _create_catalogue_item_properties_dict(supplied_properties)

    # Some mandatory catalogue item properties may not have been supplied
    _check_missing_mandatory_catalogue_item_properties(defined_properties_dict, supplied_properties_dict)
    # Catalogue item properties that have not been defined may have been supplied
    supplied_properties_dict = _filter_matching_catalogue_item_properties(
        defined_properties_dict, supplied_properties_dict
    )
    # Supplied catalogue item properties do not have units as we can't trust they would be correct
    _add_catalogue_item_property_units(defined_properties_dict, supplied_properties_dict)
    # The values of the supplied catalogue item properties may not be of the expected types
    _validate_catalogue_item_property_values(defined_properties_dict, supplied_properties_dict)

    return list(supplied_properties_dict.values())


def _create_catalogue_item_properties_dict(
    catalogue_item_properties: Union[List[CatalogueItemProperty], List[PropertyPostRequestSchema]]
) -> Dict[str, Dict]:
    """
    Convert a list of catalogue item property objects into a dictionary where the keys are the catalogue item
    property names and the values are the catalogue item property dictionaries.

    :param catalogue_item_properties: The list of catalogue item property objects.
    :return: A dictionary where the keys are the catalogue item property names and the values are the catalogue item
        property dictionaries.
    """
    return {
        catalogue_item_property.name: catalogue_item_property.model_dump()
        for catalogue_item_property in catalogue_item_properties
    }


def _add_catalogue_item_property_units(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Add the units to the supplied properties.

    The supplied properties only contain a name and value so the units from the defined properties in the database
    are added to the supplied properties. This means that this method modifies the `supplied_properties` dictionary.

    :param defined_properties: The defined catalogue item properties stored as part of the catalogue category in the
        database.
    :param supplied_properties: The supplied catalogue item properties.
    """
    logger.info("Adding the units to the supplied properties")
    for supplied_property_name, supplied_property in supplied_properties.items():
        supplied_property["unit"] = defined_properties[supplied_property_name]["unit"]


def _validate_catalogue_item_property_value(defined_property: Dict, supplied_property: Dict) -> None:
    """
    Validates that a given property value a valid type and is within the defined allowed_values (if specified) and
    raises and error if it is not.

    :param defined_property: Definition of the property from the catalogue category
    :param supplied_property: Supplied property dictionary
    :raises InvalidCatalogueItemPropertyTypeError: If the supplied property value is found to either be an
                                                   invalid type, or not an allowed value
    """

    defined_property_type = defined_property["type"]
    defined_property_allowed_values = defined_property["allowed_values"]
    defined_property_mandatory = defined_property["mandatory"]

    supplied_property_name = supplied_property["name"]
    supplied_property_value = supplied_property["value"]

    # Do not type check a value of None
    if supplied_property_value is None:
        if defined_property_mandatory:
            raise InvalidCatalogueItemPropertyTypeError(
                f"Mandatory catalogue item property '{supplied_property_name}' cannot be None."
            )
    else:
        if not CatalogueItemPropertySchema.is_valid_property_type(defined_property_type, supplied_property_value):
            raise InvalidCatalogueItemPropertyTypeError(
                f"Invalid value type for catalogue item property '{supplied_property_name}'. "
                f"Expected type: {defined_property_type}."
            )

        # Verify the given property is one of the allowed based on the type of allowed_values defined
        if defined_property_allowed_values is not None and defined_property_allowed_values["type"] == "list":
            values = defined_property_allowed_values["values"]
            if supplied_property_value not in values:
                raise InvalidCatalogueItemPropertyTypeError(
                    f"Invalid value for catalogue item property '{supplied_property_name}'. Expected one of "
                    f"{', '.join([str(value) for value in values])}."
                )


def _validate_catalogue_item_property_values(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Validate the values of the supplied properties against the expected property types. Raise an error if the type
    of the supplied value does not match the expected type.

    :param defined_properties: The defined catalogue item properties stored as part of the catalogue category in the
                               database.
    :param supplied_properties: The supplied catalogue item properties.
    :raises InvalidCatalogueItemPropertyTypeError: If the any of the types of the supplied values does not match the
                                                   expected type.
    """
    logger.info("Validating the values of the supplied properties against the expected property types")
    for supplied_property_name, supplied_property in supplied_properties.items():
        _validate_catalogue_item_property_value(defined_properties[supplied_property_name], supplied_property)


def _check_missing_mandatory_catalogue_item_properties(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> None:
    """
    Check for mandatory catalogue item properties that are missing/ have not been supplied. Raise an error as soon
    as a mandatory property is found to be missing.

    :param defined_properties: The defined catalogue item properties stored as part of the catalogue category in the
        database.
    :param supplied_properties: The supplied catalogue item properties.
    :raises MissingMandatoryCatalogueItemProperty: If a mandatory catalogue item property is missing/ not supplied.
    """
    logger.info("Checking for missing mandatory catalogue item properties")
    for defined_property_name, defined_property in defined_properties.items():
        if defined_property["mandatory"] and defined_property_name not in supplied_properties:
            raise MissingMandatoryCatalogueItemProperty(
                f"Missing mandatory catalogue item property: '{defined_property_name}'"
            )


def _filter_matching_catalogue_item_properties(
    defined_properties: Dict[str, Dict],
    supplied_properties: Dict[str, Dict],
) -> Dict[str, Dict]:
    """
    Filter through the supplied properties and extract the ones matching the defined properties.

    :param defined_properties: The defined catalogue item properties stored as part of the catalogue category in the
        database.
    :param supplied_properties: The supplied catalogue item properties.
    :return: The supplied properties that are matching the defined properties.
    """
    logger.info("Extracting the supplied properties that are matching the defined properties")
    matching_properties = {}
    for supplied_property_name, supplied_property in supplied_properties.items():
        if supplied_property_name in defined_properties:
            matching_properties[supplied_property_name] = supplied_property

    return matching_properties
