"""
Module for connecting to a MongoDB database.
"""

from contextlib import contextmanager
from typing import Annotated, Generator

from fastapi import Depends
from pymongo import MongoClient
from pymongo.client_session import ClientSession
from pymongo.database import Database
from pymongo.errors import OperationFailure

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import WriteConflictError

db_config = config.database
mongodb_client = MongoClient(
    f"{db_config.protocol.get_secret_value()}://"
    f"{db_config.username.get_secret_value()}:{db_config.password.get_secret_value()}@"
    f"{db_config.host_and_options.get_secret_value()}",
    tz_aware=True,
)


def get_database() -> Database:
    """
    Connects to a MongoDB database and returns the specified database.

    :return: The MongoDB database object.
    """
    return mongodb_client[db_config.name.get_secret_value()]


@contextmanager
def start_session_transaction(action_description: str) -> Generator[ClientSession, None, None]:
    """
    Starts a MongoDB session followed by a transaction and returns the session to use.

    Also handles write conflicts.

    :param action_description: Description of what the transaction is doing so it can be used in any raised errors.
    :raises WriteConflictError: If there a write conflict during the transaction.
    """

    with mongodb_client.start_session() as session:
        with session.start_transaction():
            try:
                yield session
            except OperationFailure as exc:
                if "write conflict" in str(exc).lower():
                    raise WriteConflictError(
                        f"Write conflict while {action_description}. Please try again later."
                    ) from exc
                raise exc


DatabaseDep = Annotated[Database, Depends(get_database)]
