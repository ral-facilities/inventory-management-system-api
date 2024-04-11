"""
Module for defining the database models for representing a Catalogue item property template
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from inventory_management_system_api.models.catalogue_category import AllowedValues
from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField

# pylint: disable=duplicate-code


class CatalogueItemPropertyTemplateOut(BaseModel):
    """
    Model representing a catalogue item property template.
    """

    id: StringObjectIdField = Field(alias="_id")
    name: str
    type: str
    unit: Optional[str] = None
    mandatory: bool
    allowed_values: Optional[AllowedValues] = None

    model_config = ConfigDict(populate_by_name=True)
