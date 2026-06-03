"""
Unit tests for the `utils` in /services.
"""

from typing import Any

import pytest
from bson import ObjectId
from pydantic import TypeAdapter, ValidationError
from pydantic_core import InitErrorDetails

from inventory_management_system_api.core.exceptions import (
    DuplicateCatalogueCategoryPropertyNameError,
    InvalidPropertyTypeError,
    MissingMandatoryProperty,
)
from inventory_management_system_api.models.catalogue_category import AllowedValues, CatalogueCategoryPropertyOut
from inventory_management_system_api.schemas.catalogue_item import PropertyPostSchema
from inventory_management_system_api.schemas.validation import ValidationErrorSchema
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
        # pylint: disable-next=unexpected-keyword-arg,no-value-for-parameter
        allowed_values=AllowedValues(type="list", values=[2, 4, 6]),
    ),
    CatalogueCategoryPropertyOut(
        id=str(ObjectId()),
        name="Property E",
        type="string",
        mandatory=False,
        # pylint: disable-next=unexpected-keyword-arg,no-value-for-parameter
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
        assert str(exc.value) == f"Missing mandatory property with ID '{SUPPLIED_PROPERTIES[1].id}'"

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


class TestValidateProperties:
    """
    Tests for the `validate_properties` method.
    """

    def assert_errors_equal(self, actual_errors: list[InitErrorDetails], expected_errors: list[dict[str, Any]]) -> None:
        """
        Asserts whether two lists of errors are equal.

        :param actual_errors: Actual errors as would be returned from a validation function.
        :param expected_errors: List of expected errors written as dictionaries.
        """
        type_adapter = TypeAdapter(list[ValidationErrorSchema])
        converted_errors = type_adapter.validate_python(
            ValidationError.from_exception_data(
                title="Errors",
                line_errors=actual_errors,
            ).errors()
        )
        converted_errors = [converted_error.model_dump() for converted_error in converted_errors]
        assert converted_errors == expected_errors

    def test_validate_properties(self):
        """
        Test `validate_properties` works correctly.
        """
        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES, errors)
        self.assert_errors_equal(errors, [])

    def test_validate_properties_with_missing_mandatory_properties(self):
        """
        Test `validate_properties` works correctly with missing mandatory properties.
        """
        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, [SUPPLIED_PROPERTIES[0]], errors)

        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "missing_mandatory_property",
                    "message": f"Missing mandatory property with ID '{property.id}'",
                    "location": [
                        "properties",
                    ],
                    "input": utils._create_properties_dict([SUPPLIED_PROPERTIES[0]]),  # pylint:disable=protected-access
                }
                for property in SUPPLIED_PROPERTIES[1:4]
            ],
        )

    def test_validate_properties_with_missing_non_mandatory_properties(self):
        """
        Test `validate_properties` works correctly with missing non-mandatory properties.
        """
        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, SUPPLIED_PROPERTIES[1:4], errors)
        self.assert_errors_equal(errors, [])

    def test_validate_properties_with_undefined_properties(self):
        """
        Test `validate_properties` works correctly with supplied properties that have not been defined.
        """
        supplied_properties = SUPPLIED_PROPERTIES + [PropertyPostSchema(id=str(ObjectId()), name="Property F", value=1)]
        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)
        self.assert_errors_equal(errors, [])

    def test_validate_properties_with_none_non_mandatory_properties(self):
        """
        Test `validate_properties` works correctly when explicitly giving a value of None
        for non-mandatory properties.
        """
        errors = []
        utils.validate_properties(
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
            errors,
        )
        self.assert_errors_equal(errors, [])

    def test_validate_properties_with_supplied_properties_and_no_defined_properties(self):
        """
        Test `validate_properties` works correctly with supplied properties but no defined properties.
        """
        errors = []
        utils.validate_properties([], SUPPLIED_PROPERTIES, errors)
        self.assert_errors_equal(errors, [])

    def test_validate_properties_without_properties(self):
        """
        Test `validate_properties` works correctly without defined and supplied properties.
        """
        errors = []
        utils.validate_properties([], [], errors)
        self.assert_errors_equal(errors, [])

    def test_validate_properties_with_invalid_value_type_for_string_property(self):
        """
        Test `validate_properties` works correctly with invalid value type for a string catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value=True),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)
        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "invalid_property_type",
                    "message": f"Invalid value type for property with ID '{DEFINED_PROPERTIES[2].id}'. "
                    "Expected type: string.",
                    "location": [
                        "properties",
                        2,
                        "value",
                    ],
                    "input": True,
                },
            ],
        )

    def test_validate_properties_with_invalid_value_type_for_number_property(self):
        """
        Test `validate_properties` works correctly with invalid value type for a number catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value="20"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)
        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "invalid_property_type",
                    "message": f"Invalid value type for property with ID '{DEFINED_PROPERTIES[0].id}'. "
                    "Expected type: number.",
                    "location": [
                        "properties",
                        0,
                        "value",
                    ],
                    "input": "20",
                },
            ],
        )

    def test_validate_properties_with_invalid_value_type_for_boolean_property(self):
        """
        Test `validate_properties` works correctly with invalid value type for a boolean catalogue item
        property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value="False"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)
        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "invalid_property_type",
                    "message": f"Invalid value type for property with ID '{DEFINED_PROPERTIES[1].id}'. "
                    "Expected type: boolean.",
                    "location": [
                        "properties",
                        1,
                        "value",
                    ],
                    "input": "False",
                },
            ],
        )

    def test_validate_properties_with_invalid_value_type_for_mandatory_property(self):
        """
        Test `validate_properties` works correctly with a None value given for a mandatory property.
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value=None),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=2),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)

        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "invalid_property_type",
                    "message": f"Mandatory property with ID '{DEFINED_PROPERTIES[2].id}' cannot be None.",
                    "location": [
                        "properties",
                        2,
                        "value",
                    ],
                    "input": None,
                },
            ],
        )

    def test_validate_properties_with_invalid_allowed_value_list_number(self):
        """
        Test `validate_properties` works correctly when given an invalid value for a number property with a specific
        list of allowed values
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=10),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="red"),
        ]

        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)
        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "invalid_property_type",
                    "message": f"Invalid value for property with ID '{DEFINED_PROPERTIES[3].id}'. "
                    "Expected one of 2, 4, 6.",
                    "location": [
                        "properties",
                        3,
                        "value",
                    ],
                    "input": 10,
                },
            ],
        )

    def test_validate_properties_with_invalid_allowed_value_list_string(self):
        """
        Test `validate_properties` works correctly when given an invalid value for a string property with a specific
        list of allowed values
        """
        supplied_properties = [
            PropertyPostSchema(id=DEFINED_PROPERTIES[0].id, name="Property A", value=20),
            PropertyPostSchema(id=DEFINED_PROPERTIES[1].id, name="Property B", value=False),
            PropertyPostSchema(id=DEFINED_PROPERTIES[2].id, name="Property C", value="20x15x10"),
            PropertyPostSchema(id=DEFINED_PROPERTIES[3].id, name="Property D", value=4),
            PropertyPostSchema(id=DEFINED_PROPERTIES[4].id, name="Property E", value="invalid"),
        ]

        errors = []
        utils.validate_properties(DEFINED_PROPERTIES, supplied_properties, errors)
        self.assert_errors_equal(
            errors,
            [
                {
                    "type": "invalid_property_type",
                    "message": f"Invalid value for property with ID '{DEFINED_PROPERTIES[4].id}'. "
                    "Expected one of red, green.",
                    "location": [
                        "properties",
                        4,
                        "value",
                    ],
                    "input": "invalid",
                },
            ],
        )
