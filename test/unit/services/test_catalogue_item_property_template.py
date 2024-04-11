"""
Unit tests for the `CatalogueItemPropertyTemplateService` service
"""


def test_list(catalogue_item_property_template_repository_mock, catalogue_item_property_template_service):
    """
    Test listing catalogue item property templates
    Verify that the `list` method properly calls the repository function
    """
    result = catalogue_item_property_template_service.list()

    catalogue_item_property_template_repository_mock.list.assert_called_once_with()
    assert result == catalogue_item_property_template_repository_mock.list.return_value
