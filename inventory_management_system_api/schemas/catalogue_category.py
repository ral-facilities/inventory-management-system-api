"""
Module for defining the API schema models for representing catalogue categories.
"""

from enum import Enum
from numbers import Number
from typing import Annotated, Any, List, Literal, Optional

from pydantic import BaseModel, Field, conlist, field_validator
from pydantic_core.core_schema import ValidationInfo

from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class CatalogueItemPropertyType(str, Enum):
    """
    Enumeration for catalogue item property types.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


class AllowedValuesListSchema(BaseModel):
    """
    Schema model representing a list of allowed values for a catalogue item property
    """

    type: Literal["list"]
    values: conlist(Any, min_length=1)


# Use discriminated union for any additional types of allowed values (so can use Pydantic's validation)
AllowedValuesSchema = Annotated[AllowedValuesListSchema, Field(discriminator="type")]


class CatalogueItemPropertySchema(BaseModel):
    """
    Schema model representing a catalogue item property.
    """

    name: str = Field(description="The name of the property")
    type: CatalogueItemPropertyType = Field(description="The type of the property")
    unit: Optional[str] = Field(default=None, description="The unit of the property such as 'nm', 'mm', 'cm' etc")
    mandatory: bool = Field(description="Whether the property must be supplied when a catalogue item is created")
    allowed_values: Optional[AllowedValuesSchema] = Field(
        default=None,
        description="Definition of the allowed values this property can take. 'null' indicates any value matching the "
        "type is allowed.",
    )

    @classmethod
    def is_valid_property_type(cls, expected_property_type: CatalogueItemPropertyType, property_value: Any) -> bool:
        """
        Validates a given value has a type matching a CatalogueItemPropertyType and returns false if they don't

        :param expected_property_type: Catalogue item property type
        :param property_value: Value of the property being checked
        :returns: Whether the value is valid or not
        """

        if expected_property_type == CatalogueItemPropertyType.STRING:
            return isinstance(property_value, str)
        if expected_property_type == CatalogueItemPropertyType.NUMBER:
            return isinstance(property_value, Number)
        if expected_property_type == CatalogueItemPropertyType.BOOLEAN:
            return isinstance(property_value, bool)
        return False

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, unit_value: Optional[str], info: ValidationInfo) -> Optional[str]:
        """
        Validator for the `unit` field.

        It checks if the `type` of the catalogue item property is a `boolean` and if a` unit` has been specified. It
        raises a `ValueError` if this is the case.

        :param unit_value: The value of the `unit` field.
        :param info: Validation info from pydantic.
        :raises ValueError: If `unit` is provided when `type` is set to `boolean`.
        :return: The value of the `unit` field.
        """
        if "type" in info.data and info.data["type"] == CatalogueItemPropertyType.BOOLEAN and unit_value is not None:
            raise ValueError(f"Unit not allowed for boolean catalogue item property '{info.data['name']}'")
        return unit_value

    @field_validator("allowed_values")
    @classmethod
    def validate_allowed_values(
        cls, allowed_values: Optional[AllowedValuesSchema], info: ValidationInfo
    ) -> Optional[AllowedValuesSchema]:
        """
        Validator for the `allowed_values` field.

        It checks if the `type` of the catalogue item property is a `boolean` and if `allowed_values` has been specified
        and raises a `ValueError` if this is the case. In the case the `allowed_values` is as `list` type, then also
        verifies all of the values are of the same `type` and raises a ValueError if not.

        :param allowed_values: The value of the `allowed_values` field.
        :param info: Validation info from pydantic.
        :return: The value of the `allowed_values` field.
        """
        if allowed_values is not None and "type" in info.data:
            # Ensure the type is not boolean
            if info.data["type"] == CatalogueItemPropertyType.BOOLEAN:
                raise ValueError(
                    f"allowed_values not allowed for a boolean catalogue item property '{info.data['name']}'"
                )
            # Check the type of allowed_values being used and validate them appropriately
            if isinstance(allowed_values, AllowedValuesListSchema):
                # List type should have all values the same type
                for allowed_value in allowed_values.values:
                    if not CatalogueItemPropertySchema.is_valid_property_type(
                        expected_property_type=info.data["type"], property_value=allowed_value
                    ):
                        raise ValueError(
                            "allowed_values must only contain values of the same type as the property itself"
                        )

        return allowed_values


class CatalogueCategoryPostRequestSchema(BaseModel):
    """
    Schema model for a catalogue category creation request.
    """

    name: str = Field(description="The name of the catalogue category")
    is_leaf: bool = Field(
        description="Whether the category is a leaf or not. If it is then it can only have catalogue items as child "
        "elements but if it is not then it can only have catalogue categories as child elements."
    )
    parent_id: Optional[str] = Field(default=None, description="The ID of the parent catalogue category")
    catalogue_item_properties: Optional[List[CatalogueItemPropertySchema]] = Field(
        default=None, description="The properties that the catalogue items in this category could/should have"
    )


# Special fields that are not allowed to be changed in a post request while the category has child elements
CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS = ["is_leaf", "catalogue_item_properties"]


class CatalogueCategoryPatchRequestSchema(CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category update request.
    """

    name: Optional[str] = Field(default=None, description="The name of the catalogue category")
    is_leaf: Optional[bool] = Field(
        default=None,
        description="Whether the category is a leaf or not. If it is then it can only have catalogue items as child "
        "elements but if it is not then it can only have catalogue categories as child elements.",
    )
    parent_id: Optional[str] = Field(default=None, description="The ID of the parent catalogue category")


class CatalogueCategorySchema(CreatedModifiedSchemaMixin, CatalogueCategoryPostRequestSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str = Field(description="The ID of the catalogue category")
    code: str = Field(description="The code of the catalogue category")
