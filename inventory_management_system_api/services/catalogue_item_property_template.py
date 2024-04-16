"""
Module for providing a service for managing catalogue item property templates using the
`CatalogueItemPropertyTemplateRepo` repository
"""

from typing import Optional
from fastapi import Depends
from inventory_management_system_api.models.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateOut,
    CatalogueItemPropertyTemplateIn,
)
from inventory_management_system_api.repositories.catalogue_item_property_template import (
    CatalogueItemPropertyTemplateRepo,
)
from inventory_management_system_api.schemas.catalogue_item_property_template import (
    CatalogueItemPropertyTemplatePostRequestSchema,
)
from inventory_management_system_api.services import utils


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

    def create(
        self, catalogue_item_property_template: CatalogueItemPropertyTemplatePostRequestSchema
    ) -> CatalogueItemPropertyTemplateOut:
        """
        Create a new catalogue item property template.
        :param  catalogue_item_property_template: The catalogue item property template to be created.
        :return: The created catalogue item property template.
        """
        code = utils.generate_code(catalogue_item_property_template.name, "catalogue item property template")
        return self._catalogue_item_property_template_repository.create(
            CatalogueItemPropertyTemplateIn(**catalogue_item_property_template.model_dump(), code=code)
        )

    def get(self, catalogue_item_property_template_repository_id: str) -> Optional[CatalogueItemPropertyTemplateOut]:
        """
        Get catalogue item property template by its ID.

        :param: catalogue_item_property_template_repository_id: The ID of the requested catalogue item property template
        :return: The retrieved catalogue item property template, or None if not found
        """
        return self._catalogue_item_property_template_repository.get(catalogue_item_property_template_repository_id)

    def list(self) -> list[CatalogueItemPropertyTemplateOut]:
        """
        Retrieve a list of all catalogue item property templates
        :return: List of catalogue item property templates or an empty list if no catalogue item property
                 templates are retrieved
        """
        return self._catalogue_item_property_template_repository.list()
