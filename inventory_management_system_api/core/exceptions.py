"""
Module for custom exception classes.
"""

from typing import Optional

from fastapi import status


class BaseAPIException(Exception):
    """Base exception for API errors."""

    # Status code to return if this exception is raised
    status_code: int

    # Generic detail of the exception (That may be returned in a response)
    response_detail: str

    detail: str

    def __init__(self, detail: str, response_detail: Optional[str] = None, status_code: Optional[int] = None):
        """
        Initialise the exception.

        :param detail: Specific detail of the exception (just like Exception would take - this will only be logged
                       and not returned in a response).
        :param response_detail: Generic detail of the exception that will be returned in a response.
        :param status_code: Status code that will be returned in a response.
        """
        super().__init__(detail)

        self.detail = detail

        if response_detail is not None:
            self.response_detail = response_detail
        # If there is no response detail defined just use the detail
        elif not hasattr(self, "response_detail"):
            self.response_detail = detail
        if status_code is not None:
            self.status_code = status_code


class DatabaseError(BaseAPIException):
    """
    Database related error.
    """


class ObjectStorageAPIError(BaseAPIException):
    """
    Object Storage API related error.
    """


class LeafCatalogueCategoryError(BaseAPIException):
    """
    Catalogue category is attempted to be added to a leaf parent catalogue category.
    """

    status_code = status.HTTP_409_CONFLICT
    response_detail = "Adding a catalogue category to a leaf parent catalogue category is not allowed"


class NonLeafCatalogueCategoryError(BaseAPIException):
    """
    Catalogue item is attempted to be added to a non-leaf catalogue category.
    """

    status_code = status.HTTP_409_CONFLICT


class DuplicateCatalogueCategoryPropertyNameError(BaseAPIException):
    """
    Catalogue category is attempted to be created with duplicate property names.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class InvalidPropertyTypeError(BaseAPIException):
    """
    The type of the provided value does not match the expected type of the property.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class MissingMandatoryProperty(BaseAPIException):
    """
    A mandatory property is missing when a catalogue item or item is attempted to be created.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class DuplicateRecordError(DatabaseError):
    """The record being added to the database is a duplicate."""

    status_code = status.HTTP_409_CONFLICT
    response_detail = "Duplicate record found"


class InvalidObjectIdError(DatabaseError):
    """
    The provided value is not a valid ObjectId.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    response_detail = "Invalid ID given"


class MissingRecordError(DatabaseError):
    """
    A specific database record was requested but could not be found.
    """

    def __init__(self, entity_id: str, entity_type: str, use_422=False):
        """
        Initialise the exception.

        :param entity_id: ID of the record that was found to be missing.
        :param entity_type: Name of the entity type e.g. catalogue categories/systems (Used for logging).
        :param use_422: Whether the error returned if uncaught should be a 422 (default is 404 when false).
        """
        super().__init__(
            detail=f"No {entity_type} found with ID: {entity_id}",
            response_detail=f"{entity_type.capitalize()} not found",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY if use_422 else status.HTTP_404_NOT_FOUND,
        )


class ChildElementsExistError(DatabaseError):
    """
    Exception raised when attempting to delete or update a catalogue category, catalogue item, or system that has child
    elements.
    """

    status_code = status.HTTP_409_CONFLICT


class PartOfCatalogueItemError(DatabaseError):
    """
    Exception raised when attempting to delete a manufacturer that is a part of a catalogue item
    """

    status_code = status.HTTP_409_CONFLICT


class PartOfCatalogueCategoryError(BaseAPIException):
    """
    Exception raised when attempting to delete a unit that is a part of a catalogue category
    """

    status_code = status.HTTP_409_CONFLICT


class PartOfItemError(DatabaseError):
    """
    Exception raised when attempting to delete a usage status that is a part of an item
    """

    status_code = status.HTTP_409_CONFLICT


class DatabaseIntegrityError(DatabaseError):
    """
    Exception raised when something is found in the database that shouldn't have been
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    response_detail = "Database integrity error"


class InvalidActionError(BaseAPIException):
    """
    Exception raised when trying to update an item's catalogue item ID
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class WriteConflictError(DatabaseError):
    """
    Exception raised when a transaction has a write conflict.
    """

    status_code = status.HTTP_409_CONFLICT


class ObjectStorageAPIAuthError(ObjectStorageAPIError):
    """
    Exception raised for auth failures or expired tokens while communicating with the Object Storage API.
    """

    status_code = status.HTTP_403_FORBIDDEN
    response_detail = "Unable to delete attachments and/or images"


class ObjectStorageAPIServerError(ObjectStorageAPIError):
    """
    Exception raised when server errors occur while communicating with the Object Storage API.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    response_detail = "Unable to delete attachments and/or images"


class PropertyValueError(BaseAPIException, ValueError):
    """Exception raised when there is an error caused by a property value"""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
