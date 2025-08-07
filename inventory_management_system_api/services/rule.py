"""
Module for providing a service for managing rules using the `RuleRepo` repository.
"""

from typing import Annotated

from fastapi import Depends

from inventory_management_system_api.models.rule import RuleOut
from inventory_management_system_api.repositories.rule import RuleRepo


class RuleService:
    """
    Service for managing rules.
    """

    def __init__(self, rule_repository: Annotated[RuleRepo, Depends(RuleRepo)]) -> None:
        """
        Initialise the `RuleService` with a `RuleRepo` repository.

        :param rule_repository: `RuleRepo` repository to use.
        """
        self._rule_repository = rule_repository

    def list(self) -> list[RuleOut]:
        """
        Retrieve rules based on the provided filters.

        :return: List of rules or an empty list if no rules are retrieved.
        """
        return self._rule_repository.list()
