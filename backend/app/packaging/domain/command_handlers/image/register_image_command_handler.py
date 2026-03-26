from datetime import datetime, timezone

from app.packaging.domain.commands.image import register_image_command
from app.packaging.domain.events.image import automated_image_registration_completed, image_registration_completed
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_detail
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import (
    component_version_query_service,
    image_query_service,
    pipeline_query_service,
    recipe_query_service,
    recipe_version_query_service,
)
from app.packaging.domain.read_models import version_release_type
from app.packaging.domain.value_objects.image import image_build_version_value_object
from app.packaging.domain.value_objects.recipe import recipe_id_value_object, recipe_name_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __append_to_components_versions_details(
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    components_versions_details: list[component_version_detail.ComponentVersionDetail],
    recipe_component_version: component_version_entry.ComponentVersionEntry,
):
    component_version_entity = component_version_qry_srv.get_component_version(
        component_id=recipe_component_version.componentId,
        version_id=recipe_component_version.componentVersionId,
    )

    if component_version_entity is None:
        raise domain_exception.DomainException(
            f"Component version {recipe_component_version.componentVersionId} for "
            f"{recipe_component_version.componentId} not found."
        )

    components_versions_details.append(
        component_version_detail.ComponentVersionDetail(
            componentName=component_version_entity.componentName,
            componentVersionType=recipe_component_version.componentVersionType,
            softwareVendor=component_version_entity.softwareVendor,
            softwareVersion=component_version_entity.softwareVersion,
            licenseDashboard=(
                component_version_entity.licenseDashboard if component_version_entity.licenseDashboard else None
            ),
            notes=component_version_entity.notes if component_version_entity.notes else None,
        )
    )


def __retire_previous_images(
    image_entities: list[image.Image],
    uow: unit_of_work.UnitOfWork,
) -> list[str]:
    retired_amis_ids = []
    current_time = datetime.now(timezone.utc).isoformat()

    for retired_image_entity in [img for img in image_entities if img.status == image.ImageStatus.Created]:
        retired_amis_ids.append(retired_image_entity.imageUpstreamId)

        with uow:
            uow.get_repository(image.ImagePrimaryKey, image.Image).update_attributes(
                image.ImagePrimaryKey(projectId=retired_image_entity.projectId, imageId=retired_image_entity.imageId),
                status=image.ImageStatus.Retired,
                lastUpdateDate=current_time,
            )
            uow.commit()

    return retired_amis_ids


def __build_components_versions_details(
    recipe_version_entity: recipe_version.RecipeVersion,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
) -> list[component_version_detail.ComponentVersionDetail]:
    components_versions_details = []
    for recipe_component_version in recipe_version_entity.recipeComponentsVersions:
        __append_to_components_versions_details(
            component_version_qry_srv=component_version_qry_srv,
            components_versions_details=components_versions_details,
            recipe_component_version=recipe_component_version,
        )
    return components_versions_details


def __check_recipe_version_entity(image_entity: image.Image, recipe_version_entity: recipe_version.RecipeVersion):
    if recipe_version_entity is None:
        raise domain_exception.DomainException(
            f"No recipe version {image_entity.recipeId} found for {image_entity.recipeVersionId}."
        )


def handle(
    command: register_image_command.RegisterImageCommand,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    image_qry_srv: image_query_service.ImageQueryService,
    message_bus: message_bus.MessageBus,
    pipeline_qry_srv: pipeline_query_service.PipelineQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    uow: unit_of_work.UnitOfWork,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
):
    # Example ARN: arn:aws:imagebuilder:us-east-1:123456789012:image/my-recipe/1.0.0/1
    # Splitting based on character "/" will return my-recipe, 1.0.0 and 1 respectively
    image_build_version = image_build_version_value_object.from_int(
        int(command.imageBuildVersionArn.value.split("/")[3])
    ).value
    recipe_id = recipe_id_value_object.from_str(command.imageBuildVersionArn.value.split("/")[1]).value
    recipe_version_name = recipe_name_value_object.from_str(command.imageBuildVersionArn.value.split("/")[2]).value

    pipeline_entity = __get_pipeline(command, pipeline_qry_srv)
    recipe_entity = __get_recipe(recipe_qry_srv, pipeline_entity)
    image_entity = image_qry_srv.get_image_by_image_build_version_arn(
        image_build_version_arn=command.imageBuildVersionArn.value
    )
    # If the image is not in the database yet this is a
    # scheduled build, and we need to add it as CREATING
    if not image_entity:
        image_entity = __create_image(command, uow, image_build_version, pipeline_entity, recipe_version_name)

    image_entities = sorted(
        image_qry_srv.get_images_by_recipe_id_and_version_name(
            recipe_id=recipe_id, recipe_version_name=recipe_version_name
        ),
        key=lambda image_entity: image_entity.imageBuildVersion,
        reverse=True,
    )
    latest_image_build_version = image_entities[0].imageBuildVersion

    # We start by assuming the status of the image to register is FAILED
    status = image.ImageStatus.Failed
    if command.imageStatus.value != image.ImageStatus.Failed:
        # If we receive a CREATED from the command and this is the last image
        # to have been built then its status is CREATED, otherwise is RETIRED
        status = (
            image.ImageStatus.Created
            if image_build_version == latest_image_build_version
            else image.ImageStatus.Retired
        )
    # If this is the last image to have been built
    # all previously CREATED images are now RETIRED
    if status == image.ImageStatus.Created:
        retired_amis_ids = __retire_previous_images(image_entities, uow)

        recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
            recipe_id=image_entity.recipeId, version_id=image_entity.recipeVersionId
        )

        __check_recipe_version_entity(image_entity=image_entity, recipe_version_entity=recipe_version_entity)
        components_versions_details = __build_components_versions_details(
            recipe_version_entity, component_version_qry_srv
        )

    current_time = datetime.now(timezone.utc).isoformat()

    # Finally we update the image entity
    with uow:
        update_attrs = {"status": status, "lastUpdateDate": current_time}
        if command.imageUpstreamId:
            update_attrs["imageUpstreamId"] = command.imageUpstreamId.value
        uow.get_repository(image.ImagePrimaryKey, image.Image).update_attributes(
            image.ImagePrimaryKey(projectId=image_entity.projectId, imageId=image_entity.imageId), **update_attrs
        )
        uow.commit()

    # And eventually publish an event to the domain event bus
    if status == image.ImageStatus.Created:
        message_bus.publish(
            image_registration_completed.ImageRegistrationCompleted(
                projectId=image_entity.projectId,
                amiDescription=recipe_version_entity.recipeName,
                amiId=command.imageUpstreamId.value,
                amiName=f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}",
                componentsVersionsDetails=components_versions_details,
                retiredAmiIds=retired_amis_ids,
                osVersion=recipe_entity.recipeOsVersion,
                platform=recipe_entity.recipePlatform,
                architecture=recipe_entity.recipeArchitecture,
                createDate=current_time,
                integrations=recipe_version_entity.recipeVersionIntegrations or [],
            )
        )

        automated_event_kwargs = {
            "amiId": command.imageUpstreamId.value,
            "projectId": image_entity.projectId,
            "releaseType": version_release_type.VersionReleaseType.Patch.value,
            "userId": "SYSTEM",
            "componentsVersionsDetails": components_versions_details,
            "osVersion": recipe_entity.recipeOsVersion,
            "platform": recipe_entity.recipePlatform,
            "architecture": recipe_entity.recipeArchitecture,
            "integrations": recipe_version_entity.recipeVersionIntegrations or [],
        }
        if pipeline_entity.productId:
            automated_event_kwargs["productId"] = pipeline_entity.productId

        message_bus.publish(
            automated_image_registration_completed.AutomatedImageRegistrationCompleted(**automated_event_kwargs)
        )


def __get_pipeline(
    command: register_image_command.RegisterImageCommand, pipeline_qry_srv: pipeline_query_service.PipelineQueryService
):
    pipeline_entity = pipeline_qry_srv.get_pipeline_by_pipeline_id(pipeline_id=command.pipelineId.value)
    if not pipeline_entity:
        raise domain_exception.DomainException(f"Pipeline {command.pipelineId.value} can not be found.")
    return pipeline_entity


def __get_recipe(recipe_qry_srv: recipe_query_service.RecipeQueryService, pipeline_entity: pipeline.Pipeline):
    recipe_entity = recipe_qry_srv.get_recipe(project_id=pipeline_entity.projectId, recipe_id=pipeline_entity.recipeId)
    if not recipe_entity:
        raise domain_exception.DomainException(f"Recipe {pipeline_entity.recipeId} can not be found.")
    return recipe_entity


def __create_image(
    command: register_image_command.RegisterImageCommand,
    uow: unit_of_work.UnitOfWork,
    image_build_version: int,
    pipeline_entity: pipeline.Pipeline,
    recipe_version_name: str,
):
    current_time = datetime.now(timezone.utc).isoformat()
    image_entity = image.Image(
        projectId=pipeline_entity.projectId,
        imageBuildVersion=image_build_version,
        imageBuildVersionArn=command.imageBuildVersionArn.value,
        pipelineId=command.pipelineId.value,
        pipelineName=pipeline_entity.pipelineName,
        recipeId=pipeline_entity.recipeId,
        recipeName=pipeline_entity.recipeName,
        recipeVersionId=pipeline_entity.recipeVersionId,
        recipeVersionName=recipe_version_name,
        status=image.ImageStatus.Creating,
        createDate=current_time,
        lastUpdateDate=current_time,
    )

    with uow:
        uow.get_repository(repo_key=image.ImagePrimaryKey, repo_type=image.Image).add(image_entity)
        uow.commit()
    return image_entity
