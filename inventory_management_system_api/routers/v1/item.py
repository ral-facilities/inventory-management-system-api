"""
Module for providing an API router which defines routes for managing items using the `ItemService` service.
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger()

router = APIRouter(prefix="/v1/items", tags=["items"])
