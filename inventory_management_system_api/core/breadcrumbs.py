"""
Useful functions for computing breadcrumbs
"""
import logging
from typing import Optional

from inventory_management_system_api.core.consts import BREADCRUMBS_TRAIL_MAX_LENGTH
from inventory_management_system_api.core.exceptions import (
    DatabaseIntegrityError,
    EntityNotFoundError,
    InvalidObjectIdError,
)
from inventory_management_system_api.schemas.breadcrumbs import BreadcrumbsGetSchema
from inventory_management_system_api.services.catalogue_category import CatalogueCategoryService
from inventory_management_system_api.services.system import SystemService

logger = logging.getLogger()


def compute_breadcrumbs(
    entity_id: str, entity_service: CatalogueCategoryService | SystemService
) -> BreadcrumbsGetSchema:
    """
    Compute breadcrumbs for an entity given it's ID

    :param entity_id: ID of the entity to look up
    :param entity_service: Service for looking up entities - It is assumed that this has a get(entity_id) function
                           that either returns the entity (complete with an id, code and parent_id field), or None if
                           it isn't found
    :raises DatabaseIntegrityError: If the entity_service.get either raises an InvalidObjectIdError or returns None
                                    for any parent entity found as this should not be possible if the database
                                    integrity is maintained
    :raises InvalidObjectIdError: If the given entity_id is invalid
    :raises EntityNotFoundError: If the entity with the given entity_id is not found
    :return: See BreadcrumbsGetSchema
    """
    # For logging
    entity_type: str = "unknown"
    if isinstance(entity_service, CatalogueCategoryService):
        entity_type = "catalogue category"
    elif isinstance(entity_service, SystemService):
        entity_type = "system"

    logger.info("Computing breadcrumbs for %s with ID %s", entity_type, entity_id)

    trail: list[tuple[str, str]] = []
    next_id: Optional[str] = entity_id

    try:
        # Keep adding to the trail until either the max length is reached, or the next id to look up is None
        # i.e. there is no parent
        while len(trail) < BREADCRUMBS_TRAIL_MAX_LENGTH and next_id is not None:
            entity = entity_service.get(next_id)
            if entity is None:
                raise EntityNotFoundError(f"{entity_type.capitalize()} with id {next_id} was not found")
            trail.append((entity.id, entity.code))
            next_id = entity.parent_id
    except (InvalidObjectIdError, EntityNotFoundError) as exc:
        # If occurred on first element, then it effects the given entity_id, otherwise
        # should be a database integrity issue as it effects one of the parents
        if len(trail) == 0:
            logger.exception(str(exc))
            raise exc
        else:
            message = (
                f"{entity_type.capitalize()} with ID {next_id} was "
                f"{'invalid' if isinstance(exc, InvalidObjectIdError) else 'not found'}"
                f"while finding breadcrumbs for {entity_id}"
            )
            logger.exception(message)
            raise DatabaseIntegrityError(message) from exc

    # Reverse trail here as should be faster than inserting to front
    return BreadcrumbsGetSchema(trail=trail[::-1], full_trail=next_id is None)
