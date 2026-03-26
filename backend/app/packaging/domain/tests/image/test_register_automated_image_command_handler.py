from app.packaging.domain.command_handlers.image import (
    register_automated_image_command_handler,
)
from app.packaging.domain.tests.conftest import (
    TEST_AMI_ID,
    TEST_PRODUCT_ID,
    TEST_PROJECT_ID,
    TEST_USER_ID,
)


def test_handle_should_publish_automated_image_registration_completed_event(
    message_bus_mock,
    register_automated_image_command_mock,
    pipeline_query_service_mock,
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    component_version_query_service_mock,
    get_pipeline_entity,
    mock_recipe_object,
    mock_recipe_version_object,
    get_test_component_version,
):
    # ARRANGE
    pipeline_entity = get_pipeline_entity(product_id=TEST_PRODUCT_ID)
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = pipeline_entity
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    recipe_version_query_service_mock.get_recipe_version.return_value = mock_recipe_version_object
    component_version_query_service_mock.get_component_version.return_value = get_test_component_version

    # ACT
    register_automated_image_command_handler.handle(
        command=register_automated_image_command_mock,
        message_bus=message_bus_mock,
        pipeline_qry_srv=pipeline_query_service_mock,
        recipe_qry_srv=recipe_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    message_bus_mock.publish.assert_called_once()
    published_event = message_bus_mock.publish.call_args[0][0]
    assert published_event.amiId == TEST_AMI_ID
    assert published_event.productId == TEST_PRODUCT_ID
    assert published_event.projectId == TEST_PROJECT_ID
    assert published_event.releaseType == "MINOR"
    assert published_event.userId == TEST_USER_ID
    assert published_event.osVersion == mock_recipe_object.recipeOsVersion
    assert published_event.platform == mock_recipe_object.recipePlatform
    assert published_event.architecture == mock_recipe_object.recipeArchitecture
    assert len(published_event.componentsVersionsDetails) == len(mock_recipe_version_object.recipeComponentsVersions)
