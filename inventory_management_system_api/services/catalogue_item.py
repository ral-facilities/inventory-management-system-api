"""
Module for providing a service for managing catalogue items using the `CatalogueItemRepo` and `CatalogueItemRepo`
repositories.
"""
import logging
from numbers import Number
from typing import Dict

from fastapi import Depends

from inventory_management_system_api.core.exceptions import (
    MissingRecordError,
    NonLeafCategoryError,
    InvalidCatalogueItemPropertyTypeError,
    MissingMandatoryCatalogueItemProperty,
)
from inventory_management_system_api.models.catalogue_item import CatalogueItemOut, CatalogueItemIn
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.repositories.catalogue_item import CatalogueItemRepo
from inventory_management_system_api.schemas.catalogue_category import CatalogueItemPropertyType
from inventory_management_system_api.schemas.catalogue_item import CatalogueItemPostRequestSchema

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
        Initialise the `CatalogueItemService` with a `CatalogueItemRepo` repo.

        :param catalogue_item_repository: The `CatalogueItemRepo` repository to use.
        :param catalogue_category_repository: The `CatalogueCategoryRepo` repository to use.
        """
        self._catalogue_item_repository = catalogue_item_repository
        self._catalogue_category_repository = catalogue_category_repository

    def create(self, catalogue_item: CatalogueItemPostRequestSchema) -> CatalogueItemOut:
        """
        Create a new catalogue item.

        The method checks if the catalogue category exists in the database and raises a `MissingRecordError` if it does
        not. It also checks if the category is not a leaf category and raises a `NonLeafCategoryError` if it is. It
        then proceeds to check for missing mandatory catalogue item properties, adds the propety units, and finally
        validates the property values.

        :param catalogue_item: The catalogue item to be created.
        :return: The created catalogue item.
        :raises MissingRecordError: If the catalogue category does not exist.
        :raises NonLeafCategoryError: If the catalogue category is not a leaf category.
        """
        catalogue_category_id = catalogue_item.catalogue_category_id
        catalogue_category = self._catalogue_category_repository.get(catalogue_category_id)
        if not catalogue_category:
            raise MissingRecordError(f"No catalogue category found with ID: {catalogue_category_id}")

        if not catalogue_category.is_leaf:
            raise NonLeafCategoryError("Cannot add catalogue item to a non-leaf catalogue category")

        defined_properties = {
            defined_property.name: defined_property.dict()
            for defined_property in catalogue_category.catalogue_item_properties
        }
        supplied_properties = {
            supplied_property.name: supplied_property.dict() for supplied_property in catalogue_item.properties
        }

        self._check_missing_mandatory_catalogue_item_properties(defined_properties, supplied_properties)
        supplied_properties = self._filter_matching_catalogue_item_properties(defined_properties, supplied_properties)
        self._add_catalogue_item_property_units(defined_properties, supplied_properties)
        self._validate_catalogue_item_property_values(defined_properties, supplied_properties)

        return self._catalogue_item_repository.create(
            CatalogueItemIn(
                catalogue_category_id=catalogue_item.catalogue_category_id,
                name=catalogue_item.name,
                description=catalogue_item.description,
                properties=list(supplied_properties.values()),
            )
        )

    def _add_catalogue_item_property_units(
        self,
        defined_properties: Dict[str, Dict],
        supplied_properties: Dict[str, Dict],
    ) -> None:
        for supplied_property_name, supplied_property in supplied_properties.items():
            supplied_property["unit"] = defined_properties[supplied_property_name]["unit"]

    def _validate_catalogue_item_property_values(
        self,
        defined_properties: Dict[str, Dict],
        supplied_properties: Dict[str, Dict],
    ) -> None:
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
        matching_properties = {}
        for supplied_property_name, supplied_property in supplied_properties.items():
            if supplied_property_name in defined_properties:
                matching_properties[supplied_property_name] = supplied_property

        return matching_properties