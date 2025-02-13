"""
Module for providing an implementation of a client class for interacting with the Object Storage API.
"""

import requests
from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.exceptions import ObjectStorageAPIAuthError, ObjectStorageAPIServerError


class ObjectStorageAPIClient:
    """
    Client class for interacting with the Object Storage API.
    """

    @staticmethod
    def delete_attachments(access_token: str, entity_id: str) -> None:
        """
        Delete attachments associated with the given entity ID.

        :param access_token: The JWT access token for auth with the Object Storage API.
        :param entity_id: The ID of the entity whose attachments should be deleted.
        """
        ObjectStorageAPIClient._delete("/attachments", access_token, entity_id)

    @staticmethod
    def delete_images(access_token: str, entity_id: str) -> None:
        """
        Delete images associated with the given entity ID.

        :param access_token: The JWT access token for auth with the Object Storage API.
        :param entity_id: The ID of the entity whose images should be deleted.
        """
        ObjectStorageAPIClient._delete("/images", access_token, entity_id)

    @staticmethod
    def _delete(endpoint: str, access_token: str, entity_id: str) -> None:
        """
        Sends a `DELETE` request to the Object Storage API with the provided JWT access token as a header and the entity
        ID as a query parameter.

        :param endpoint: The Object Storage API endpoint to send the request to.
        :param access_token: The JWT access token for auth with the Object Storage API.
        :param entity_id: The ID of the entity whose objects should be deleted.
        :raises ObjectStorageAPIAuthenticationError: If auth with the Object Storage API fails.
        :raises ObjectStorageAPIServerError: If any other error is encountered while communicating with the Object
            Storage API.
        """
        url = f"{config.object_storage.api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"entity_id": entity_id}

        # pylint: disable=missing-timeout
        response = requests.delete(url, headers=headers, params=params)

        if response.status_code == 403:
            raise ObjectStorageAPIAuthError(response.json()["detail"])

        if response.status_code != 204:
            raise ObjectStorageAPIServerError(
                f"Object Storage API server error: [{response.status_code}] {response.json()}"
            )
