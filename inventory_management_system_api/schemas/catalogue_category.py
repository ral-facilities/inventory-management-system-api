"""
Module for defining the API schema models for representing catalogue categories.
"""
from enum import Enum
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, validator, Field


class CatalogueItemPropertyType(str, Enum):
    """
    Enumeration for catalogue item property types.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


class CatalogueItemPropertySchema(BaseModel):
    """
    Schema model representing a catalogue item property.
    """

    name: str = Field(description="The name of the property")
    type: CatalogueItemPropertyType = Field(description="The type of the property")
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
    catalogue_item_properties: Optional[List[CatalogueItemPropertySchema]] = Field(
        description="The properties that the catalogue items in this category could/should have"
    )

    @validator("catalogue_item_properties")
    @classmethod
    def validate_catalogue_item_properties(
        cls, catalogue_item_properties: List[CatalogueItemPropertySchema], values: Dict[str, Any]
    ) -> List[CatalogueItemPropertySchema]:
        """
        Validator for the `catalogue_item_properties` field.

        It checks if the category is a non-leaf category and if catalogue item properties are present in the body. It
        raises a `ValueError` if this is the case.

        :param catalogue_item_properties: The list of catalogue item properties.
        :param values: The values of the model fields.
        :return: The list of catalogue item properties.
        :raises ValueError: If catalogue item properties are provided for a non-leaf catalogue category.
        """
        if "is_leaf" in values and values["is_leaf"] is False and catalogue_item_properties:
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
