"""
Unit tests for the `ObjectStorageAPIClient` class.
"""

from unittest.mock import patch, MagicMock
from test.mock_data import VALID_ACCESS_TOKEN, EXPIRED_ACCESS_TOKEN

from bson import ObjectId

import pytest

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import ObjectStorageAPIAuthError, ObjectStorageAPIServerError
from inventory_management_system_api.core.object_storage_api_client import ObjectStorageAPIClient


class TestObjectStorageAPIClient:
    """Tests for the `ObjectStorageAPIClient` class."""

    @pytest.mark.parametrize(
        "method, endpoint",
        [
            (ObjectStorageAPIClient.delete_attachments, "/attachments"),
            (ObjectStorageAPIClient.delete_images, "/images"),
        ],
    )
    @patch("inventory_management_system_api.core.object_storage_api_client.requests.delete")
    def test_delete_success(self, mock_delete, method, endpoint):
        """
        Test `delete_attachments` and `delete_images` methods when Object Storage API responds with 204 No Content.
        """
        mock_delete.return_value.status_code = 204

        entity_id = str(ObjectId())

        method(entity_id, VALID_ACCESS_TOKEN)
        mock_delete.assert_called_once_with(
            f"{config.object_storage.api_url}{endpoint}",
            headers={"Authorization": f"Bearer {VALID_ACCESS_TOKEN}"},
            params={"entity_id": entity_id},
            timeout=config.object_storage.api_request_timeout_seconds,
        )

    @pytest.mark.parametrize(
        "method",
        [
            ObjectStorageAPIClient.delete_attachments,
            ObjectStorageAPIClient.delete_images,
        ],
    )
    @patch("inventory_management_system_api.core.object_storage_api_client.requests.delete")
    def test_delete_auth_error(self, mock_delete, method):
        """Test `ObjectStorageAPIAuthError` is raised when Object Storage API responds with 403."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "Invalid token or expired token"}
        mock_delete.return_value = mock_response

        with pytest.raises(ObjectStorageAPIAuthError) as exc:
            method(str(ObjectId()), EXPIRED_ACCESS_TOKEN)
        assert str(exc.value) == "Invalid token or expired token"

    @pytest.mark.parametrize(
        "method",
        [
            ObjectStorageAPIClient.delete_attachments,
            ObjectStorageAPIClient.delete_images,
        ],
    )
    @patch("inventory_management_system_api.core.object_storage_api_client.requests.delete")
    def test_delete_server_error(self, mock_delete, method):
        """Test `ObjectStorageAPIServerError` is raised when Object Storage API responds with 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Something went wrong"}
        mock_delete.return_value = mock_response

        with pytest.raises(ObjectStorageAPIServerError) as exc:
            method(str(ObjectId()), VALID_ACCESS_TOKEN)
        assert str(exc.value) == "Object Storage API server error: [500] {'detail': 'Something went wrong'}"
