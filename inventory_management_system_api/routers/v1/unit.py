"""
Module for providing an API router which defines routes for managing Units using the `UnitService`
service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from inventory_management_system_api.core.exceptions import InvalidObjectIdError
from inventory_management_system_api.schemas.unit import UnitSchema
from inventory_management_system_api.services.unit import UnitService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/units", tags=["units"])


@router.get(path="/", summary="Get Units", response_description="List of Units")
def get_units(unit_service: Annotated[UnitService, Depends(UnitService)]) -> list[UnitSchema]:
    # pylint: disable=missing-function-docstring
    logger.info("Getting Units")

    try:
        units = unit_service.list()
        return [UnitSchema(**unit.model_dump()) for unit in units]
    except InvalidObjectIdError:
        # As this endpoint filters, and to hide the database behaviour, we treat any invalid id
        # the same as a valid one that doesn't exist i.e. return an empty list
        return []
