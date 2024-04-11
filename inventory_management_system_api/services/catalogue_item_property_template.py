"""
Module for providing a service for managing catalogue item property templates using the
`CatalogueItemPropertyTemplateRepo` repository
"""

from fastapi import Depends
from inventory_management_system_api.models.catalogue_item_property_template import CatalogueItemPropertyTemplateOut
from inventory_management_system_api.repositories.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateRepo,
)


class CatalogueItemPropertyTemplateService:
    """
    Service for managing catalogue item property templates
    """

    def __init__(
        self,
        catalogue_item_property_template_repository: CatalogueItemPropertyTemplateRepo = Depends(
            CatalogueItemPropertyTemplateRepo
        ),
    ) -> None:
        """
        Initialise the `CatalogueItemPropertyTemplateService` with a `CatalogueItemPropertyTemplateRepo` repository
        :param catalogue_item_property_template_repository: `CatalogueItemPropertyTemplateRepo` repository to use
        """
        self._catalogue_item_property_template_repository = catalogue_item_property_template_repository

    def list(self) -> list[CatalogueItemPropertyTemplateOut]:
        """
        Retrieve a list of all catalogue item property templates
        :return: List of catalogue item property templates or an empty list if no catalogue item property
                 templates are retrieved
        """
        return self._catalogue_item_property_template_repository.list()
