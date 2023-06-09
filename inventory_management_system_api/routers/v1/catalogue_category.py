"""
Module for providing an API router which defines routes for managing catalogue categories.
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger()

router = APIRouter(prefix="/v1/catalogue-categories")
