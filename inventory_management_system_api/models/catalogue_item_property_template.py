"""
Module for defining the database models for representing a Catalogue item property template
"""

from pydantic import ConfigDict, Field

from inventory_management_system_api.models.catalogue_category import CatalogueItemProperty
from inventory_management_system_api.models.custom_object_id_data_types import StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin


class CatalogueItemPropertyTemplateIn(CreatedModifiedTimeInMixin, CatalogueItemProperty):
    """
    Input database model for a catalogue item property template.
    """

    code: str


class CatalogueItemPropertyTemplateOut(CreatedModifiedTimeOutMixin, CatalogueItemProperty):
    """
    Output database model for a catalogue item property template.
    """

    id: StringObjectIdField = Field(alias="_id")
    code: str

    model_config = ConfigDict(populate_by_name=True)
