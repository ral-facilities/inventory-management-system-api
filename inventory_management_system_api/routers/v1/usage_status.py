"""
Module for providing an API router which defines routes for managing Usage statuses using the `UsageStatusService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from inventory_management_system_api.schemas.usage_status import UsageStatusSchema
from inventory_management_system_api.services.usage_status import UsageStatusService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/usage-statuses", tags=["usage statuses"])


@router.get(path="", summary="Get usage statuses", response_description="List of usage statuses")
def get_usage_statuses(
    usage_status_service: Annotated[UsageStatusService, Depends(UsageStatusService)]
) -> list[UsageStatusSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting Usage statuses")

    usage_statuses = usage_status_service.list()
    return [UsageStatusSchema(**usage_status.model_dump()) for usage_status in usage_statuses]
