"""
Module for the overall configuration for the application.
"""
from pydantic import BaseSettings, BaseModel


class APIConfig(BaseModel):
    """
    Configuration model for the API.
    """
    title: str = "Inventory Management System API"
    description: str = "This is the API for the Inventory Management System"


class DatabaseConfig(BaseModel):
    """
    Configuration model for the database.
    """
    protocol: str
    username: str
    password: str
    hostname: str
    port: int
    name: str


class Config(BaseSettings):
    """
    Overall configuration model for the application.

    It includes attributes for the API and database configurations. The class inherits from `BaseSettings` and
    automatically reads environment variables. If values are not passed in form of system environment variables at
    runtime, it will attempt to read them from the .env file.
    """
    api: APIConfig
    database: DatabaseConfig


config = Config()
