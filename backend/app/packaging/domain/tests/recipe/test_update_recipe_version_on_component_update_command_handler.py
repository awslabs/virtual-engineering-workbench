import pytest
from assertpy import assertpy

from app.packaging.domain.command_handlers.recipe import update_recipe_version_on_component_update_command_handler
from app.packaging.domain.events.recipe import recipe_version_update_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_project_association, component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.tests.conftest import TEST_PROJECT_ID


def test_handle_should_update_recipe_on_component_update(
    get_recipe_version_with_rc_component,
    recipe_version_query_service_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    uow_mock,
    message_bus_mock,
    get_test_component_version_with_specific_version_name_and_status_with_recipe,
    update_recipe_version_on_component_update_command_mock,
    generic_repo_mock,
):
    # ARRANGE
    recipe_version_entity = get_recipe_version_with_rc_component(
        component_version_name="1.0.0-rc2",
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    expected_version_name = "1.0.0-rc3"
    component_version_entity = get_test_component_version_with_specific_version_name_and_status_with_recipe(
        version_name=expected_version_name, status=component_version.ComponentVersionStatus.Validated
    )
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    component_query_service_mock.get_component_project_associations.return_value = [
        component_project_association.ComponentProjectAssociation(
            componentId=component_version_entity.componentId, projectId=TEST_PROJECT_ID
        )
    ]

    update_recipe_version_on_component_update_command_handler.handle(
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        component_qry_srv=component_query_service_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        command=update_recipe_version_on_component_update_command_mock,
    )

    uow_mock.commit.assert_called()
    final_recipe = get_recipe_version_with_rc_component(
        component_id=component_version_entity.componentId,
        component_version_id=component_version_entity.componentVersionId,
        component_version_name=expected_version_name,
    )
    generic_repo_mock.update_entity.assert_called_once_with(
        recipe_version.RecipeVersionPrimaryKey(
            recipeId=final_recipe.recipeId,
            recipeVersionId=final_recipe.recipeVersionId,
        ),
        final_recipe,
    )
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_update_started.RecipeVersionUpdateStarted(
            projectId=TEST_PROJECT_ID,
            recipe_id=recipe_version_entity.recipeId,
            recipe_version_id=recipe_version_entity.recipeVersionId,
            recipe_components_versions=recipe_version_entity.recipeComponentsVersions,
            recipe_version_description=recipe_version_entity.recipeVersionDescription,
            recipe_version_volume_size=recipe_version_entity.recipeVersionVolumeSize,
            last_updated_by=component_version_entity.lastUpdatedBy,
            parent_image_upstream_id=recipe_version_entity.parentImageUpstreamId,
            recipe_version_name=recipe_version_entity.recipeVersionName,
            previous_recipe_components_versions=recipe_version_entity.recipeComponentsVersions,
        )
    )


def test_handle_should_skip_update_recipe_when_empty_component_associatedRecipesVersions(
    get_recipe_version_with_rc_component,
    recipe_version_query_service_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    uow_mock,
    message_bus_mock,
    get_test_component_version_with_specific_version_name_and_status_with_recipe,
    update_recipe_version_on_component_update_command_mock,
    generic_repo_mock,
):
    # ARRANGE
    recipe_version_entity = get_recipe_version_with_rc_component(
        component_version_name="1.0.0-rc2",
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    expected_version_name = "1.0.0-rc3"
    component_version_entity = get_test_component_version_with_specific_version_name_and_status_with_recipe(
        version_name=expected_version_name, status=component_version.ComponentVersionStatus.Validated
    )
    component_version_entity.associatedRecipesVersions = None
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    component_query_service_mock.get_component_project_associations.return_value = [
        component_project_association.ComponentProjectAssociation(
            componentId=component_version_entity.componentId, projectId=TEST_PROJECT_ID
        )
    ]

    update_recipe_version_on_component_update_command_handler.handle(
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        component_qry_srv=component_query_service_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        command=update_recipe_version_on_component_update_command_mock,
    )

    uow_mock.commit.assert_not_called()


def test_handle_should_skip_update_recipe_when_empty_recipe_recipeComponentsVersions(
    get_recipe_version_with_rc_component,
    recipe_version_query_service_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    uow_mock,
    message_bus_mock,
    get_test_component_version_with_specific_version_name_and_status_with_recipe,
    update_recipe_version_on_component_update_command_mock,
    generic_repo_mock,
):
    # ARRANGE
    recipe_version_entity = get_recipe_version_with_rc_component(
        component_version_name="1.0.0-rc2",
    )
    recipe_version_entity.recipeComponentsVersions = None
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity
    expected_version_name = "1.0.0-rc3"
    component_version_entity = get_test_component_version_with_specific_version_name_and_status_with_recipe(
        version_name=expected_version_name, status=component_version.ComponentVersionStatus.Validated
    )
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    component_query_service_mock.get_component_project_associations.return_value = [
        component_project_association.ComponentProjectAssociation(
            componentId=component_version_entity.componentId, projectId=TEST_PROJECT_ID
        )
    ]

    update_recipe_version_on_component_update_command_handler.handle(
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        component_qry_srv=component_query_service_mock,
        recipe_version_query_service=recipe_version_query_service_mock,
        command=update_recipe_version_on_component_update_command_mock,
    )

    uow_mock.commit.assert_not_called()


def test_handle_should_raise_exception_when_no_component_version_entity_is_returned(
    get_recipe_version_with_rc_component,
    recipe_version_query_service_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    uow_mock,
    message_bus_mock,
    get_test_component_version_with_specific_version_name_and_status_with_recipe,
    update_recipe_version_on_component_update_command_mock,
    generic_repo_mock,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = None
    with pytest.raises(domain_exception.DomainException) as exc_info:
        update_recipe_version_on_component_update_command_handler.handle(
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            component_qry_srv=component_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            command=update_recipe_version_on_component_update_command_mock,
        )
    # Assert
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {update_recipe_version_on_component_update_command_mock.componentVersionId} of component {update_recipe_version_on_component_update_command_mock.componentId} does not exist."
    )


def test_handle_should_raise_exception_when_no_recipe_version_entity_is_returned(
    get_recipe_version_with_rc_component,
    recipe_version_query_service_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    uow_mock,
    message_bus_mock,
    get_test_component_version_with_specific_version_name_and_status_with_recipe,
    update_recipe_version_on_component_update_command_mock,
    generic_repo_mock,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = None
    expected_version_name = "1.0.0-rc3"
    component_version_entity = get_test_component_version_with_specific_version_name_and_status_with_recipe(
        version_name=expected_version_name, status=component_version.ComponentVersionStatus.Validated
    )
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    component_query_service_mock.get_component_project_associations.return_value = [
        component_project_association.ComponentProjectAssociation(
            componentId=component_version_entity.componentId, projectId=TEST_PROJECT_ID
        )
    ]
    with pytest.raises(domain_exception.DomainException) as exc_info:
        update_recipe_version_on_component_update_command_handler.handle(
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            component_qry_srv=component_query_service_mock,
            recipe_version_query_service=recipe_version_query_service_mock,
            command=update_recipe_version_on_component_update_command_mock,
        )
    # Assert
    assertpy.assert_that(str(exc_info.value)).is_equal_to(
        f"Version {component_version_entity.associatedRecipesVersions[0].recipeVersionId} of recipe {component_version_entity.associatedRecipesVersions[0].recipeId} does not exist."
    )
