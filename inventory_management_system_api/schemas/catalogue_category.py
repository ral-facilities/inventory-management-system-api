"""
Module for defining the API schema models for representing catalogue categories.
"""
from enum import Enum
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, validator


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

    name: str
    type: CatalogueItemPropertyType
    unit: Optional[str] = None
    mandatory: bool

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

    name: str
    is_leaf: bool
    parent_id: Optional[str] = None
    catalogue_item_properties: List[CatalogueItemProperty]


class CatalogueCategorySchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str
    code: str
    path: str
    parent_path: str
