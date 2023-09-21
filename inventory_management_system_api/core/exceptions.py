"""
Module for custom exception classes.
"""


class DatabaseError(Exception):
    """
    Database related error.
    """


class LeafCategoryError(Exception):
    """
    Catalogue category is attempted to be added to a leaf parent catalogue category.
    """


class NonLeafCategoryError(Exception):
    """
    Catalogue item is attempted to be added to a non-leaf catalogue category.
    """


class InvalidCatalogueItemPropertyTypeError(Exception):
    """
    The type of the provided value does not match the expected type of the catalogue item property.
    """


class MissingMandatoryCatalogueItemProperty(Exception):
    """
    A mandatory catalogue item property is missing when a catalogue item is attempted to be created.
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


class ChildrenElementsExistError(DatabaseError):
    """
    Exception raised when attempting to delete a catalogue category that has children elements.
    """
