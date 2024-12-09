"""
Unit tests for the `utils` in /services.
"""

from test.mock_data import SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.exceptions import (
    DuplicateCatalogueCategoryPropertyNameError,
    InvalidPropertyTypeError,
    MissingMandatoryProperty,
)
from inventory_management_system_api.models.catalogue_category import AllowedValues, CatalogueCategoryPropertyOut
from inventory_management_system_api.models.setting import SparesDefinitionOut
from inventory_management_system_api.schemas.catalogue_item import PropertyPostSchema
from inventory_management_system_api.services import utils

DEFINED_PROPERTIES = [
    CatalogueCategoryPropertyOut(
        id=str(ObjectId()), name="Property A", type="number", unit_id=str(ObjectId()), unit="mm", mandatory=False
    ),
    CatalogueCategoryPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
    CatalogueCategoryPropertyOut(
        id=str(ObjectId()), name="Property C", type="string", unit_id=str(ObjectId()), unit="cm", mandatory=True
    ),
    CatalogueCategoryPropertyOut(
        id=str(ObjectId()),
        name="Property D",
        type="number",
        unit_id=str(ObjectId()),
        unit="mm",
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[2, 4, 6]),
    ),
    CatalogueCategoryPropertyOut(
        id=str(ObjectId()),
        name="Property E",
        type="string",
        mandatory=False,
        allowed_values=AllowedValues(type="list", values=["red", "green"]),
    ),
]

SUPPLIED_PROPERTIES = [
    PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20, unit_id=DEFINED_PROPERTIES[0].unit_id),
    PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
    PropertyPostSchema(
        id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10", unit_id=DEFINED_PROPERTIES[2].unit_id
    ),
    PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2, unit_id=DEFINED_PROPERTIES[3].unit_id),
    PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
]

EXPECTED_PROCESSED_PROPERTIES = [
    {
        "id": DEFINED_PROPERTIES[0].id,
        "name": "Property A",
        "value": 20,
        "unit": "mm",
        "unit_id": DEFINED_PROPERTIES[0].unit_id,
    },
    {"id": DEFINED_PROPERTIES[1].id, "name": "Property B", "value": False, "unit": None, "unit_id": None},
    {
        "id": DEFINED_PROPERTIES[2].id,
        "name": "Property C",
        "value": "20x15x10",
        "unit": "cm",
        "unit_id": DEFINED_PROPERTIES[2].unit_id,
    },
    {
        "id": DEFINED_PROPERTIES[3].id,
        "name": "Property D",
        "value": 2,
        "unit": "mm",
        "unit_id": DEFINED_PROPERTIES[3].unit_id,
    },
    {"id": DEFINED_PROPERTIES[4].id, "name": "Property E", "value": "red", "unit": None, "unit_id": None},
]


class TestGenerateCode:
    """Tests for the `generate_code` method"""

    def test_generate_code(self):
        """Test `generate_code` works correctly"""

        result = utils.generate_code("string with spaces", "entity_type")
        assert result == "string-with-spaces"


class TestDuplicateCategoryPropertyNames:
    """Tests for the `check_duplicate_property_names` method"""

    def test_with_no_duplicate_names(self):
        """
        Test `check_duplicate_property_names` works correctly when there are no duplicate names given
        """

        utils.check_duplicate_property_names(DEFINED_PROPERTIES)

    def test_with_duplicate_names(self):
        """Test `check_duplicate_property_names` works correctly when there are duplicate names given"""

        with pytest.raises(DuplicateCatalogueCategoryPropertyNameError) as exc:
            utils.check_duplicate_property_names([*DEFINED_PROPERTIES, DEFINED_PROPERTIES[-1]])
        assert str(exc.value) == f"Duplicate property name: {DEFINED_PROPERTIES[-1].name}"


class TestProcessProperties:
    """
    Tests for the `process_properties` method.
    """

    def test_process_properties(self):
        """
        Test `process_properties` works correctly.
        """
        result = utils.process_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES)
        assert result == EXPECTED_PROCESSED_PROPERTIES

    def test_process_properties_with_missing_mandatory_properties(self):
        """
        Test `process_properties` works correctly with missing mandatory properties.
        """
        with pytest.raises(MissingMandatoryProperty) as exc:
            utils.process_properties(DEFINED_PROPERTIES, [SUPPLIED_PROPERTIES[0]])
        assert str(exc.value) == f"Missing mandatory property with ID: '{SUPPLIED_PROPERTIES[1].id}'"

    def test_process_properties_with_missing_non_mandatory_properties(self):
        """
        Test `process_properties` works correctly with missing non-mandatory properties.
        """
        result = utils.process_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES[1:4])
        assert result == [
            {**EXPECTED_PROCESSED_PROPERTIES[0], "value": None},
            *EXPECTED_PROCESSED_PROPERTIES[1:4],
            {**EXPECTED_PROCESSED_PROPERTIES[4], "value": None},
        ]

    def test_process_properties_with_undefined_properties(self):
        """
        Test `process_properties` works correctly with supplied properties that have not been defined.
        """
        supplied_properties = SUPPLIED_PROPERTIES + [PropertyPostSchema(id=str(ObjectId()), name="Property F", value=1)]
        result = utils.process_properties(DEFINED_PROPERTIES, supplied_properties)
        assert result == EXPECTED_PROCESSED_PROPERTIES

    def test_process_properties_with_none_non_mandatory_properties(self):
        """
        Test `process_properties` works correctly when explicitly giving a value of None
        for non-mandatory properties.
        """
        result = utils.process_properties(
            DEFINED_PROPERTIES,
            [
                PropertyPostSchema(
                    id=DEFINED_PROPERTIES[0].id, name="Property A", value=None, unit_id=DEFINED_PROPERTIES[0].unit_id
                ),
                PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
                PropertyPostSchema(
                    id=DEFINED_PROPERTIES[2].id,
                    name="Property C",
                    value="20x15x10",
                    unit_id=DEFINED_PROPERTIES[2].unit_id,
                ),
                PropertyPostSchema(
                    id=DEFINED_PROPERTIES[3].id, name="Property D", value=2, unit_id=DEFINED_PROPERTIES[3].unit_id
                ),
                PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value=None),
            ],
        )
        assert result == [
            {
                "id": DEFINED_PROPERTIES[0].id,
                "name": "Property A",
                "value": None,
                "unit": "mm",
                "unit_id": DEFINED_PROPERTIES[0].unit_id,
            },
            {"id": DEFINED_PROPERTIES[1].id, "name": "Property B", "value": False, "unit": None, "unit_id": None},
            {
                "id": DEFINED_PROPERTIES[2].id,
                "name": "Property C",
                "value": "20x15x10",
                "unit": "cm",
                "unit_id": DEFINED_PROPERTIES[2].unit_id,
            },
            {
                "id": DEFINED_PROPERTIES[3].id,
                "name": "Property D",
                "value": 2,
                "unit": "mm",
                "unit_id": DEFINED_PROPERTIES[3].unit_id,
            },
            {"id": DEFINED_PROPERTIES[4].id, "name": "Property E", "value": None, "unit": None, "unit_id": None},
        ]

    def test_process_properties_with_supplied_properties_and_no_defined_properties(self):
        """
        Test `process_properties` works correctly with supplied properties but no defined properties.
        """
        result = utils.process_properties([], SUPPLIED_PROPERTIES)
        assert not result

    def test_process_properties_without_properties(self):
        """
        Test `process_properties` works correctly without defined and supplied properties.
        """
        result = utils.process_properties([], [])
        assert not result

    def test_process_properties_with_invalid_value_type_for_string_property(self):
        """
        Test `process_properties` works correctly with invalid value type for a string catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value=True),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidPropertyTypeError) as exc:
            utils.process_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for property with ID '{supplied_properties[2].id}'. "
            "Expected type: string."
        )

    def test_process_properties_with_invalid_value_type_for_number_property(self):
        """
        Test `process_properties` works correctly with invalid value type for a number catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value="20"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidPropertyTypeError) as exc:
            utils.process_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for property with ID '{supplied_properties[0].id}'. "
            "Expected type: number."
        )

    def test_process_properties_with_invalid_value_type_for_boolean_property(self):
        """
        Test `process_properties` works correctly with invalid value type for a boolean catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value="False"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidPropertyTypeError) as exc:
            utils.process_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for property with ID '{supplied_properties[1].id}'. "
            "Expected type: boolean."
        )

    def test_process_properties_with_invalid_value_type_for_mandatory_property(self):
        """
        Test `process_properties` works correctly with a None value given for a mandatory property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value=None),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidPropertyTypeError) as exc:
            utils.process_properties(DEFINED_PROPERTIES, supplied_properties)

        assert str(exc.value) == f"Mandatory property with ID '{supplied_properties[2].id}' cannot be None."

    def test_process_properties_with_invalid_allowed_value_list_number(self):
        """
        Test `process_properties` works correctly when given an invalid value for a number property with a specific list
        of allowed values
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=10),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidPropertyTypeError) as exc:
            utils.process_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value for property with ID '{supplied_properties[3].id}'. "
            "Expected one of 2, 4, 6."
        )

    def test_process_properties_with_invalid_allowed_value_list_string(self):
        """
        Test `process_properties` works correctly when given an invalid value for a string property with a specific
        list of allowed values
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=4),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="invalid"),
        ]

        with pytest.raises(InvalidPropertyTypeError) as exc:
            utils.process_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value for property with ID '{supplied_properties[4].id}'. "
            "Expected one of red, green."
        )


class TestGetUsageStatusIdsFromSparesDefinition:
    """Tests for the `get_usage_status_ids_from_spares_definition` method."""

    def test_get_usage_status_ids_from_spares_definition(self):
        """Tests `get_usage_status_ids_from_spares_definition` works correctly."""

        result = utils.get_usage_status_ids_from_spares_definition(
            SparesDefinitionOut(**SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED)
        )
        assert result == [
            CustomObjectId(usage_status["id"])
            for usage_status in SETTING_SPARES_DEFINITION_OUT_DATA_NEW_USED["usage_statuses"]
        ]


class TestPrepareForNumberOfSparesRecalculation:
    """Tests for the `prepare_for_number_of_spares_recalculation` method."""

    def test_prepare_for_number_of_spares_recalculation(self):
        """Tests `prepare_for_number_of_spares_recalculation` works correctly."""

        catalogue_item_id = MagicMock()
        catalogue_item_repository = MagicMock()
        session = MagicMock()
        utils.prepare_for_number_of_spares_recalculation(catalogue_item_id, catalogue_item_repository, session)

        catalogue_item_repository.update_number_of_spares.assert_called_once_with(
            catalogue_item_id, None, session=session
        )


class TestPerformNumberOfSparesRecalculation:
    """Tests for the `perform_number_of_spares_recalculation` method."""

    def test_perform_number_of_spares_recalculation(self):
        """Tests `perform_number_of_spares_recalculation` works correctly."""

        catalogue_item_id = MagicMock()
        usage_status_ids = MagicMock()
        catalogue_item_repository = MagicMock()
        item_repository = MagicMock()
        session = MagicMock()

        utils.perform_number_of_spares_recalculation(
            catalogue_item_id, usage_status_ids, catalogue_item_repository, item_repository, session
        )

        item_repository.count_with_usage_status_ids_in.assert_called_once_with(
            catalogue_item_id, usage_status_ids, session=session
        )
        expected_new_number_of_spares = item_repository.count_with_usage_status_ids_in.return_value
        catalogue_item_repository.update_number_of_spares(
            catalogue_item_id, expected_new_number_of_spares, session=session
        )
