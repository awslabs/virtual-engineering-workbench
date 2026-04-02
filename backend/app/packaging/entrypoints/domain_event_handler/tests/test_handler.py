import pytest

from app.packaging.domain.commands.component import (
    deploy_component_version_command,
    remove_component_version_command,
    update_component_version_associations_command,
)
from app.packaging.domain.commands.pipeline import (
    deploy_pipeline_command,
    remove_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    deploy_recipe_version_command,
    remove_recipe_version_command,
    update_recipe_version_associations_command,
)
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.value_objects.component import (
    component_build_version_arn_value_object,
    component_id_value_object,
)
from app.packaging.domain.value_objects.component_version import (
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_name_value_object,
    component_version_yaml_definition_value_object,
    components_versions_list_value_object,
)
from app.packaging.domain.value_objects.pipeline import (
    pipeline_arn_value_object,
    pipeline_distribution_config_arn_value_object,
    pipeline_id_value_object,
    pipeline_infrastructure_config_arn_value_object,
)
from app.packaging.domain.value_objects.recipe import (
    recipe_id_value_object,
    recipe_name_value_object,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_arn_value_object,
    recipe_version_components_versions_value_object,
    recipe_version_id_value_object,
    recipe_version_name_value_object,
    recipe_version_parent_image_upstream_id_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
)


def test_handler_component_version_creation_started_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    component_version_creation_started_event_payload,
    mock_deploy_component_version_command_handler,
    mock_update_component_version_associations_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ComponentVersionCreationStarted",
        detail=component_version_creation_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_deploy_component_version_command_handler.assert_called_once_with(
        deploy_component_version_command.DeployComponentVersionCommand(
            componentId=component_id_value_object.from_str(
                component_version_creation_started_event_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_creation_started_event_payload.get("componentVersionId")
            ),
            componentVersionName=component_version_name_value_object.from_str(
                component_version_creation_started_event_payload.get("componentVersionName")
            ),
            componentVersionDescription=component_version_description_value_object.from_str(
                component_version_creation_started_event_payload.get("componentVersionDescription")
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                component_version_creation_started_event_payload.get("componentVersionYamlDefinition")
            ),
        )
    )
    mock_update_component_version_associations_command_handler.assert_called_once_with(
        update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
            componentId=component_id_value_object.from_str(
                component_version_creation_started_event_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_creation_started_event_payload.get("componentVersionId")
            ),
            componentsVersionDependencies=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(dependency)
                    for dependency in component_version_creation_started_event_payload.get(
                        "componentVersionDependencies"
                    )
                ]
            ),
        )
    )


def test_handler_component_update_creation_started_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    component_version_update_started_event_payload,
    mock_deploy_component_version_command_handler,
    mock_update_component_version_associations_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ComponentVersionUpdateStarted",
        detail=component_version_update_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_deploy_component_version_command_handler.assert_called_once_with(
        deploy_component_version_command.DeployComponentVersionCommand(
            componentId=component_id_value_object.from_str(
                component_version_update_started_event_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_update_started_event_payload.get("componentVersionId")
            ),
            componentVersionName=component_version_name_value_object.from_str(
                component_version_update_started_event_payload.get("componentVersionName")
            ),
            componentVersionDescription=component_version_description_value_object.from_str(
                component_version_update_started_event_payload.get("componentVersionDescription")
            ),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                component_version_update_started_event_payload.get("componentVersionYamlDefinition")
            ),
        )
    )
    mock_update_component_version_associations_command_handler.assert_called_once_with(
        update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
            componentId=component_id_value_object.from_str(
                component_version_update_started_event_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_update_started_event_payload.get("componentVersionId")
            ),
            componentsVersionDependencies=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(dependency)
                    for dependency in component_version_update_started_event_payload.get("componentVersionDependencies")
                ]
            ),
            previousComponentsVersionDependencies=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(dependency)
                    for dependency in component_version_update_started_event_payload.get(
                        "previousComponentVersionDependencies"
                    )
                ]
            ),
        )
    )


def test_handler_recipe_version_retirement_started_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    recipe_version_retirement_started_payload,
    mock_remove_recipe_version_command_handler,
    mock_update_recipe_version_associations_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="RecipeVersionRetirementStarted",
        detail=recipe_version_retirement_started_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_remove_recipe_version_command_handler.assert_called_once_with(
        remove_recipe_version_command.RemoveRecipeVersionCommand(
            projectId=project_id_value_object.from_str(recipe_version_retirement_started_payload.get("projectId")),
            recipeId=recipe_id_value_object.from_str(recipe_version_retirement_started_payload.get("recipeId")),
            recipeName=recipe_name_value_object.from_str(recipe_version_retirement_started_payload.get("recipeName")),
            recipeVersionId=recipe_version_id_value_object.from_str(
                recipe_version_retirement_started_payload.get("recipeVersionId")
            ),
            recipeVersionArn=recipe_version_arn_value_object.from_str(
                recipe_version_retirement_started_payload.get("recipeVersionArn")
            ),
            recipeVersionComponentArn=component_build_version_arn_value_object.from_str(
                recipe_version_retirement_started_payload.get("recipeVersionComponentArn")
            ),
            recipeVersionName=recipe_version_name_value_object.from_str(
                recipe_version_retirement_started_payload.get("recipeVersionName")
            ),
            lastUpdatedBy=user_id_value_object.from_str(recipe_version_retirement_started_payload.get("lastUpdatedBy")),
        )
    )

    mock_update_recipe_version_associations_command_handler.assert_called_once_with(
        update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand(
            recipeId=recipe_id_value_object.from_str(recipe_version_retirement_started_payload.get("recipeId")),
            recipeVersionId=recipe_version_id_value_object.from_str(
                recipe_version_retirement_started_payload.get("recipeVersionId")
            ),
            componentsVersionsList=components_versions_list_value_object.from_list(list()),
            previousComponentsVersionsList=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(recipe_component_version)
                    for recipe_component_version in recipe_version_retirement_started_payload.get(
                        "recipeComponentsVersions"
                    )
                ]
            ),
        )
    )


def test_handler_component_version_retirement_started_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    component_version_retirement_started_payload,
    mock_remove_component_version_command_handler,
    mock_update_component_version_associations_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ComponentVersionRetirementStarted",
        detail=component_version_retirement_started_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_remove_component_version_command_handler.assert_called_once_with(
        remove_component_version_command.RemoveComponentVersionCommand(
            componentId=component_id_value_object.from_str(
                component_version_retirement_started_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_retirement_started_payload.get("componentVersionId")
            ),
            componentBuildVersionArn=component_build_version_arn_value_object.from_str(
                component_version_retirement_started_payload.get("componentBuildVersionArn")
            ),
        )
    )
    mock_update_component_version_associations_command_handler.assert_called_once_with(
        update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
            componentId=component_id_value_object.from_str(
                component_version_retirement_started_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_retirement_started_payload.get("componentVersionId")
            ),
            componentsVersionDependencies=components_versions_list_value_object.from_list(list()),
            previousComponentsVersionDependencies=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(dependency)
                    for dependency in component_version_retirement_started_payload.get("componentVersionDependencies")
                ]
            ),
        )
    )


def test_handler_component_release_completed_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    component_version_release_completed_event_payload,
    mock_update_component_version_associations_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="ComponentVersionReleaseCompleted",
        detail=component_version_release_completed_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_component_version_associations_command_handler.assert_called_once_with(
        update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
            componentId=component_id_value_object.from_str(
                component_version_release_completed_event_payload.get("componentId")
            ),
            componentVersionId=component_version_id_value_object.from_str(
                component_version_release_completed_event_payload.get("componentVersionId")
            ),
            componentsVersionDependencies=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(dependency)
                    for dependency in component_version_release_completed_event_payload.get(
                        "componentVersionDependencies"
                    )
                ]
            ),
        )
    )


def test_handler_recipe_version_creation_started_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    recipe_version_creation_started_event_payload,
    mock_deploy_recipe_version_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="RecipeVersionCreationStarted",
        detail=recipe_version_creation_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_deploy_recipe_version_command_handler.assert_called_once_with(
        deploy_recipe_version_command.DeployRecipeVersionCommand(
            projectId=project_id_value_object.from_str(recipe_version_creation_started_event_payload.get("projectId")),
            recipeId=recipe_id_value_object.from_str(recipe_version_creation_started_event_payload.get("recipeId")),
            recipeVersionId=recipe_version_id_value_object.from_str(
                recipe_version_creation_started_event_payload.get("recipeVersionId")
            ),
            recipeVersionName=recipe_version_name_value_object.from_str(
                recipe_version_creation_started_event_payload.get("recipeVersionName")
            ),
            components=recipe_version_components_versions_value_object.from_list(
                [
                    ComponentVersionEntry(**item)
                    for item in recipe_version_creation_started_event_payload.get("recipeComponentsVersions")
                ]
            ),
            parentImageUpstreamId=recipe_version_parent_image_upstream_id_value_object.from_str(
                recipe_version_creation_started_event_payload.get("parentImageUpstreamId")
            ),
            recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(
                recipe_version_creation_started_event_payload.get("recipeVersionVolumeSize")
            ),
        )
    )


def test_handler_recipe_version_update_started_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    recipe_version_update_started_event_payload,
    mock_deploy_recipe_version_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="RecipeVersionUpdateStarted",
        detail=recipe_version_update_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_deploy_recipe_version_command_handler.assert_called_once_with(
        deploy_recipe_version_command.DeployRecipeVersionCommand(
            projectId=project_id_value_object.from_str(recipe_version_update_started_event_payload.get("projectId")),
            recipeId=recipe_id_value_object.from_str(recipe_version_update_started_event_payload.get("recipeId")),
            recipeVersionId=recipe_version_id_value_object.from_str(
                recipe_version_update_started_event_payload.get("recipeVersionId")
            ),
            recipeVersionName=recipe_version_name_value_object.from_str(
                recipe_version_update_started_event_payload.get("recipeVersionName")
            ),
            components=recipe_version_components_versions_value_object.from_list(
                [
                    ComponentVersionEntry(**item)
                    for item in recipe_version_update_started_event_payload.get("recipeComponentsVersions")
                ]
            ),
            parentImageUpstreamId=recipe_version_parent_image_upstream_id_value_object.from_str(
                recipe_version_update_started_event_payload.get("parentImageUpstreamId")
            ),
            recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(
                recipe_version_update_started_event_payload.get("recipeVersionVolumeSize")
            ),
        )
    )


def test_handler_recipe_version_release_completed_event(
    mock_dependencies,
    generate_event,
    lambda_context,
    recipe_version_release_completed_event_payload,
    mock_update_recipe_version_associations_command_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="RecipeVersionReleaseCompleted",
        detail=recipe_version_release_completed_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_recipe_version_associations_command_handler.assert_called_once_with(
        update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand(
            recipeId=recipe_id_value_object.from_str(recipe_version_release_completed_event_payload.get("recipeId")),
            recipeVersionId=recipe_version_id_value_object.from_str(
                recipe_version_release_completed_event_payload.get("recipeVersionId")
            ),
            componentsVersionsList=components_versions_list_value_object.from_list(
                [
                    component_version_entry.ComponentVersionEntry.model_validate(component_version)
                    for component_version in recipe_version_release_completed_event_payload.get(
                        "recipeComponentsVersions"
                    )
                ]
            ),
        )
    )


def test_handler_pipeline_creation_started_started_event(
    generate_event,
    lambda_context,
    mock_dependencies,
    mock_deploy_pipeline_command_handler,
    pipeline_creation_started_event_payload,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="PipelineCreationStarted",
        detail=pipeline_creation_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_deploy_pipeline_command_handler.assert_called_once_with(
        deploy_pipeline_command.DeployPipelineCommand(
            projectId=project_id_value_object.from_str(pipeline_creation_started_event_payload.get("projectId")),
            pipelineId=pipeline_id_value_object.from_str(pipeline_creation_started_event_payload.get("pipelineId")),
        )
    )


@pytest.mark.parametrize(
    "distribution_config_arn,infrastructure_config_arn,pipeline_arn",
    (
        (
            None,
            None,
            None,
        ),
        (
            "arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/pipe-12345abc",
            None,
            None,
        ),
        (
            "arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/pipe-12345abc",
            "arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/pipe-12345abc",
            None,
        ),
        (
            "arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/pipe-12345abc",
            "arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/pipe-12345abc",
            "arn:aws:imagebuilder:us-east-1:123456789012:image-pipeline/pipe-12345abc",
        ),
    ),
)
def test_handler_pipeline_retirement_started_started_event(
    distribution_config_arn,
    generate_event,
    get_pipeline_retirement_started_event_payload,
    infrastructure_config_arn,
    lambda_context,
    mock_dependencies,
    mock_remove_pipeline_command_handler,
    pipeline_arn,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    pipeline_retirement_started_event_payload = get_pipeline_retirement_started_event_payload(
        distribution_config_arn=distribution_config_arn,
        infrastructure_config_arn=infrastructure_config_arn,
        pipeline_arn=pipeline_arn,
    )
    event_bridge_event = generate_event(
        detail_type="PipelineRetirementStarted",
        detail=pipeline_retirement_started_event_payload,
    )
    remove_pipeline_command_kwargs = {
        "projectId": project_id_value_object.from_str(pipeline_retirement_started_event_payload.get("projectId")),
        "pipelineId": pipeline_id_value_object.from_str(pipeline_retirement_started_event_payload.get("pipelineId")),
    }
    if distribution_config_arn:
        remove_pipeline_command_kwargs["distributionConfigArn"] = (
            pipeline_distribution_config_arn_value_object.from_str(
                pipeline_retirement_started_event_payload.get("distributionConfigArn")
            )
        )
    if infrastructure_config_arn:
        remove_pipeline_command_kwargs["infrastructureConfigArn"] = (
            pipeline_infrastructure_config_arn_value_object.from_str(
                pipeline_retirement_started_event_payload.get("infrastructureConfigArn")
            )
        )
    if pipeline_arn:
        remove_pipeline_command_kwargs["pipelineArn"] = pipeline_arn_value_object.from_str(
            pipeline_retirement_started_event_payload.get("pipelineArn")
        )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_remove_pipeline_command_handler.assert_called_once_with(
        remove_pipeline_command.RemovePipelineCommand(**remove_pipeline_command_kwargs)
    )


def test_handler_pipeline_update_started_started_event(
    generate_event,
    lambda_context,
    mock_dependencies,
    mock_deploy_pipeline_command_handler,
    pipeline_update_started_event_payload,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="PipelineUpdateStarted",
        detail=pipeline_update_started_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_deploy_pipeline_command_handler.assert_called_once_with(
        deploy_pipeline_command.DeployPipelineCommand(
            projectId=project_id_value_object.from_str(pipeline_update_started_event_payload.get("projectId")),
            pipelineId=pipeline_id_value_object.from_str(pipeline_update_started_event_payload.get("pipelineId")),
        )
    )


def test_handler_update_recipe_version_on_component_update_event(
    generate_event,
    lambda_context,
    mock_dependencies,
    mock_update_recipe_on_component_update_command_handler,
    recipe_version_update_on_component_update_requested_event_payload,
):
    # ARRANGE
    from app.packaging.entrypoints.domain_event_handler import handler

    handler.dependencies = mock_dependencies
    event_bridge_event = generate_event(
        detail_type="RecipeVersionUpdateOnComponentUpdateRequested",
        detail=recipe_version_update_on_component_update_requested_event_payload,
    )

    # ACT
    handler.handler(event_bridge_event, lambda_context)

    # ASSERT
    mock_update_recipe_on_component_update_command_handler.assert_called_once
