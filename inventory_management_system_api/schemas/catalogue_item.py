"""
Module for defining the API schema models for representing catalogue items.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from inventory_management_system_api.schemas.mixins import CreatedModifiedSchemaMixin


class PropertyPostSchema(BaseModel):
    """
    Schema model for a property creation request.
    """

    id: str = Field(description="The ID of the property")
    value: Any = Field(default=None, description="The value of the property")


class PropertySchema(PropertyPostSchema):
    """
    Schema model for a property response.
    """

    name: str = Field(description="The name of the property")
    unit_id: Optional[str] = Field(default=None, description="The ID of the unit")
    unit: Optional[str] = Field(default=None, description="The unit of the property such as 'nm', 'mm', 'cm' etc")


class CatalogueItemPostSchema(BaseModel):
    """
    Schema model for a catalogue item creation request.
    """

    catalogue_category_id: str = Field(
        description="The ID of the catalogue category that the catalogue item belongs to"
    )
    manufacturer_id: str = Field(description="The ID of the manufacturer")
    name: str = Field(description="The name of the catalogue item")
    description: Optional[str] = Field(default=None, description="The description of the catalogue item")
    cost_gbp: float = Field(description="The cost of the catalogue item")
    cost_to_rework_gbp: Optional[float] = Field(default=None, description="The cost to rework the catalogue item")
    days_to_replace: float = Field(description="The number of days to replace the catalogue item")
    days_to_rework: Optional[float] = Field(default=None, description="The number of days to rework the catalogue item")
    drawing_number: Optional[str] = Field(default=None, description="The drawing number of the catalogue item")
    drawing_link: Optional[HttpUrl] = Field(default=None, description="The link to the drawing of the catalogue item")
    item_model_number: Optional[str] = Field(default=None, description="The model number of the catalogue item")
    is_obsolete: bool = Field(description="Whether the catalogue item is obsolete or not")
    obsolete_reason: Optional[str] = Field(
        default=None, description="The reason why the catalogue item became obsolete"
    )
    obsolete_replacement_catalogue_item_id: Optional[str] = Field(
        default=None, description="The ID of the catalogue item that replaces this catalogue item if obsolete"
    )
    notes: Optional[str] = Field(default=None, description="Any notes about the catalogue item")
    properties: Optional[List[PropertyPostSchema]] = Field(
        default=None,
        description="The properties specific to this catalogue item as defined in the corresponding "
        "catalogue category",
    )


# Special fields that are not allowed to be changed in a post request while the catalogue item has child elements
CATALOGUE_ITEM_WITH_CHILD_NON_EDITABLE_FIELDS = ["manufacturer_id", "properties"]


class CatalogueItemPatchSchema(CatalogueItemPostSchema):
    """
    Schema model for a catalogue item update request.
    """

    catalogue_category_id: Optional[str] = Field(
        default=None, description="The ID of the catalogue category that the catalogue item belongs to"
    )
    manufacturer_id: Optional[str] = Field(default=None, description="The ID of the manufacturer")
    name: Optional[str] = Field(default=None, description="The name of the catalogue item")
    cost_gbp: Optional[float] = Field(default=None, description="The cost of the catalogue item")
    days_to_replace: Optional[float] = Field(
        default=None, description="The number of days to replace the catalogue item"
    )
    is_obsolete: Optional[bool] = Field(default=None, description="Whether the catalogue item is obsolete or not")


class CatalogueItemSchema(CreatedModifiedSchemaMixin, CatalogueItemPostSchema):
    """
    Schema model for a catalogue item response.
    """

    id: str = Field(description="The ID of the catalogue item")
    properties: List[PropertySchema] = Field(
        description="The properties specific to this catalogue item as defined "
        "in the corresponding catalogue category"
    )

    # Computed
    number_of_spares: Optional[int] = Field(
        default=None, description="The number of spares currently available within this catalogue item if known"
    )
