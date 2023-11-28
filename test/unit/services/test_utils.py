"""
Unit tests for the `utils` in /services.
"""
import pytest

from inventory_management_system_api.core.exceptions import (
    MissingMandatoryCatalogueItemProperty,
    InvalidCatalogueItemPropertyTypeError,
)
from inventory_management_system_api.models.catalogue_category import CatalogueItemProperty
from inventory_management_system_api.schemas.catalogue_item import PropertyPostRequestSchema
from inventory_management_system_api.services import utils

DEFINED_PROPERTIES = [
    CatalogueItemProperty(name="Property A", type="number", unit="mm", mandatory=False),
    CatalogueItemProperty(name="Property B", type="boolean", mandatory=True),
    CatalogueItemProperty(name="Property C", type="string", unit="cm", mandatory=True),
]

SUPPLIED_PROPERTIES = [
    PropertyPostRequestSchema(name="Property A", value=20),
    PropertyPostRequestSchema(name="Property B", value=False),
    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
]

EXPECTED_PROCESSED_PROPERTIES = [
    {"name": "Property A", "value": 20, "unit": "mm"},
    {"name": "Property B", "value": False, "unit": None},
    {"name": "Property C", "value": "20x15x10", "unit": "cm"},
]


class TestProcessCatalogueItemProperties:
    """
    Tests for the `process_catalogue_item_properties` method.
    """

    def test_process_catalogue_item_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly.
        """
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES)
        assert result == EXPECTED_PROCESSED_PROPERTIES

    def test_process_catalogue_item_properties_with_missing_mandatory_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly with missing mandatory properties.
        """
        with pytest.raises(MissingMandatoryCatalogueItemProperty) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, [SUPPLIED_PROPERTIES[0]])
        assert str(exc.value) == f"Missing mandatory catalogue item property: '{SUPPLIED_PROPERTIES[1].name}'"

    def test_process_catalogue_item_properties_with_missing_mandatory_properties_when_check_skipped(
        self,
    ):
        """
        Test `test_process_catalogue_item_properties` works correctly with missing mandatory properties when the
        `skip_missing_mandatory_check` param is set to `True`.
        """
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, [SUPPLIED_PROPERTIES[0]], True)
        assert result == [EXPECTED_PROCESSED_PROPERTIES[0]]

    def test_process_catalogue_item_properties_with_missing_non_mandatory_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly with missing non-mandatory properties.
        """
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES[-2:])
        assert result == EXPECTED_PROCESSED_PROPERTIES[-2:]

    def test_process_catalogue_item_properties_with_undefined_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly with supplied properties that have not been defined.
        """
        supplied_properties = SUPPLIED_PROPERTIES + [PropertyPostRequestSchema(name="Property D", value=1)]
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert result == EXPECTED_PROCESSED_PROPERTIES

    def test_process_catalogue_item_properties_with_supplied_properties_and_no_defined_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly with supplied properties but no defined properties.
        """
        result = utils.process_catalogue_item_properties([], SUPPLIED_PROPERTIES)
        assert not result

    def test_process_catalogue_item_properties_without_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly without defined and supplied properties.
        """
        result = utils.process_catalogue_item_properties([], [])
        assert not result

    def test_process_catalogue_item_properties_with_invalid_value_type_for_string_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with invalid value type for a string catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(name="Property A", value=20),
            PropertyPostRequestSchema(name="Property B", value=False),
            PropertyPostRequestSchema(name="Property C", value=True),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value)
            == f"Invalid value type for catalogue item property '{supplied_properties[2].name}'. Expected type: string."
        )

    def test_process_catalogue_item_properties_with_invalid_value_type_for_number_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with invalid value type for a number catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(name="Property A", value="20"),
            PropertyPostRequestSchema(name="Property B", value=False),
            PropertyPostRequestSchema(name="Property C", value="20x15x10"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value)
            == f"Invalid value type for catalogue item property '{supplied_properties[0].name}'. Expected type: number."
        )

    def test_process_catalogue_item_properties_with_invalid_value_type_for_boolean_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with invalid value type for a boolean catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(name="Property A", value=20),
            PropertyPostRequestSchema(name="Property B", value="False"),
            PropertyPostRequestSchema(name="Property C", value="20x15x10"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for catalogue item property '{supplied_properties[1].name}'. "
            "Expected type: boolean."
        )
