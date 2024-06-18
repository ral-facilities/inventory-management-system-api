"""
Module for defining the API schema models for representing catalogue categories.
"""

from enum import Enum
from numbers import Number
from typing import Annotated, Any, List, Literal, Optional

from pydantic import BaseModel, Field, conlist, field_validator
from pydantic_core.core_schema import ValidationInfo

from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class CatalogueCategoryPropertyType(str, Enum):
    """
    Enumeration for catalogue category property types
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


class AllowedValuesListSchema(BaseModel):
    """
    Schema model representing a list of allowed values for a property defined within a catalogue category
    """

    type: Literal["list"]
    values: conlist(Any, min_length=1)


# Use discriminated union for any additional types of allowed values (so can use Pydantic's validation)
AllowedValuesSchema = Annotated[AllowedValuesListSchema, Field(discriminator="type")]


class CatalogueCategoryPostPropertySchema(BaseModel):
    """
    Schema model for a property within a catalogue category creation request.
    """

    name: str = Field(description="The name of the property")
    type: CatalogueCategoryPropertyType = Field(description="The type of the property")
    unit_id: Optional[str] = Field(default=None, description="The ID of the unit of the property")
    mandatory: bool = Field(description="Whether the property must be supplied when a catalogue item is created")
    allowed_values: Optional[AllowedValuesSchema] = Field(
        default=None,
        description="Definition of the allowed values this property can take. 'null' indicates any value matching the "
        "type is allowed.",
    )

    @classmethod
    def is_valid_property_type(cls, expected_property_type: CatalogueCategoryPropertyType, property_value: Any) -> bool:
        """
        Validates a given value has a type matching a CatalogueCategoryPropertyType and returns false if they don't

        :param expected_property_type: Property type
        :param property_value: Value of the property being checked
        :returns: Whether the value is valid or not
        """

        # pylint: disable=unidiomatic-typecheck
        if expected_property_type == CatalogueCategoryPropertyType.STRING:
            return isinstance(property_value, str)
        if expected_property_type == CatalogueCategoryPropertyType.NUMBER:
            # Python cares if there is a decimal or not, so can't just use float for this check, even though
            # Pydantic & the FastAPI docs shows float as 'number'
            # Also boolean is a subtype of integer so have to use type here
            return isinstance(property_value, Number) and type(property_value) is not bool
        if expected_property_type == CatalogueCategoryPropertyType.BOOLEAN:
            return type(property_value) is bool
        # pylint: enable=unidiomatic-typecheck
        return False

    @field_validator("unit_id")
    @classmethod
    def validate_unit_id(cls, unit_id: Optional[str], info: ValidationInfo) -> Optional[str]:
        """
        Validator for the `unit_id` field.

        It checks if the `type` of the property is a `boolean` and if a` unit_id` has been specified. It
        raises a `ValueError` if this is the case.

        :param unit_id: The value of the `unit_id` field.
        :param info: Validation info from pydantic.
        :raises ValueError: If `unit_id` is provided when `type` is set to `boolean`.
        :return: The value of the `unit_id` field.
        """
        if "type" in info.data and info.data["type"] == CatalogueCategoryPropertyType.BOOLEAN and unit_id is not None:
            raise ValueError(f"Unit not allowed for boolean property '{info.data['name']}'")
        return unit_id

    @classmethod
    def check_valid_allowed_values(
        cls, allowed_values: Optional[AllowedValuesSchema], property_data: dict[str, Any]
    ) -> None:
        """
        Checks allowed_values against its parent property raising an error if its invalid

        :param allowed_values: The value of the `allowed_values` field.
        :param property_data: Property data to validate the allowed values against.
        :raises ValueError:
            - If the allowed_values has been given a value and the property type is a `boolean`
            - If the allowed_values is of type 'list' and 'values' contains any with a different type to the property
              type
            - If the allowed_values is of type 'list' and 'values' contains any duplicates
        """
        if allowed_values is not None and "type" in property_data:
            # Ensure the type is not boolean
            if property_data["type"] == CatalogueCategoryPropertyType.BOOLEAN:
                raise ValueError("allowed_values not allowed for a boolean property " f"'{property_data['name']}'")
            # Check the type of allowed_values being used and validate them appropriately
            if isinstance(allowed_values, AllowedValuesListSchema):
                # List type should have all values the same type and no duplicate values
                seen_values = set()

                for allowed_value in allowed_values.values:
                    # Ensure the value is the correct type
                    if not CatalogueCategoryPostPropertySchema.is_valid_property_type(
                        expected_property_type=property_data["type"], property_value=allowed_value
                    ):
                        raise ValueError(
                            "allowed_values of type 'list' must only contain values of the same type as the property "
                            "itself"
                        )

                    # Ensure the value isn't duplicated
                    seen_value = (
                        allowed_value
                        if property_data["type"] != CatalogueCategoryPropertyType.STRING
                        else allowed_value.lower()
                    )
                    if seen_value in seen_values:
                        raise ValueError(f"allowed_values of type 'list' contains a duplicate value: {allowed_value}")
                    seen_values.add(seen_value)

    @field_validator("allowed_values")
    @classmethod
    def validate_allowed_values(
        cls, allowed_values: Optional[AllowedValuesSchema], info: ValidationInfo
    ) -> Optional[AllowedValuesSchema]:
        """
        Validator for the `allowed_values` field.

        Ensures the allowed_values are valid given the rest of the property schema.

        :param allowed_values: The value of the `allowed_values` field.
        :param info: Validation info from pydantic.
        :return: The value of the `allowed_values` field.
        """

        CatalogueCategoryPostPropertySchema.check_valid_allowed_values(allowed_values, info.data)

        return allowed_values


class CatalogueCategoryPropertySchema(CatalogueCategoryPostPropertySchema):
    """
    Schema model representing a property defined within a catalogue category
    """

    id: str = Field(description="The ID of the property")
    unit: Optional[str] = Field(default=None, description="The unit of the property such as 'nm', 'mm', 'cm' etc")


class CatalogueCategoryPostSchema(BaseModel):
    """
    Schema model for a catalogue category creation request.
    """

    name: str = Field(description="The name of the catalogue category")
    is_leaf: bool = Field(
        description="Whether the category is a leaf or not. If it is then it can only have catalogue items as child "
        "elements but if it is not then it can only have catalogue categories as child elements."
    )
    parent_id: Optional[str] = Field(default=None, description="The ID of the parent catalogue category")
    properties: Optional[List[CatalogueCategoryPostPropertySchema]] = Field(
        default=None, description="The properties that the catalogue items in this category could/should have"
    )


# Special fields that are not allowed to be changed in a post request while the category has child elements
CATALOGUE_CATEGORY_WITH_CHILD_NON_EDITABLE_FIELDS = ["is_leaf", "properties"]


class CatalogueCategoryPatchSchema(CatalogueCategoryPostSchema):
    """
    Schema model for a catalogue category update request.
    """

    name: Optional[str] = Field(default=None, description="The name of the catalogue category")
    is_leaf: Optional[bool] = Field(
        default=None,
        description="Whether the category is a leaf or not. If it is then it can only have catalogue items as child "
        "elements but if it is not then it can only have catalogue categories as child elements.",
    )


class CatalogueCategorySchema(CreatedModifiedSchemaMixin, CatalogueCategoryPostSchema):
    """
    Schema model for a catalogue category response.
    """

    id: str = Field(description="The ID of the catalogue category")
    code: str = Field(description="The code of the catalogue category")
    properties: Optional[List[CatalogueCategoryPropertySchema]] = Field(
        default=None, description="The properties that the catalogue items in this category could/should have"
    )


class CatalogueCategoryPropertyPostSchema(CatalogueCategoryPostPropertySchema):
    """
    Schema model for a property creation request on a catalogue category
    """

    default_value: Any = Field(
        default=None,
        description="Value to populate all child catalogue items and items with. Required if the added field is "
        "mandatory.",
    )

    @field_validator("default_value")
    @classmethod
    def validate_default_value(cls, default_value: Any, info: ValidationInfo) -> Any:
        """
        Validator for the `default_value` field.

        It checks if the `type` of the default value is a valid type and if `allowed_values` is defined, ensures
        that the given value is within the list.

        :param default_value: The value of the `default_value` field.
        :param info: Validation info from pydantic.
        :return: The value of the `allowed_values` field.
        """
        if default_value is not None:
            if not CatalogueCategoryPostPropertySchema.is_valid_property_type(
                expected_property_type=info.data["type"], property_value=default_value
            ):
                raise ValueError("default_value must be the same type as the property itself")
            if "allowed_values" in info.data and info.data["allowed_values"]:
                allowed_values = info.data["allowed_values"]

                # Check the type of allowed_values being used and validate the default value appropriately
                if (
                    isinstance(allowed_values, AllowedValuesListSchema)
                    and default_value not in info.data["allowed_values"].values
                ):
                    raise ValueError("default_value is not one of the allowed_values")

        return default_value


class CatalogueCategoryPropertyPatchSchema(BaseModel):
    """
    Schema model for a property patch request on a catalogue category
    """

    name: Optional[str] = Field(default=None, description="The name of the property")
    allowed_values: Optional[AllowedValuesSchema] = Field(
        default=None,
        description="Definition of the allowed values this property can take. 'null' indicates any value matching the "
        "type is allowed.",
    )
