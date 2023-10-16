"""
Module for defining the API schema models for representing breadcrumbs
"""
from pydantic import BaseModel, Field

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH


class BreadcrumbsGetSchema(BaseModel):
    """
    Schema model for a breadcrumbs get request
    """

    trail: list[tuple[str, str]] = Field(
        description="List of tuples representing the trail of parents for the entity in the form (entity_id, name). "
        "Where the 'entity_id' is a string giving the ID of the entity and 'name' is a string representation of how "
        f"it should be displayed in the breadcrumb. A maximum number of ${BREADCRUMBS_TRAIL_MAX_LENGTH} are returned."
    )
    full_trail: bool = Field(
        description="Whether the entire parent hierarchy is reflected in the returned 'trail'. Will be False "
        f"if the entity has more than ${BREADCRUMBS_TRAIL_MAX_LENGTH - 1} parents above it."
    )
