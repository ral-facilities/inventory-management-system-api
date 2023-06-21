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
