"""Module for providing the base of a migration script."""

from abc import ABC, abstractmethod

from pymongo.client_session import ClientSession
from pymongo.database import Database


class BaseMigration(ABC):
    """Base class for a migration with a forward and backward step."""

    @abstractmethod
    def __init__(self, database: Database):
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of this migration."""
        return ""

    @abstractmethod
    def forward(self, session: ClientSession):
        """Method for executing the migration."""

    def forward_after_transaction(self):
        """Method called after the forward function is called to do anything that can't be done inside a transaction
        (ONLY USE IF NECESSARY e.g. dropping a collection)."""

    @abstractmethod
    def backward(self, session: ClientSession):
        """Method for reversing the migration."""

    def backward_after_transaction(self):
        """
        Method called after the backward function is called to do anything that can't be done inside a transaction
        (ONLY USE IF NECESSARY e.g. dropping a collection).

        Note that this can run after other migrations as well so should not interfere with them.
        """
