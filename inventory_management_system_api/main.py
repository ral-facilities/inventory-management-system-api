"""
Main module contains the API entrypoint.
"""
from fastapi import FastAPI

from inventory_management_system_api.core.config import config

app = FastAPI(title=config.api.title, description=config.api.description)


@app.get("/")
def read_root():
    """
    Root endpoint for the API.
    """
    return {"Title": "Inventory Management System API"}
