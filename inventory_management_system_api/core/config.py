"""
Module for the overall configuration for the application.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIConfig(BaseModel):
    """
    Configuration model for the API.
    """

    title: str = "Inventory Management System API"
    description: str = "This is the API for the Inventory Management System"
    root_path: str = ""  # (If using a proxy) The path prefix handled by a proxy that is not seen by the app.
    allowed_cors_headers: List[str]
    allowed_cors_origins: List[str]
    allowed_cors_methods: List[str]


class AuthenticationConfig(BaseModel):
    """
    Configuration model for the JWT access token authentication/authorization.
    """

    enabled: bool
    public_key_path: Optional[str] = Field(default=None, validate_default=True)
    jwt_algorithm: Optional[str] = Field(default=None, validate_default=True)

    @field_validator("public_key_path", "jwt_algorithm")
    @classmethod
    def validate_optional_fields(cls, field_value: str, info: ValidationInfo) -> Optional[str]:
        """
        Validator for the `public_key_path` and `jwt_algorithm` fields to make them mandatory if the value of the
        `enabled` field is `True`. It raises a `ValueError` if no value is provided for the field when the `enabled`
        field has been set to `True`.

        :param field_value: The value of the field.
        :param info: Validation info from pydantic.
        :raises ValueError: If no value is provided for the field when the `enabled` field is set to `True`.
        :return: The value of the field.
        """
        if ("enabled" in info.data and info.data["enabled"] is True) and field_value is None:
            raise ValueError("Field required")
        return field_value


class DatabaseConfig(BaseModel):
    """
    Configuration model for the database.
    """

    protocol: SecretStr
    username: SecretStr
    password: SecretStr
    host_and_options: SecretStr
    name: SecretStr

    model_config = ConfigDict(hide_input_in_errors=True)


class ObjectStorageConfig(BaseModel):
    """
    Configuration model for the Object Storage.
    """

    enabled: bool
    api_request_timeout_seconds: Optional[int] = Field(default=None, validate_default=True)
    api_url: Optional[str] = Field(default=None, validate_default=True)

    @field_validator("api_request_timeout_seconds", "api_url")
    @classmethod
    def validate_optional_fields(cls, field_value: str, info: ValidationInfo) -> Optional[str]:
        """
        Validator for the `api_request_timeout_seconds` and `api_url` fields to make them mandatory if the value of the
        `enabled` field is `True`. It raises a `ValueError` if no value is provided for the field when the `enabled`
        field has been set to `True`.

        :param field_value: The value of the field.
        :param info: Validation info from pydantic.
        :raises ValueError: If no value is provided for the field when the `enabled` field is set to `True`.
        :return: The value of the field.
        """
        if ("enabled" in info.data and info.data["enabled"] is True) and field_value is None:
            raise ValueError("Field required")
        return field_value


class Config(BaseSettings):
    """
    Overall configuration model for the application.

    It includes attributes for the API, authentication and database configurations. The class inherits from
    `BaseSettings` and automatically reads environment variables. If values are not passed in form of system environment
    variables at runtime, it will attempt to read them from the .env file.
    """

    api: APIConfig
    authentication: AuthenticationConfig
    database: DatabaseConfig
    object_storage: ObjectStorageConfig

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        hide_input_in_errors=True,
    )


config = Config()
