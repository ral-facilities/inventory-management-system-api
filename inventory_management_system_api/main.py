"""
Main module contains the API entrypoint.
"""
import logging

from fastapi import FastAPI

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.logger_setup import setup_logger

app = FastAPI(title=config.api.title, description=config.api.description)

setup_logger()
logger = logging.getLogger()
logger.info("Logging now setup")


@app.get("/")
def read_root():
    """
    Root endpoint for the API.
    """
    return {"Title": "Inventory Management System API"}
