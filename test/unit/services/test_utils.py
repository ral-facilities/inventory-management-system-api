"""
Unit tests for the `utils` in /services.
"""

import pytest

from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    InvalidCatalogueItemPropertyTypeError,
    MissingMandatoryCatalogueItemProperty,
)
from inventory_management_system_api.models.catalogue_category import (
    AllowedValues,
    CatalogueItemPropertyOut,
)
from inventory_management_system_api.schemas.catalogue_item import PropertyPostRequestSchema
from inventory_management_system_api.services import utils

DEFINED_PROPERTIES = [
    CatalogueItemPropertyOut(id=str(ObjectId()), name="Property A", type="number", unit="mm", mandatory=False),
    CatalogueItemPropertyOut(id=str(ObjectId()), name="Property B", type="boolean", mandatory=True),
    CatalogueItemPropertyOut(id=str(ObjectId()), name="Property C", type="string", unit="cm", mandatory=True),
    CatalogueItemPropertyOut(
        id=str(ObjectId()),
        name="Property D",
        type="number",
        unit="mm",
        mandatory=True,
        allowed_values=AllowedValues(type="list", values=[2, 4, 6]),
    ),
    CatalogueItemPropertyOut(
        id=str(ObjectId()),
        name="Property E",
        type="string",
        mandatory=False,
        allowed_values=AllowedValues(type="list", values=["red", "green"]),
    ),
]

SUPPLIED_PROPERTIES = [
    PropertyPostRequestSchema(name="Property A", value=20),
    PropertyPostRequestSchema(name="Property B", value=False),
    PropertyPostRequestSchema(name="Property C", value="20x15x10"),
    PropertyPostRequestSchema(name="Property D", value=2),
    PropertyPostRequestSchema(name="Property E", value="red"),
]

EXPECTED_PROCESSED_PROPERTIES = [
    {"name": "Property A", "value": 20, "unit": "mm"},
    {"name": "Property B", "value": False, "unit": None},
    {"name": "Property C", "value": "20x15x10", "unit": "cm"},
    {"name": "Property D", "value": 2, "unit": "mm"},
    {"name": "Property E", "value": "red", "unit": None},
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

    def test_process_catalogue_item_properties_with_missing_non_mandatory_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly with missing non-mandatory properties.
        """
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES[1:4])
        assert result == [
            {**EXPECTED_PROCESSED_PROPERTIES[0], "value": None},
            *EXPECTED_PROCESSED_PROPERTIES[1:4],
            {**EXPECTED_PROCESSED_PROPERTIES[4], "value": None},
        ]

    def test_process_catalogue_item_properties_with_undefined_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly with supplied properties that have not been defined.
        """
        supplied_properties = SUPPLIED_PROPERTIES + [PropertyPostRequestSchema(name="Property F", value=1)]
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert result == EXPECTED_PROCESSED_PROPERTIES

    def test_process_catalogue_item_properties_with_none_non_mandatory_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly when explicitely giving a value of None
        for non-mandatory properties.
        """
        result = utils.process_catalogue_item_properties(
            DEFINED_PROPERTIES,
            [
                PropertyPostRequestSchema(name="Property A", value=None),
                PropertyPostRequestSchema(name="Property B", value=False),
                PropertyPostRequestSchema(name="Property C", value="20x15x10"),
                PropertyPostRequestSchema(name="Property D", value=2),
                PropertyPostRequestSchema(name="Property E", value=None),
            ],
        )
        assert result == [
            {"name": "Property A", "value": None, "unit": "mm"},
            {"name": "Property B", "value": False, "unit": None},
            {"name": "Property C", "value": "20x15x10", "unit": "cm"},
            {"name": "Property D", "value": 2, "unit": "mm"},
            {"name": "Property E", "value": None, "unit": None},
        ]

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
            PropertyPostRequestSchema(name="Property D", value=2),
            PropertyPostRequestSchema(name="Property E", value="red"),
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
            PropertyPostRequestSchema(name="Property D", value=2),
            PropertyPostRequestSchema(name="Property E", value="red"),
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
            PropertyPostRequestSchema(name="Property D", value=2),
            PropertyPostRequestSchema(name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for catalogue item property '{supplied_properties[1].name}'. "
            "Expected type: boolean."
        )

    def test_process_catalogue_item_properties_with_invalid_value_type_for_mandatory_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with a None value given for a mandatory property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(name="Property A", value=20),
            PropertyPostRequestSchema(name="Property B", value=False),
            PropertyPostRequestSchema(name="Property C", value=None),
            PropertyPostRequestSchema(name="Property D", value=2),
            PropertyPostRequestSchema(name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert str(exc.value) == f"Mandatory catalogue item property '{supplied_properties[2].name}' cannot be None."

    def test_process_catalogue_item_properties_with_invalid_allowed_value_list_number(self):
        """
        Test `process_catalogue_item_properties` works correctly when given an invalid value for a number catalogue
        item property with a specific list of allowed values
        """
        supplied_properties = [
            PropertyPostRequestSchema(name="Property A", value=20),
            PropertyPostRequestSchema(name="Property B", value=False),
            PropertyPostRequestSchema(name="Property C", value="20x15x10"),
            PropertyPostRequestSchema(name="Property D", value=10),
            PropertyPostRequestSchema(name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value for catalogue item property '{supplied_properties[3].name}'. "
            "Expected one of 2, 4, 6."
        )

    def test_process_catalogue_item_properties_with_invalid_allowed_value_list_string(self):
        """
        Test `process_catalogue_item_properties` works correctly when given an invalid value for a string catalogue
        item property with a specific list of allowed values
        """
        supplied_properties = [
            PropertyPostRequestSchema(name="Property A", value=20),
            PropertyPostRequestSchema(name="Property B", value=False),
            PropertyPostRequestSchema(name="Property C", value="20x15x10"),
            PropertyPostRequestSchema(name="Property D", value=4),
            PropertyPostRequestSchema(name="Property E", value="invalid"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value for catalogue item property '{supplied_properties[4].name}'. "
            "Expected one of red, green."
        )
