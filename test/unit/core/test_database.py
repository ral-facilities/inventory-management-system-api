"""
Unit tests for functions inside the `database` module.
"""

from unittest.mock import patch

import pytest
from pymongo.errors import OperationFailure

from inventory_management_system_api.core.database import start_session_transaction
from inventory_management_system_api.core.exceptions import WriteConflictError


@patch("inventory_management_system_api.core.database.mongodb_client")
def test_start_session_transaction(mock_mongodb_client):
    """Test `start_session_transaction`."""

    expected_session = mock_mongodb_client.start_session.return_value.__enter__.return_value

    with start_session_transaction("testing") as session:
        pass

    assert expected_session == session
    expected_session.start_transaction.assert_called_once()


@patch("inventory_management_system_api.core.database.mongodb_client")
def test_start_session_transaction_with_operation_failure(mock_mongodb_client):
    """Test `start_session_transaction` when there is an operation failure inside the transaction."""

    expected_session = mock_mongodb_client.start_session.return_value.__enter__.return_value

    with pytest.raises(OperationFailure) as exc:
        with start_session_transaction("testing") as session:
            raise OperationFailure("Some operation error.")

    assert expected_session == session
    expected_session.start_transaction.assert_called_once()
    assert str(exc.value) == "Some operation error."


@patch("inventory_management_system_api.core.database.mongodb_client")
def test_start_session_transaction_with_operation_failure_write_conflict(mock_mongodb_client):
    """Test `start_session_transaction` when there is an operation failure due to a write conflict inside the
    transaction."""

    expected_session = mock_mongodb_client.start_session.return_value.__enter__.return_value

    with pytest.raises(WriteConflictError) as exc:
        with start_session_transaction("testing") as session:
            raise OperationFailure("Write conflict during plan execution and yielding is disabled.")

    assert expected_session == session
    expected_session.start_transaction.assert_called_once()
    assert str(exc.value) == "Write conflict while testing. Please try again later."
