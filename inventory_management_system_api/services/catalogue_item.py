"""
Module for providing a service for managing catalogue items using the `CatalogueItemRepo` and `CatalogueCategoryRepo`
repositories.
"""

import logging
from typing import Annotated, Any, List, Optional

from fastapi import Depends
from pydantic import ValidationError
from pydantic_core import ErrorDetails, InitErrorDetails

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import (
    ChildElementsExistError,
    InvalidActionError,
    InvalidObjectIdError,
    MissingRecordError,
    NonLeafCatalogueCategoryError,
    ReplacementForObsoleteCatalogueItemError,
)
from inventory_management_system_api.core.object_storage_api_client import ObjectStorageAPIClient
from inventory_management_system_api.models.catalogue_category import CatalogueCategoryPropertyOut
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.repositories.manufacturer import ManufacturerRepo
from inventory_management_system_api.repositories.setting import SettingRepo
from inventory_management_system_api.schemas.catalogue_category import (
    CatalogueCategoryPostPropertySchema,
    CatalogueCategoryPropertyType,
)
from inventory_management_system_api.schemas.catalogue_item import (
    CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS,
    CatalogueItemPatchSchema,
    CatalogueItemPostSchema,
    PropertyPostSchema,
)
from inventory_management_system_api.services import utils

logger = logging.getLogger()


class CatalogueItemService:
    """
    Service for managing catalogue items.
    """

    def __init__(
        self,
        catalogue_item_repository: Annotated[CatalogueItemRepo, Depends(CatalogueItemRepo)],
        catalogue_category_repository: Annotated[CatalogueCategoryRepo, Depends(CatalogueCategoryRepo)],
        manufacturer_repository: Annotated[ManufacturerRepo, Depends(ManufacturerRepo)],
        setting_repository: Annotated[SettingRepo, Depends(SettingRepo)],
    ) -> None:
        """
        Initialise the `CatalogueItemService` with `CatalogueItemRepo`, `CatalogueCategoryRepo` and `ManufacturerRepo`
        repos.

        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        :param manufacturer_repository: The `ManufacturerRepo` repository to use.
        :param setting_repository: The `SettingRepo` repository to use.
        """
        self._catalogue_item_repository = catalogue_item_repository
        self._catalogue_category_repository = catalogue_category_repository
        self._manufacturer_repository = manufacturer_repository
        self._setting_repository = setting_repository

    def create(self, catalogue_item: CatalogueItemPostSchema) -> CatalogueItemOut:
        """
        Create a new catalogue item.

        The method checks if the catalogue category exists in the database and raises a `MissingRecordError` if it does
        not. It also checks if the category is not a leaf category and raises a `NonLeafCatalogueCategoryError` if it
        is. It then processes the properties.

        :param catalogue_item: The catalogue item to be created.
        :return: The created catalogue item.
        :raises MissingRecordError: If the catalogue category does not exist, and/or the manufacturer does not exist
        :raises NonLeafCatalogueCategoryError: If the catalogue category is not a leaf category.
        """
        catalogue_category_id = catalogue_item.catalogue_category_id
        catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID '{catalogue_category_id}'")

        if catalogue_category.is_leaf is False:
            raise NonLeafCatalogueCategoryError("Cannot add catalogue item to a non-leaf catalogue category")

        manufacturer_id = catalogue_item.manufacturer_id
        manufacturer = self._manufacturer_repository.get(manufacturer_id)
        if not manufacturer:
            raise MissingRecordError(f"No manufacturer found with ID '{manufacturer_id}'")

        obsolete_replacement_catalogue_item_id = catalogue_item.obsolete_replacement_catalogue_item_id
        if obsolete_replacement_catalogue_item_id and not self._catalogue_item_repository.get(
            obsolete_replacement_catalogue_item_id
        ):
            raise MissingRecordError(f"No catalogue item found with ID '{obsolete_replacement_catalogue_item_id}'")

        defined_properties = catalogue_category.properties
        supplied_properties = catalogue_item.properties if catalogue_item.properties else []
        supplied_properties = utils.process_properties(defined_properties, supplied_properties)

        # Obtain current spares definition to determine if the number of spares should be None (when its undefined)
        # or 0 (when its defined)
        spares_definition = self._setting_repository.get(SparesDefinitionOut)

        return self._catalogue_item_repository.create(
            CatalogueItemIn(
                **{
                    **catalogue_item.model_dump(),
                    "properties": supplied_properties,
                },
                number_of_spares=0 if spares_definition else None,
            )
        )

    def get(self, catalogue_item_id: str) -> Optional[CatalogueItemOut]:
        """
        Retrieve a catalogue item by its ID.

        :param catalogue_item_id: The ID of the catalogue item to retrieve.
        :return: The retrieved catalogue item, or `None` if not found.
        """
        return self._catalogue_item_repository.get(catalogue_item_id)

    def list(self, catalogue_category_id: Optional[str]) -> List[CatalogueItemOut]:
        """
        Retrieve all catalogue items.

        :param catalogue_category_id:  The ID of the catalogue category to filter catalogue items by.
        :return: A list of catalogue items, or an empty list if no catalogue items are retrieved.
        """
        return self._catalogue_item_repository.list(catalogue_category_id)

    # pylint:disable=too-many-branches
    # pylint:disable=too-many-locals
    def update(self, catalogue_item_id: str, catalogue_item: CatalogueItemPatchSchema) -> CatalogueItemOut:
        """
        Update a catalogue item by its ID.

        If the properties are being updated, it also processes them.

        :param catalogue_item_id: The ID of the catalogue item to update.
        :param catalogue_item: The catalogue item containing the fields that need to be updated.
        :raises MissingRecordError: If the catalogue item doesn't exist.
        :raises ChildElementsExistError: If updating a property that is not allowed to be edited when there are child
                                         entities, and there are child entities currently.
        :raises MissingRecordError: If the catalogue category doesn't exist.
        :raises NonLeafCatalogueCategoryError: If the catalogue category isn't a leaf category.
        :raises InvalidActionError: If moving the catalogue item between categories with different properties without
                                    explicitly specifying them.
        :raises MissingRecordError: If the manufacturer doesn't exist.
        :raises MissingRecordError: If the obsolete replacement catalogue item doesn't exist.
        :return: The updated catalogue item.
        """
        update_data = catalogue_item.model_dump(exclude_unset=True)

        stored_catalogue_item = self.get(catalogue_item_id)
        if not stored_catalogue_item:
            raise MissingRecordError(f"No catalogue item found with ID '{catalogue_item_id}'")

        # If any of these, need to ensure the catalogue item has no child elements
        if any(key in update_data for key in CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS):
            if self._catalogue_item_repository.has_child_elements(catalogue_item_id):
                raise ChildElementsExistError(
                    f"Catalogue item with ID '{catalogue_item_id}' has child elements and cannot be updated"
                )

        catalogue_category = None
        if (
            "catalogue_category_id" in update_data
            and catalogue_item.catalogue_category_id != stored_catalogue_item.catalogue_category_id
        ):
            catalogue_category = self._catalogue_category_repository.get(catalogue_item.catalogue_category_id)
            if not catalogue_category:
                raise MissingRecordError(
                    f"No catalogue category found with ID '{catalogue_item.catalogue_category_id}'"
                )

            if catalogue_category.is_leaf is False:
                raise NonLeafCatalogueCategoryError("Cannot add catalogue item to a non-leaf catalogue category")

            # If the catalogue category ID is updated but no catalogue item properties are supplied then we
            # only allow the item to be moved provided that the two categories expect exactly the same properties
            if "properties" not in update_data:
                current_catalogue_category = self._catalogue_category_repository.get(
                    stored_catalogue_item.catalogue_category_id
                )

                # Ensure the properties are the same in every way ignoring the ids
                invalid_action_error_message = (
                    "Cannot move catalogue item to a category with different properties without "
                    "specifying the new properties"
                )
                if len(current_catalogue_category.properties) != len(catalogue_category.properties):
                    raise InvalidActionError(invalid_action_error_message)

                old_to_new_id_map = {}
                for current_catalogue_category_prop, catalogue_category_prop in zip(
                    current_catalogue_category.properties, catalogue_category.properties
                ):
                    if not current_catalogue_category_prop.is_equal_without_id(catalogue_category_prop):
                        raise InvalidActionError(invalid_action_error_message)
                    old_to_new_id_map[current_catalogue_category_prop.id] = catalogue_category_prop.id

                # The IDs of the properties need to be updated to those of the new catalogue category
                for stored_catalogue_item_prop in stored_catalogue_item.properties:
                    stored_catalogue_item_prop.id = old_to_new_id_map[stored_catalogue_item_prop.id]

        if "manufacturer_id" in update_data and catalogue_item.manufacturer_id != stored_catalogue_item.manufacturer_id:
            manufacturer = self._manufacturer_repository.get(catalogue_item.manufacturer_id)
            if not manufacturer:
                raise MissingRecordError(f"No manufacturer found with ID '{catalogue_item.manufacturer_id}'")

        if "obsolete_replacement_catalogue_item_id" in update_data:
            obsolete_replacement_catalogue_item_id = catalogue_item.obsolete_replacement_catalogue_item_id
            if (
                obsolete_replacement_catalogue_item_id
                and obsolete_replacement_catalogue_item_id
                != stored_catalogue_item.obsolete_replacement_catalogue_item_id
                and not self._catalogue_item_repository.get(obsolete_replacement_catalogue_item_id)
            ):
                raise MissingRecordError(f"No catalogue item found with ID '{obsolete_replacement_catalogue_item_id}'")

        if "properties" in update_data:
            if not catalogue_category:
                catalogue_category = self._catalogue_category_repository.get(
                    stored_catalogue_item.catalogue_category_id
                )

            defined_properties = catalogue_category.properties
            supplied_properties = catalogue_item.properties
            update_data["properties"] = utils.process_properties(defined_properties, supplied_properties)

        return self._catalogue_item_repository.update(
            catalogue_item_id,
            CatalogueItemIn(**{**stored_catalogue_item.model_dump(), **update_data}),
        )

    def delete(self, catalogue_item_id: str, access_token: Optional[str] = None) -> None:
        """
        Delete a catalogue item by its ID.

        :param catalogue_item_id: The ID of the catalogue item to delete.
        :param access_token: The JWT access token to use for auth with the Object Storage API if object storage enabled.
        :raises ChildElementsExistError: If the catalogue item has child elements.
        :raises ReplacementForObsoleteCatalogueItemError: If the catalogue item is the replacement for at least one
                                                          obsolete catalogue item.
        """
        if self._catalogue_item_repository.has_child_elements(catalogue_item_id):
            raise ChildElementsExistError(
                f"Catalogue item with ID '{catalogue_item_id}' has child elements and cannot be deleted"
            )

        if self._catalogue_item_repository.is_replacement_for(catalogue_item_id):
            raise ReplacementForObsoleteCatalogueItemError(
                f"Catalogue item with ID '{catalogue_item_id}' is the replacement for at least one obsolete catalogue "
                "item and cannot be deleted"
            )

        # First, attempt to delete any attachments and/or images that might be associated with this catalogue item.
        if config.object_storage.enabled:
            ObjectStorageAPIClient.delete_attachments(catalogue_item_id, access_token)
            ObjectStorageAPIClient.delete_images(catalogue_item_id, access_token)

        self._catalogue_item_repository.delete(catalogue_item_id)

    def validate(self, catalogue_item_data: dict[str, Any]) -> List[ErrorDetails]:
        """
        Performs validation of catalogue item data returning any errors.

        :param catalogue_item_data: Catalogue item data to verify.
        :return: List of errors that have occurred.
        """

        errors = []
        # This records any errors from basic schema validation including the properties
        try:
            catalogue_item_schema = CatalogueItemPostSchema(**catalogue_item_data)
        except ValidationError as exc:
            errors.append(exc.errors())

        # Check the catalogue category exists (if defined)
        catalogue_category = None
        if "catalogue_category_id" in catalogue_item_data:
            try:
                catalogue_category = self._catalogue_category_repository.get(
                    catalogue_item_data["catalogue_category_id"]
                )
            except InvalidObjectIdError:
                # Ignore invalid object ID, treat as missing
                pass
            if not catalogue_category:
                errors.append(
                    ValidationError.from_exception_data(
                        title="Missing catalogue category",
                        line_errors=[
                            InitErrorDetails(
                                type="missing",
                                loc=("catalogue_category_id",),
                                #  msg=("Missing mandatory property"),
                                input=catalogue_item_data,
                            )
                        ],
                    ).errors()
                )

        # Check the manufacturer exists (if defined)
        if "manufacturer_id" in catalogue_item_data:
            manufacturer = None
            try:
                manufacturer = self._manufacturer_repository.get(catalogue_item_data["manufacturer_id"])
            except InvalidObjectIdError:
                # Ignore invalid object ID, treat as missing
                pass
            if not manufacturer:
                errors.append(
                    ValidationError.from_exception_data(
                        title="Missing manufacturer",
                        line_errors=[
                            InitErrorDetails(
                                type="missing",
                                loc=("manufacturer_id",),
                                #  msg=("Missing mandatory property"),
                                input=catalogue_item_data,
                            )
                        ],
                    ).errors()
                )

        # Now validate any properties
        if "properties" in catalogue_item_data:
            # NOTE: Basic schema validation of properties has already occurred at this point from using
            #       CatalogueItemPostSchema above, we dont want to capture those errors again.
            #       While we cant validate those properties that dont pass the basic checks, we can
            #       at least attempt to perform additional validation on those that do.
            property_schemas = []

            for property_data in catalogue_item_data["properties"]:
                try:
                    property_schemas.append(PropertyPostSchema(**property_data))
                except ValidationError:
                    pass

            # Perform validation of the properties - can only be done assuming a catalogue category ID has been provided
            if catalogue_category:
                validate_properties(errors, catalogue_category.properties, property_schemas)
        return errors


# TODO: Move elsewhere put in here to avoid clash with existing utils
# TODO: Update comments
def validate_properties(
    errors: list[ErrorDetails],
    defined_properties: List[CatalogueCategoryPropertyOut],
    supplied_properties: List[PropertyPostSchema],
) -> List[dict]:
    """
    Process and validate supplied properties based on the defined properties. It checks for missing mandatory, filters
    the matching properties, adds the property units, and finally validates the property values.

    The `supplied_properties_dict` dictionary may get modified as part of the processing and validation.

    :param defined_properties: The list of defined property objects.
    :param supplied_properties: The list of supplied property objects.
    :return: A list of processed and validated supplied properties.
    """
    # Convert properties to dictionaries for easier lookups
    defined_properties_dict = utils._create_properties_dict(defined_properties)
    supplied_properties_dict = utils._create_properties_dict(supplied_properties)

    # Some mandatory properties may not have been supplied
    _check_missing_mandatory_properties(errors, defined_properties_dict, supplied_properties_dict)
    # # Some non-mandatory properties may not have been supplied
    # supplied_properties_dict = _merge_non_mandatory_properties(defined_properties_dict, supplied_properties_dict)
    # # Supplied properties do not have names as we can't trust they would be correct
    # _add_property_names(defined_properties_dict, supplied_properties_dict)
    # # Supplied properties do not have units as we can't trust they would be correct
    # _add_property_units(defined_properties_dict, supplied_properties_dict)
    # # The values of the supplied properties may not be of the expected types
    _validate_property_values(errors, defined_properties_dict, supplied_properties_dict)

    # return list(supplied_properties_dict.values())


def _check_missing_mandatory_properties(
    errors: list[ErrorDetails],
    defined_properties: dict[str, dict],
    supplied_properties: dict[str, dict],
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
            errors.append(
                ValidationError.from_exception_data(
                    title="Missing mandatory property",
                    line_errors=[
                        InitErrorDetails(
                            type="missing",
                            loc=("properties", "id", defined_property_id),
                            # msg=("Missing mandatory property"),
                            input=supplied_properties,
                        )
                    ],
                ).errors()
            )
    # raise MissingMandatoryProperty(f"Missing mandatory property with ID '{defined_property_id}'")


def _validate_property_values(
    errors: list[ErrorDetails],
    defined_properties: dict[str, dict],
    supplied_properties: dict[str, dict],
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
    for i, (supplied_property_id, supplied_property) in enumerate(supplied_properties.items()):
        _validate_property_value(errors, i, defined_properties[supplied_property_id], supplied_property)


def _validate_property_value(
    errors: list[ErrorDetails], index: int, defined_property: dict, supplied_property: dict
) -> None:
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
            errors.append(
                ValidationError.from_exception_data(
                    title="Missing mandatory property",
                    line_errors=[
                        InitErrorDetails(
                            type="missing",
                            loc=("properties", index, "value"),
                            # msg=("Missing mandatory value"),
                            input=supplied_property,
                        )
                    ],
                ).errors()
            )
            # raise InvalidPropertyTypeError(f"Mandatory property with ID '{supplied_property_id}' cannot be None.")
    else:
        if not CatalogueCategoryPostPropertySchema.is_valid_property_type(
            defined_property_type, supplied_property_value
        ):
            errors.append(
                ValidationError.from_exception_data(
                    title="Missing mandatory property",
                    line_errors=[
                        InitErrorDetails(
                            type=(
                                "string_type"
                                if defined_property_type == CatalogueCategoryPropertyType.STRING
                                else (
                                    "decimal_type"
                                    if defined_property_type == CatalogueCategoryPropertyType.NUMBER
                                    else (
                                        "bool_type"
                                        if defined_property_type == CatalogueCategoryPropertyType.BOOLEAN
                                        else "value_error"
                                    )
                                )
                            ),
                            loc=("properties", index, "value"),
                            # msg=("Missing mandatory value"),
                            input=supplied_property,
                        )
                    ],
                ).errors()
            )
            # raise InvalidPropertyTypeError(
            #     f"Invalid value type for property with ID '{supplied_property_id}'. Expected type: "
            #     f"{defined_property_type}."
            # )

        # Verify the given property is one of the allowed based on the type of allowed_values defined
        if defined_property_allowed_values is not None and defined_property_allowed_values["type"] == "list":
            values = defined_property_allowed_values["values"]
            if supplied_property_value not in values:
                errors.append(
                    ValidationError.from_exception_data(
                        title="Invalid property type",
                        line_errors=[
                            InitErrorDetails(
                                type="literal_error",
                                loc=("properties", index, "value"),
                                # msg=(f"Input should be one of {', '.join([str(value) for value in values])}"),
                                input=supplied_property,
                                ctx={"expected": f"{', '.join([str(value) for value in values])}."},
                            )
                        ],
                    ).errors()
                )
                # raise InvalidPropertyTypeError(
                #     f"Invalid value for property with ID '{supplied_property_id}'. Expected one of "
                #     f"{', '.join([str(value) for value in values])}."
                # )
