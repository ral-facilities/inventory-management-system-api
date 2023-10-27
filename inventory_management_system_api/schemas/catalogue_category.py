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


# Special fields that are not allowed to be changed in a post request while the category has child elements
CATALOGUE_CATEGORY_WITH_CHILDREN_NON_EDITABLE_FIELDS = ["is_leaf", "catalogue_item_properties"]


class CatalogueCategoryPatchRequestSchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category update request.
    """

    name: Optional[str] = Field(description="The name of the catalogue category")
    is_leaf: Optional[bool] = Field(
        description="Whether the category is a leaf or not. If it is then it can only have catalogue items as "
        "children but if it is not then it can only have catalogue categories as children."
    )
    parent_id: Optional[str] = Field(description="The ID of the parent catalogue category")


class CatalogueCategorySchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str = Field(description="The ID of the catalogue category")
    code: str = Field(description="The code of the catalogue category")
