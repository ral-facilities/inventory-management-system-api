"""
Unit tests for the `utils` in /services.
"""

import pytest

from bson import ObjectId

from inventory_management_system_api.core.exceptions import (
    DuplicateCatalogueItemPropertyNameError,
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
    PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
    PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
    PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
    PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
    PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
]

EXPECTED_PROCESSED_PROPERTIES = [
    {"id": DEFINED_PROPERTIES[0].id, "name": "Property A", "value": 20, "unit": "mm"},
    {"id": DEFINED_PROPERTIES[1].id, "name": "Property B", "value": False, "unit": None},
    {"id": DEFINED_PROPERTIES[2].id, "name": "Property C", "value": "20x15x10", "unit": "cm"},
    {"id": DEFINED_PROPERTIES[3].id, "name": "Property D", "value": 2, "unit": "mm"},
    {"id": DEFINED_PROPERTIES[4].id, "name": "Property E", "value": "red", "unit": None},
]


class TestGenerateCode:
    """Tests for the `generate_code` method"""

    def test_generate_code(self):
        """Test `generate_code` works correctly"""

        result = utils.generate_code("string with spaces", "entity_type")
        assert result == "string-with-spaces"


class TestDuplicateCatalogueItemPropertyNames:
    """Tests for the `check_duplicate_catalogue_item_property_names` method"""

    def test_with_no_duplicate_names(self):
        """
        Test `check_duplicate_catalogue_item_property_names` works correctly when there are no duplicate names given
        """

        utils.check_duplicate_catalogue_item_property_names(DEFINED_PROPERTIES)

    def test_with_duplicate_names(self):
        """Test `check_duplicate_catalogue_item_property_names` works correctly when there are duplicate names given"""

        with pytest.raises(DuplicateCatalogueItemPropertyNameError) as exc:
            utils.check_duplicate_catalogue_item_property_names([*DEFINED_PROPERTIES, DEFINED_PROPERTIES[-1]])
        assert str(exc.value) == f"Duplicate catalogue item property name: {DEFINED_PROPERTIES[-1].name}"


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
        assert str(exc.value) == f"Missing mandatory catalogue item property with ID: '{SUPPLIED_PROPERTIES[1].id}'"

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
        supplied_properties = SUPPLIED_PROPERTIES + [
            PropertyPostRequestSchema(id=str(ObjectId()), name="Property F", value=1)
        ]
        result = utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert result == EXPECTED_PROCESSED_PROPERTIES

    def test_process_catalogue_item_properties_with_none_non_mandatory_properties(self):
        """
        Test `process_catalogue_item_properties` works correctly when explicitly giving a value of None
        for non-mandatory properties.
        """
        result = utils.process_catalogue_item_properties(
            DEFINED_PROPERTIES,
            [
                PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=None),
                PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
                PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
                PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
                PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value=None),
            ],
        )
        assert result == [
            {"id": DEFINED_PROPERTIES[0].id, "name": "Property A", "value": None, "unit": "mm"},
            {"id": DEFINED_PROPERTIES[1].id, "name": "Property B", "value": False, "unit": None},
            {"id": DEFINED_PROPERTIES[2].id, "name": "Property C", "value": "20x15x10", "unit": "cm"},
            {"id": DEFINED_PROPERTIES[3].id, "name": "Property D", "value": 2, "unit": "mm"},
            {"id": DEFINED_PROPERTIES[4].id, "name": "Property E", "value": None, "unit": None},
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
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value=True),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for catalogue item property with ID '{supplied_properties[2].id}'. "
            "Expected type: string."
        )

    def test_process_catalogue_item_properties_with_invalid_value_type_for_number_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with invalid value type for a number catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value="20"),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for catalogue item property with ID '{supplied_properties[0].id}'. "
            "Expected type: number."
        )

    def test_process_catalogue_item_properties_with_invalid_value_type_for_boolean_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with invalid value type for a boolean catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value="False"),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value type for catalogue item property with ID '{supplied_properties[1].id}'. "
            "Expected type: boolean."
        )

    def test_process_catalogue_item_properties_with_invalid_value_type_for_mandatory_property(self):
        """
        Test `process_catalogue_item_properties` works correctly with a None value given for a mandatory property.
        """
        supplied_properties = [
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value=None),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)

        assert (
            str(exc.value) == f"Mandatory catalogue item property with ID '{supplied_properties[2].id}' cannot be None."
        )

    def test_process_catalogue_item_properties_with_invalid_allowed_value_list_number(self):
        """
        Test `process_catalogue_item_properties` works correctly when given an invalid value for a number catalogue
        item property with a specific list of allowed values
        """
        supplied_properties = [
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=10),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value for catalogue item property with ID '{supplied_properties[3].id}'. "
            "Expected one of 2, 4, 6."
        )

    def test_process_catalogue_item_properties_with_invalid_allowed_value_list_string(self):
        """
        Test `process_catalogue_item_properties` works correctly when given an invalid value for a string catalogue
        item property with a specific list of allowed values
        """
        supplied_properties = [
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=4),
            PropertyPostRequestSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="invalid"),
        ]

        with pytest.raises(InvalidCatalogueItemPropertyTypeError) as exc:
            utils.process_catalogue_item_properties(DEFINED_PROPERTIES, supplied_properties)
        assert (
            str(exc.value) == f"Invalid value for catalogue item property with ID '{supplied_properties[4].id}'. "
            "Expected one of red, green."
        )
