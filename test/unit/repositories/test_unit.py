"""
Unit tests for the `UnitRepo` repository
"""

from bson import ObjectId
from inventory_management_system_api.core.custom_object_id import CustomObjectId

from inventory_management_system_api.models.units import UnitOut


UNIT_A_INFO = {"value": "millimeter"}
UNIT_B_INFO = {"value": "micrometer"}


def test_list(test_helpers, database_mock, unit_repository):
    """
    Test getting units

    Verify that the `list` method properly handles the retrieval of units without filters
    """
    unit_a = UnitOut(id=str(ObjectId()), **UNIT_A_INFO)
    unit_b = UnitOut(id=str(ObjectId()), **UNIT_B_INFO)

    # Mock `find` to return a list of Unit documents
    test_helpers.mock_find(
        database_mock.units,
        [{"_id": CustomObjectId(unit_a.id), **UNIT_A_INFO}, {"_id": CustomObjectId(unit_b.id), **UNIT_B_INFO}],
    )

    retrieved_units = unit_repository.list()

    database_mock.units.find.assert_called_once_with()
    assert retrieved_units == [unit_a, unit_b]
