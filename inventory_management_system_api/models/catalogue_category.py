"""
Module for defining the database models for representing catalogue categories.
"""
from typing import Annotated, Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField


class AllowedValuesList(BaseModel):
    """
    Model representing a list of allowed values for a catalogue item property
    """

    type: Literal["list"]
    values: List[Any]


# Use discriminated union for any additional types of allowed values (so can use Pydantic's validation)
AllowedValues = Annotated[AllowedValuesList, Field(discriminator="type")]


class CatalogueItemProperty(BaseModel):
    """
    Model representing a catalogue item property.
    """

    name: str
    type: str
    unit: Optional[str] = None
    mandatory: bool
    allowed_values: Optional[AllowedValues] = None


class CatalogueCategoryIn(BaseModel):
    """
    Input database model for a catalogue category.
    """

    name: str
    code: str
    is_leaf: bool
    parent_id: Optional[CustomObjectIdField] = None
    catalogue_item_properties: List[CatalogueItemProperty] = []

    @field_validator("catalogue_item_properties", mode="before")
    @classmethod
    def validate_catalogue_item_properties(cls, catalogue_item_properties: Any, info: ValidationInfo) -> Any:
        """
        Validator for the `catalogue_item_properties` field that runs after field assignment but before type validation.

        If the value is `None`, it replaces it with an empty list allowing for catalogue categories without catalogue
        item properties to be created. If the category is a non-leaf category and if catalogue item properties are
        supplied, it replaces it with an empty list because they cannot have properties.

        :param catalogue_item_properties: The list of catalogue item properties.
        :param info: Validation info from pydantic.
        :return: The list of catalogue item properties or an empty list.
        """
        if catalogue_item_properties is None or (
            "is_leaf" in info.data and info.data["is_leaf"] is False and catalogue_item_properties
        ):
            catalogue_item_properties = []

        return catalogue_item_properties


class CatalogueCategoryOut(CatalogueCategoryIn):
    """
    Output database model for a catalogue category.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
