"""
Module for providing an API router which defines routes for managing catalogue items using the `CatalogueItemService`
service.
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-items", tags=["catalogue items"])
