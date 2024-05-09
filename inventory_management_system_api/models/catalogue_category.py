"""
Module for defining the database models for representing catalogue categories.
"""

from typing import Annotated, Any, List, Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


class AllowedValuesList(BaseModel):
    """
    Model representing a list of allowed values for a catalogue item property
    """

    type: Literal["list"]
    values: List[Any]


# Use discriminated union for any additional types of allowed values (so can use Pydantic's validation)
AllowedValues = Annotated[AllowedValuesList, Field(discriminator="type")]


class CatalogueItemPropertyBase(BaseModel):
    """
    Base database model for a catalogue item property.
    """

    name: str
    type: str
    unit_id: Optional[CustomObjectIdField] = None
    unit: Optional[str] = None
    mandatory: bool
    allowed_values: Optional[AllowedValues] = None


class CatalogueItemPropertyIn(CatalogueItemPropertyBase):
    """
    Input database model for a catalogue item property.
    """

    # Because the catalogue item properties are stored in a list inside the catalogue categories and not in a separate
    # collection, it means that the IDs have to be manually generated here.
    id: CustomObjectIdField = Field(default_factory=ObjectId, serialization_alias="_id")


class CatalogueItemPropertyOut(CatalogueItemPropertyBase):
    """
    Output database model for a catalogue item property.
    """

    id: StringObjectIdField = Field(alias="_id")
    unit_id: Optional[StringObjectIdField] = None
    model_config = ConfigDict(populate_by_name=True)

    def is_equal_without_id(self, other: Any) -> bool:
        """
        Compare this instance with another instance of `CatalogueItemPropertyOut` while ignoring the ID.

        :param other: An instance of a model to compare with.
        :return: `True` if the instances are of the same type and are equal when ignoring the ID field, `False`
            otherwise.
        """
        if not isinstance(other, CatalogueItemPropertyOut):
            return False

        return (
            self.name == other.name
            and self.type == other.type
            and self.unit == other.unit
            and self.unit_id == other.unit_id
            and self.mandatory == other.mandatory
            and self.allowed_values == other.allowed_values
        )


class CatalogueCategoryBase(BaseModel):
    """
    Base database model for a catalogue category.
    """

    name: str
    code: str
    is_leaf: bool
    parent_id: Optional[CustomObjectIdField] = None
    catalogue_item_properties: List[CatalogueItemPropertyIn] = []

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


class CatalogueCategoryBaseOut(CatalogueCategoryBase):
    """
    Base database model for a catalogue category out.
    """

    catalogue_item_properties: List[CatalogueItemPropertyOut] = []


class CatalogueCategoryIn(CreatedModifiedTimeInMixin, CatalogueCategoryBase):
    """
    Input database model for a catalogue category.
    """


class CatalogueCategoryOut(CreatedModifiedTimeOutMixin, CatalogueCategoryBaseOut):
    """
    Output database model for a catalogue category.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None
    catalogue_item_properties: List[CatalogueItemPropertyOut] = []
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
