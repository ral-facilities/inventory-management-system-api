"""
Module for defining the database models for representing a Catalogue item property template
"""

from pydantic import ConfigDict, Field

from inventory_management_system_api.models.catalogue_category import CatalogueItemProperty
from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField


class CatalogueItemPropertyTemplateOut(CatalogueItemProperty):
    """
    Model representing a catalogue item property template.
    """

    id: StringObjectIdField = Field(alias="_id")

    model_config = ConfigDict(populate_by_name=True)
