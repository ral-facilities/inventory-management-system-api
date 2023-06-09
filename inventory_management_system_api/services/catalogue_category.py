"""
Module for providing a service for managing catalogue categories using the CategoryRepo repository.
"""
from fastapi import Depends

from inventory_management_system_api.models.catalogue_category import CatalogueCategoryIn, CatalogueCategoryOut
from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo
from inventory_management_system_api.schemas.catalogue_category import CatalogueCategoryPostRequestSchema


class CatalogueCategoryService:
    """
    Service for managing catalogue categories.
    """

    def __init__(self, catalogue_category_repository: CatalogueCategoryRepo = Depends()) -> None:
        """
        Initialize the CatalogueCategoryService with a catalogue category repository.

        :param catalogue_category_repository: The catalogue category repository to use.
        """
        self.catalogue_category_repository = catalogue_category_repository

    def create(self, catalogue_category: CatalogueCategoryPostRequestSchema) -> CatalogueCategoryOut:
        """
        Create a new catalogue category.

        :param catalogue_category: The catalogue category to be created.
        :return: The created catalogue category.
        """
        return self.catalogue_category_repository.create(
            CatalogueCategoryIn(**catalogue_category.dict())
        )
