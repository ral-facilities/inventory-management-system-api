"""
Module for defining the API schema models for representing catalogue categories.
"""
from enum import Enum
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, validator, root_validator, Field


class CatalogueItemPropertyType(str, Enum):
    """
    Enumeration for catalogue item property types.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


class CatalogueItemProperty(BaseModel):
    """
    Model representing a catalogue item property.
    """

    name: str = Field(description="The name of the catalogue item property")
    type: CatalogueItemPropertyType
    unit: Optional[str] = Field(default=None, description="The unit of the property such as 'nm', 'mm', 'cm' etc")
    mandatory: bool = Field(description="Whether the property must be supplied when a catalogue item is created")

    @validator("unit")
    @classmethod
    def validate_unit(cls, unit_value: str, values: Dict[str, Any]) -> Optional[str]:
        """
        Validator for the `unit` field.

        It checks if the `type` of the catalogue item property is a `boolean` and if a` unit` has been specified. It
        raises a `ValueError` if this is the case.

        :param unit_value: The value of the `unit` field.
        :param values: The values of the model fields.
        :return: The value of the `unit` field.
        :raises ValueError: If `unit` is provided when `type` is set to `boolean`.
        """
        if "type" in values and values["type"] == CatalogueItemPropertyType.BOOLEAN and unit_value is not None:
            raise ValueError(f"Unit not allowed for boolean catalogue item property '{values['name']}'")
        return unit_value


class CatalogueCategoryPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue category creation request.
    """

    name: str = Field(description="The name of the catalogue category")
    is_leaf: bool = Field(
        description="Whether the category is a leaf or not. If it is then it can only have catalogue items as "
        "children but if it is not then it can only have catalogue categories as children."
    )
    parent_id: Optional[str] = Field(default=None, description="The ID of the parent catalogue category")
    catalogue_item_properties: List[CatalogueItemProperty] = Field(
        description="The properties that the catalogue items in this category could/should have"
    )

    @root_validator(pre=True)
    @classmethod
    def validate_values(cls, values):
        """
        Root validator for the model which runs before the values are assigned to the fields.

        This is needed to make the `catalogue_item_properties` field not required if the catalogue category is not a
        leaf. It assigns an empty list if the field is not present in the body.

        :param values: The values of the model fields.
        :return: The values of the model fields.
        """
        # Do not require the `catalogue_item_properties` field to be present in the body if the catalogue category is
        # not a leaf. Assign an empty list
        if "is_leaf" in values and not values["is_leaf"] and "catalogue_item_properties" not in values:
            values["catalogue_item_properties"] = []
        return values

    @validator("catalogue_item_properties")
    @classmethod
    def validate_catalogue_item_properties(
        cls, catalogue_item_properties: List[CatalogueItemProperty], values: Dict[str, Any]
    ) -> List[CatalogueItemProperty]:
        """
        Validator for the `catalogue_item_properties` field.

        It checks if the category is a non-leaf category and if catalogue item properties are present in the body. It
        raises a `ValueError` if this is the case.

        :param catalogue_item_properties: The list of catalogue item properties.
        :param values: The values of the model fields.
        :return: The list of catalogue item properties.
        :raises ValueError: If catalogue item properties are provided for a non-leaf catalogue category.
        """
        if "is_leaf" in values and not values["is_leaf"] and catalogue_item_properties:
            raise ValueError("Catalogue item properties not allowed for non-leaf catalogue category")
        return catalogue_item_properties


class CatalogueCategorySchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str = Field(description="The ID of the catalogue category")
    code: str = Field(description="The code of the catalogue category")
    path: str = Field(description="The path to the catalogue category")
    parent_path: str = Field(description="The path to the parent catalogue category of the category")
