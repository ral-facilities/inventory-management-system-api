"""
Module for providing a service for managing catalogue categories using the CategoryRepo repository.
"""
from fastapi import Depends

from inventory_management_system_api.repositories.catalogue_category import CatalogueCategoryRepo


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
