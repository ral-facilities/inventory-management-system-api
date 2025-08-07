"""
Module for providing an API router which defines routes for managing rules using the `RuleService` service.
"""

# We don't define docstrings in router methods as they would end up in the openapi/swagger docs. We also expect
# some duplicate code inside routers as the code is similar between entities and error handling may be repeated.
# pylint: disable=missing-function-docstring
# pylint: disable=duplicate-code

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from inventory_management_system_api.core.exceptions import InvalidObjectIdError
from inventory_management_system_api.schemas.rule import RuleSchema
from inventory_management_system_api.services.rule import RuleService

logger = logging.getLogger()

router = APIRouter(prefix="/v1/rules", tags=["rules"])

RuleServiceDep = Annotated[RuleService, Depends(RuleService)]


@router.get("", summary="Get rules", response_description="List of rules")
def get_rules(rule_service: RuleServiceDep) -> list[RuleSchema]:
    logger.info("Getting rules")

    try:
        rules = rule_service.list()
        return [RuleSchema(**rule.model_dump()) for rule in rules]
    except InvalidObjectIdError:
        # As this endpoint filters, and to hide the database behaviour, we treat any invalid id the same as a valid one
        # that doesn't exist i.e. return an empty list
        return []
