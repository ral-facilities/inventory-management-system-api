"""
Module for custom exception classes.
"""


class DatabaseError(Exception):
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
    """
    The record being added to the database is a duplicate.
    """


class InvalidObjectIdError(DatabaseError):
    """
    The provided value is not a valid ObjectId.
    """


class MissingRecordError(DatabaseError):
    """
    A specific database record was requested but could not be found.
    """


class ChildElementsExistError(DatabaseError):
    """
    Exception raised when attempting to delete or update a catalogue category, catalogue item, or system that has child
    elements.
    """


class IsAReplacementForError(DatabaseError):
    """
    Exception raised when attempting to delete a catalogue item that is a replacement for another catalogue item.
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
