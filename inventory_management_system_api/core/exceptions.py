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
        if status_code is not None:
            self.status_code = status_code


class DatabaseError(BaseAPIException):
    """
    Database related error.
    """


class ObjectStorageAPIError(Exception):
    """
    Object Storage API related error.
    """


class LeafCatalogueCategoryError(Exception):
    """
    Catalogue category is attempted to be added to a leaf parent catalogue category.
    """


class NonLeafCatalogueCategoryError(Exception):
    """
    Catalogue item is attempted to be added to a non-leaf catalogue category.
    """


class DuplicateCatalogueCategoryPropertyNameError(Exception):
    """
    Catalogue category is attempted to be created with duplicate property names.
    """


class InvalidPropertyTypeError(Exception):
    """
    The type of the provided value does not match the expected type of the property.
    """


class MissingMandatoryProperty(Exception):
    """
    A mandatory property is missing when a catalogue item or item is attempted to be created.
    """


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

    status_code = status.HTTP_404_NOT_FOUND
    response_detail = "Requested record was not found"


class ChildElementsExistError(DatabaseError):
    """
    Exception raised when attempting to delete or update a catalogue category, catalogue item, or system that has child
    elements.
    """


class PartOfCatalogueItemError(DatabaseError):
    """
    Exception raised when attempting to delete a manufacturer that is a part of a catalogue item
    """


class PartOfCatalogueCategoryError(DatabaseError):
    """
    Exception raised when attempting to delete a unit that is a part of a catalogue category
    """


class PartOfItemError(DatabaseError):
    """
    Exception raised when attempting to delete a usage status that is a part of an item
    """


class DatabaseIntegrityError(DatabaseError):
    """
    Exception raised when something is found in the database that shouldn't have been
    """


class InvalidActionError(DatabaseError):
    """
    Exception raised when trying to update an item's catalogue item ID
    """


class WriteConflictError(DatabaseError):
    """
    Exception raised when a transaction has a write conflict.
    """


class ObjectStorageAPIAuthError(ObjectStorageAPIError):
    """
    Exception raised for auth failures or expired tokens while communicating with the Object Storage API.
    """


class ObjectStorageAPIServerError(ObjectStorageAPIError):
    """
    Exception raised when server errors occur while communicating with the Object Storage API.
    """
