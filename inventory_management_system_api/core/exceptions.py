"""
Module for custom exception classes.
"""


class DatabaseError(Exception):
    """
    Database related error.
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
