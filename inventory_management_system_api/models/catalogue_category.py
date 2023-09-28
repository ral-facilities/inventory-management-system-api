"""
Module for defining the database models for representing catalogue categories.
"""
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, validator

from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField


class CatalogueItemProperty(BaseModel):
    """
    Model representing a catalogue item property.
    """

    name: str
    type: str
    unit: Optional[str] = None
    mandatory: bool


class CatalogueCategoryIn(BaseModel):
    """
    Input database model for a catalogue category.
    """

    name: str
    code: str
    is_leaf: bool
    path: str
    parent_path: str
    parent_id: Optional[CustomObjectIdField] = None
    catalogue_item_properties: List[CatalogueItemProperty] = []

    @validator("catalogue_item_properties", pre=True, always=True)
    @classmethod
    def validate_catalogue_item_properties(
        cls, catalogue_item_properties: List[CatalogueItemProperty] | None, values: Dict[str, Any]
    ) -> List[CatalogueItemProperty] | List:
        """
        Validator for the `catalogue_item_properties` field that runs after field assignment but before type validation.

        If the value is `None`, it replaces it with an empty list allowing for catalogue categories without catalogue
        item properties to be created. If the category is a non-leaf category and if catalogue item properties are
        supplied, it replaces it with an empty list because they cannot have properties.

        :param catalogue_item_properties: The list of catalogue item properties.
        :param values: The values of the model fields.
        :return: The list of catalogue item properties or an empty list.
        """
        if catalogue_item_properties is None or (
            "is_leaf" in values and values["is_leaf"] is False and catalogue_item_properties
        ):
            catalogue_item_properties = []

        return catalogue_item_properties


class CatalogueCategoryOut(CatalogueCategoryIn):
    """
    Output database model for a catalogue category.
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    class Config:
        # pylint: disable=C0115
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
