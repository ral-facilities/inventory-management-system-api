"""
Module for the overall configuration for the application.
"""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import SettingsConfigDict, BaseSettings


class APIConfig(BaseModel):
    """
    Configuration model for the API.
    """

    title: str = "Inventory Management System API"
    description: str = "This is the API for the Inventory Management System"
    root_path: str = ""  # (If using a proxy) The path prefix handled by a proxy that is not seen by the app.


class AuthenticationConfig(BaseModel):
    """
    Configuration model for the JWT access token authentication/authorization.
    """

    enabled: bool = False
    public_key_path: Optional[str] = Field(default=None, validate_default=True)
    jwt_algorithm: Optional[str] = Field(default=None, validate_default=True)

    @field_validator("public_key_path", "jwt_algorithm")
    @classmethod
    def validate_unit(cls, field_value: str, info: ValidationInfo) -> Optional[str]:
        """
        Validator for the `public_key_path` and `jwt_algorithm` fields to make them mandatory if the value of the
        `enabled` is `True`

        It checks if the `enabled` field has been set to `True` and raises a `TypeError` if this is the case.

        :param field_value: The value of the field.
        :param info: Validation info from pydantic.
        :return: The value of the field.
        :raises ValueError: If `unit` is provided when `type` is set to `boolean`.
        """
        if ("enabled" in info.data and info.data["enabled"] is True) and field_value is None:
            raise ValueError("Field required")
        return field_value


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
    authentication: AuthenticationConfig
    database: DatabaseConfig
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env", env_file_encoding="utf-8", env_nested_delimiter="__"
    )


config = Config()
