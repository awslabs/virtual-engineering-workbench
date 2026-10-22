from http import HTTPStatus

from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.packaging.domain.commands.image import create_image_command
from app.packaging.domain.commands.pipeline import (
    create_pipeline_command,
    retire_pipeline_command,
    update_pipeline_command,
)
from app.packaging.domain.value_objects.image import image_id_value_object, product_id_value_object
from app.packaging.domain.value_objects.pipeline import (
    pipeline_build_instance_types_value_object,
    pipeline_description_value_object,
    pipeline_id_value_object,
    pipeline_name_value_object,
    pipeline_schedule_value_object,
)
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.packaging.entrypoints.s2s_api import bootstrapper
from app.packaging.entrypoints.s2s_api.model import api_model
from app.packaging.entrypoints.s2s_api.routers import common

tracer = Tracer()

READ_SCOPE = "clients/packaging/pipeline.read"
WRITE_SCOPE = "clients/packaging/pipeline.write"
EXECUTE_SCOPE = "clients/packaging/pipeline.execute"


def init(dependencies: bootstrapper.Dependencies) -> api_gateway.Router:  # noqa: C901
    router = api_gateway.Router()

    def authorize(project_id: str, scope: str) -> str:
        current_client_id = common.client_id(router)
        dependencies.project_access_service.require_access(current_client_id, project_id)
        common.require_scope(router, scope)
        return current_client_id

    def pipeline_in_project(project_id: str, pipeline_id: str):
        pipeline = dependencies.pipeline_domain_qry_srv.get_pipeline(
            project_id_value_object.from_str(project_id), pipeline_id_value_object.from_str(pipeline_id)
        )
        if pipeline is None:
            raise NotFoundError(f"Pipeline {pipeline_id} not found in project {project_id}.")
        return pipeline

    def image_in_project(project_id: str, image_id: str):
        image = dependencies.image_domain_qry_srv.get_image(
            project_id_value_object.from_str(project_id), image_id_value_object.from_str(image_id)
        )
        if image is None:
            raise NotFoundError(f"Image {image_id} not found in project {project_id}.")
        return image

    def action_response(pipeline_id: str) -> api_gateway.Response:
        return api_gateway.Response(
            status_code=HTTPStatus.ACCEPTED,
            body=api_model.PipelineActionResponse(pipelineId=pipeline_id),
            headers={**common.NO_STORE, "Retry-After": "5"},
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.post("/projects/<project_id>/pipelines")
    def create_pipeline(project_id: str, request: api_model.CreatePipelineRequest):
        client_id = authorize(project_id, WRITE_SCOPE)
        dependencies.recipe_domain_qry_srv.require_recipe_in_project(
            project_id_value_object.from_str(project_id), recipe_id_value_object.from_str(request.recipeId)
        )
        dependencies.recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
            recipe_id_value_object.from_str(request.recipeId),
            recipe_version_id_value_object.from_str(request.recipeVersionId),
        )
        result = dependencies.command_bus.handle(
            create_pipeline_command.CreatePipelineCommand(
                projectId=project_id_value_object.from_str(project_id),
                buildInstanceTypes=pipeline_build_instance_types_value_object.from_list(request.buildInstanceTypes),
                pipelineDescription=pipeline_description_value_object.from_str(request.pipelineDescription),
                pipelineName=pipeline_name_value_object.from_str(request.pipelineName),
                pipelineSchedule=pipeline_schedule_value_object.from_str(request.pipelineSchedule),
                recipeId=recipe_id_value_object.from_str(request.recipeId),
                recipeVersionId=recipe_version_id_value_object.from_str(request.recipeVersionId),
                productId=product_id_value_object.from_str(request.productId) if request.productId else None,
                createdBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return action_response(result["pipelineId"])

    @tracer.capture_method
    @router.get("/projects/<project_id>/pipelines")
    def list_pipelines(project_id: str):
        authorize(project_id, READ_SCOPE)
        pipelines = dependencies.pipeline_domain_qry_srv.get_pipelines(project_id_value_object.from_str(project_id))
        return api_model.PipelinePage(
            pipelines=[api_model.Pipeline.model_validate(pipeline.model_dump()) for pipeline in pipelines]
        )

    @tracer.capture_method
    @router.get("/projects/<project_id>/pipelines/<pipeline_id>")
    def get_pipeline(project_id: str, pipeline_id: str):
        authorize(project_id, READ_SCOPE)
        pipeline = pipeline_in_project(project_id, pipeline_id)
        return api_model.PipelineResponse(pipeline=api_model.Pipeline.model_validate(pipeline.model_dump()))

    @tracer.capture_method
    @router.put("/projects/<project_id>/pipelines/<pipeline_id>")
    def update_pipeline(project_id: str, pipeline_id: str, request: api_model.UpdatePipelineRequest):
        client_id = authorize(project_id, WRITE_SCOPE)
        pipeline = pipeline_in_project(project_id, pipeline_id)
        kwargs = {}
        if request.pipelineSchedule:
            kwargs["pipelineSchedule"] = pipeline_schedule_value_object.from_str(request.pipelineSchedule)
        if request.buildInstanceTypes:
            kwargs["buildInstanceTypes"] = pipeline_build_instance_types_value_object.from_list(
                request.buildInstanceTypes
            )
        if request.recipeVersionId:
            dependencies.recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
                recipe_id_value_object.from_str(pipeline.recipeId),
                recipe_version_id_value_object.from_str(request.recipeVersionId),
            )
            kwargs["recipeVersionId"] = recipe_version_id_value_object.from_str(request.recipeVersionId)
        kwargs["productId"] = product_id_value_object.from_str(request.productId) if request.productId else None
        dependencies.command_bus.handle(
            update_pipeline_command.UpdatePipelineCommand(
                projectId=project_id_value_object.from_str(project_id),
                pipelineId=pipeline_id_value_object.from_str(pipeline_id),
                lastUpdatedBy=user_id_value_object.from_str(f"service:{client_id}"),
                **kwargs,
            )
        )
        return action_response(pipeline_id)

    @tracer.capture_method
    @router.delete("/projects/<project_id>/pipelines/<pipeline_id>")
    def retire_pipeline(project_id: str, pipeline_id: str):
        client_id = authorize(project_id, WRITE_SCOPE)
        pipeline_in_project(project_id, pipeline_id)
        dependencies.command_bus.handle(
            retire_pipeline_command.RetirePipelineCommand(
                projectId=project_id_value_object.from_str(project_id),
                pipelineId=pipeline_id_value_object.from_str(pipeline_id),
                lastUpdateBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return action_response(pipeline_id)

    @tracer.capture_method
    @router.post("/projects/<project_id>/images")
    def create_image(project_id: str, request: api_model.CreateImageRequest):
        authorize(project_id, EXECUTE_SCOPE)
        pipeline_in_project(project_id, request.pipelineId)
        image_id = dependencies.command_bus.handle(
            create_image_command.CreateImageCommand(
                projectId=project_id_value_object.from_str(project_id),
                pipelineId=pipeline_id_value_object.from_str(request.pipelineId),
            )
        )
        return api_gateway.Response(
            status_code=HTTPStatus.ACCEPTED,
            body=api_model.CreateImageResponse(imageId=image_id),
            headers={**common.NO_STORE, "Retry-After": "5"},
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.get("/projects/<project_id>/images")
    def list_images(project_id: str):
        authorize(project_id, READ_SCOPE)
        images = dependencies.image_domain_qry_srv.get_images(project_id_value_object.from_str(project_id))
        return api_model.ImagePage(images=[image_model(image) for image in images])

    @tracer.capture_method
    @router.get("/projects/<project_id>/images/<image_id>")
    def get_image(project_id: str, image_id: str):
        authorize(project_id, READ_SCOPE)
        return api_model.ImageResponse(image=image_model(image_in_project(project_id, image_id)))

    return router


def image_model(image) -> api_model.Image:
    return api_model.Image.model_validate({**image.model_dump(), "imageBuildVersion": str(image.imageBuildVersion)})
