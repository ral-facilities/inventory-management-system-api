"""
Main module contains the API entrypoint.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.logger_setup import setup_logger
from inventory_management_system_api.routers.v1 import catalogue_category

app = FastAPI(title=config.api.title, description=config.api.description)

setup_logger()
logger = logging.getLogger()
logger.info("Logging now setup")

# Fixes CORS issues but should be updated before deploying to prod
ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogue_category.router)


@app.get("/")
def read_root():
    """
    Root endpoint for the API.
    """
    return {"Title": "Inventory Management System API"}
