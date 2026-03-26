from app.packaging.domain.commands.image import register_automated_image_command
from app.packaging.domain.events.image import automated_image_registration_completed
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_detail
from app.packaging.domain.ports import (
    component_version_query_service,
    pipeline_query_service,
    recipe_query_service,
    recipe_version_query_service,
)
from app.shared.adapters.message_bus import message_bus


def handle(
    command: register_automated_image_command.RegisterAutomatedImageCommand,
    message_bus: message_bus.MessageBus,
    pipeline_qry_srv: pipeline_query_service.PipelineQueryService,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    pipeline_entity = pipeline_qry_srv.get_pipeline_by_pipeline_id(pipeline_id=command.pipelineId.value)
    if not pipeline_entity:
        raise domain_exception.DomainException(f"Pipeline {command.pipelineId.value} not found.")

    recipe_entity = recipe_qry_srv.get_recipe(project_id=pipeline_entity.projectId, recipe_id=pipeline_entity.recipeId)
    if not recipe_entity:
        raise domain_exception.DomainException(f"Recipe {pipeline_entity.recipeId} not found.")

    recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
        recipe_id=pipeline_entity.recipeId, version_id=pipeline_entity.recipeVersionId
    )
    if not recipe_version_entity:
        raise domain_exception.DomainException(
            f"Recipe version {pipeline_entity.recipeVersionId} not found for recipe {pipeline_entity.recipeId}."
        )

    components_versions_details = []
    for recipe_component_version in recipe_version_entity.recipeComponentsVersions:
        component_version_entity = component_version_qry_srv.get_component_version(
            component_id=recipe_component_version.componentId,
            version_id=recipe_component_version.componentVersionId,
        )
        if component_version_entity:
            components_versions_details.append(
                component_version_detail.ComponentVersionDetail(
                    componentName=component_version_entity.componentName,
                    componentVersionType=recipe_component_version.componentVersionType,
                    softwareVendor=component_version_entity.softwareVendor,
                    softwareVersion=component_version_entity.softwareVersion,
                    licenseDashboard=component_version_entity.licenseDashboard,
                    notes=component_version_entity.notes,
                )
            )

    message_bus.publish(
        automated_image_registration_completed.AutomatedImageRegistrationCompleted(
            amiId=command.amiId.value,
            productId=command.productId.value,
            projectId=command.projectId.value,
            releaseType=command.productVersionReleaseType.value,
            userId=command.userId.value,
            componentsVersionsDetails=components_versions_details,
            osVersion=recipe_entity.recipeOsVersion,
            platform=recipe_entity.recipePlatform,
            architecture=recipe_entity.recipeArchitecture,
            integrations=recipe_version_entity.recipeVersionIntegrations or [],
        )
    )
