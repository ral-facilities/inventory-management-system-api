"""
Module for defining the database models for representing catalogue categories.
"""
from typing import Optional, List

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
    catalogue_item_properties: List[CatalogueItemProperty]

    @validator("catalogue_item_properties", pre=True, always=True)
    @classmethod
    def validate_catalogue_item_properties(
        cls, catalogue_item_properties: List[CatalogueItemProperty] | None
    ) -> List[CatalogueItemProperty] | List:
        """
        Validator for the `catalogue_item_properties` field that runs always (even if the field is missing) and before
        any Pydantic validation checks.

        If the value is `None`, it replaces it with an empty list.

        :param catalogue_item_properties: The list of catalogue item properties.
        :return: The list of catalogue item properties or an empty list.
        """
        if catalogue_item_properties is None:
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
