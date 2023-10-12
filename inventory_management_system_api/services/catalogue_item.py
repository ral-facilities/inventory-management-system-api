"""
Module for providing a service for managing catalogue items using the `CatalogueItemRepo` and `CatalogueCategoryRepo`
repositories.
"""
import logging
from numbers import Number
from typing import Optional, List, Dict, Union

from fastapi import Depends

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    NonLeafCategoryError,
    InvalidCatalogueItemPropertyTypeError,
    MissingMandatoryCatalogueItemProperty,
)
from inventory_management_system_api.models.catalogue_category import CatalogueItemProperty
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut, CatalogueItemIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.schemas.catalogue_category import CatalogueItemPropertyType
from inventory_management_system_api.schemas.catalogue_item import (
    CatalogueItemPostRequestSchema,
    CatalogueItemPatchRequestSchema,
    PropertyPostRequestSchema,
)

logger = logging.getLogger()


class CatalogueItemService:
    """
    Service for managing catalogue items.
    """

    def __init__(
        self,
        catalogue_item_repository: CatalogueItemRepo = Depends(CatalogueItemRepo),
        catalogue_category_repository: CatalogueCategoryRepo = Depends(CatalogueCategoryRepo),
    ) -> None:
        """
        Initialise the `CatalogueItemService` with a `CatalogueItemRepo` and `CatalogueCategoryRepo` repos.

        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        """
        self._catalogue_item_repository = catalogue_item_repository
        self._catalogue_category_repository = catalogue_category_repository

    def create(self, catalogue_item: CatalogueItemPostRequestSchema) -> CatalogueItemOut:
        """
        Create a new catalogue item.

        The method checks if the catalogue category exists in the database and raises a `MissingRecordError` if it does
        not. It also checks if the category is not a leaf category and raises a `NonLeafCategoryError` if it is. It then
        processes the catalogue item properties.

        :param catalogue_item: The catalogue item to be created.
        :return: The created catalogue item.
        :raises MissingRecordError: If the catalogue category does not exist.
        :raises NonLeafCategoryError: If the catalogue category is not a leaf category.
        """
        catalogue_category_id = catalogue_item.catalogue_category_id
        catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        if catalogue_category.is_leaf is False:
            raise NonLeafCategoryError("Cannot add catalogue item to a non-leaf catalogue category")

        defined_properties = catalogue_category.catalogue_item_properties
        supplied_properties = catalogue_item.properties if catalogue_item.properties else []
        supplied_properties = self._process_catalogue_item_properties(defined_properties, supplied_properties)

        return self._catalogue_item_repository.create(
            CatalogueItemIn(
                catalogue_category_id=catalogue_item.catalogue_category_id,
                name=catalogue_item.name,
                description=catalogue_item.description,
                properties=supplied_properties,
                manufacturer=catalogue_item.manufacturer,
            )
        )

    def _process_catalogue_item_properties(
        self, defined_properties: List[CatalogueItemProperty], supplied_properties: List[PropertyPostRequestSchema]
    ) -> List[Dict]:
        """
        Process and validate supplied catalogue item properties based on defined catalogue item properties. It checks
        for missing mandatory catalogue item properties, files the matching catalogue item properties, adds the property
        units, and finally validates the property values.

        The `supplied_properties_dict` dictionary may get modified as part of the processing and validation.

        :param defined_properties: The list of defined catalogue item property objects.
        :param supplied_properties: The list of supplied catalogue item property objects.
        :return: A list of processed and validated supplied catalogue item properties.
        """
        # Convert properties to dictionaries for easier lookups
        defined_properties_dict = self._create_catalogue_item_properties_dict(defined_properties)
        supplied_properties_dict = self._create_catalogue_item_properties_dict(supplied_properties)

        # Some mandatory catalogue item properties may not have been supplied
        self._check_missing_mandatory_catalogue_item_properties(defined_properties_dict, supplied_properties_dict)
        # Catalogue item properties that have not been defined may have been supplied
        supplied_properties_dict = self._filter_matching_catalogue_item_properties(
            defined_properties_dict, supplied_properties_dict
        )
        # Supplied catalogue item properties do not have units as we can't trust they would be correct
        self._add_catalogue_item_property_units(defined_properties_dict, supplied_properties_dict)
        # The values of the supplied catalogue item properties may not be of the expected types
        self._validate_catalogue_item_property_values(defined_properties_dict, supplied_properties_dict)

        return list(supplied_properties_dict.values())

    def _create_catalogue_item_properties_dict(
        self, catalogue_item_properties: Union[List[CatalogueItemProperty], List[PropertyPostRequestSchema]]
    ) -> Dict[str, Dict]:
        """
        Convert a list of catalogue item property objects into a dictionary where the keys are the catalogue item
        property names and the values are the catalogue item property dictionaries.

        :param catalogue_item_properties: The list of catalogue item property objects.
        :return: A dictionary where the keys are the catalogue item property names and the values are the catalogue item
            property dictionaries.
        """
        return {
            catalogue_item_property.name: catalogue_item_property.dict()
            for catalogue_item_property in catalogue_item_properties
        }

    def _add_catalogue_item_property_units(
        self,
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

    def _validate_catalogue_item_property_values(
        self,
        defined_properties: Dict[str, Dict],
        supplied_properties: Dict[str, Dict],
    ) -> None:
        """
        Validate the values of the supplied properties against the expected property types. Raise an error if the type
        of the supplied value does not match the expected type.

        :param defined_properties: The defined catalogue item properties stored as part of the catalogue category in the
            database.
        :param supplied_properties: The supplied catalogue item properties.
        :raises InvalidCatalogueItemPropertyTypeError: If the type of the supplied value does not match the expected
            type.
        """
        logger.info("Validating the values of the supplied properties against the expected property types")
        for supplied_property_name, supplied_property in supplied_properties.items():
            expected_property_type = defined_properties[supplied_property_name]["type"]
            supplied_property_value = supplied_property["value"]

            if expected_property_type == CatalogueItemPropertyType.STRING and not isinstance(
                supplied_property_value, str
            ):
                raise InvalidCatalogueItemPropertyTypeError(
                    f"Invalid value type for catalogue item property '{supplied_property_name}'. Expected type: string."
                )
            if expected_property_type == CatalogueItemPropertyType.NUMBER and not isinstance(
                supplied_property_value, Number
            ):
                raise InvalidCatalogueItemPropertyTypeError(
                    f"Invalid value type for catalogue item property '{supplied_property_name}'. Expected type: number."
                )
            if expected_property_type == CatalogueItemPropertyType.BOOLEAN and not isinstance(
                supplied_property_value, bool
            ):
                raise InvalidCatalogueItemPropertyTypeError(
                    f"Invalid value type for catalogue item property '{supplied_property_name}'. Expected type: "
                    f"boolean."
                )

    def _check_missing_mandatory_catalogue_item_properties(
        self,
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
        self,
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

    def update(self, catalogue_item_id: str, catalogue_item: CatalogueItemPatchRequestSchema) -> CatalogueItemOut:
        """
        Update a catalogue item by its ID.

        The method checks if the catalogue item exists in the database and raises a `MissingRecordError` if it does
        not. If the catalogue category ID is being updated, it checks if catalogue category with such ID exists and
        raises a MissingRecordError` if it does not. It also checks if the category is not a leaf category and raises a
        `NonLeafCategoryError` if it is. If the catalogue item properties are being updated, it also processes them.

        :param catalogue_item_id: The ID of the catalogue item to update.
        :param catalogue_item: The catalogue item containing the fields that need to be updated.
        :return: The updated catalogue item.
        """
        update_data = catalogue_item.dict(exclude_unset=True)

        stored_catalogue_item = self.get(catalogue_item_id)
        if not stored_catalogue_item:
            raise MissingRecordError(f"No catalogue item found with ID: {catalogue_item_id}")

        catalogue_category = None
        if (
            "catalogue_category_id" in update_data
            and catalogue_item.catalogue_category_id != stored_catalogue_item.catalogue_category_id
        ):
            catalogue_category = self._catalogue_category_repository.get(catalogue_item.catalogue_category_id)
            if not catalogue_category:
                raise MissingRecordError(f"No catalogue category found with ID: {catalogue_item.catalogue_category_id}")

            if catalogue_category.is_leaf is False:
                raise NonLeafCategoryError("Cannot add catalogue item to a non-leaf catalogue category")

            # If the catalogue category ID is updated but no catalogue item properties are supplied then the stored
            # catalogue item properties should be used. They need to be processed and validated against the defined
            # properties of the new catalogue category.
            if "properties" not in update_data:
                update_data["properties"] = stored_catalogue_item.properties

        if "properties" in update_data:
            if not catalogue_category:
                catalogue_category = self._catalogue_category_repository.get(
                    stored_catalogue_item.catalogue_category_id
                )

            defined_properties = catalogue_category.catalogue_item_properties
            supplied_properties = catalogue_item.properties if catalogue_item.properties else []
            update_data["properties"] = self._process_catalogue_item_properties(defined_properties, supplied_properties)

        stored_catalogue_item = stored_catalogue_item.copy(update=update_data)
        return self._catalogue_item_repository.update(
            catalogue_item_id, CatalogueItemIn(**stored_catalogue_item.dict())
        )
