from http import HTTPStatus

from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler import api_gateway, content_types

from app.packaging.domain.commands.component import (
    archive_component_command,
    create_component_command,
    update_component_command,
)
from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
    component_name_value_object,
    component_system_configuration_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.packaging.entrypoints.s2s_api import bootstrapper
from app.packaging.entrypoints.s2s_api.model import api_model
from app.packaging.entrypoints.s2s_api.routers import common

tracer = Tracer()

READ_SCOPE = "clients/packaging/component.read"
WRITE_SCOPE = "clients/packaging/component.write"


def init(dependencies: bootstrapper.Dependencies) -> api_gateway.Router:  # noqa: C901
    router = api_gateway.Router()

    def authorize(project_id: str, scope: str) -> str:
        current_client_id = common.client_id(router)
        dependencies.project_access_service.require_access(current_client_id, project_id)
        common.require_scope(router, scope)
        return current_client_id

    def require_component(project_id: str, component_id: str) -> None:
        dependencies.component_domain_qry_srv.require_component_in_project(
            project_id_value_object.from_str(project_id), component_id_value_object.from_str(component_id)
        )

    @tracer.capture_method
    @router.post("/projects/<project_id>/components")
    def create_component(project_id: str, request: api_model.CreateComponentRequest):
        client_id = authorize(project_id, WRITE_SCOPE)
        component_id = component_id_value_object.generate_component_id()
        dependencies.command_bus.handle(
            create_component_command.CreateComponentCommand(
                projectId=project_id_value_object.from_str(project_id),
                componentId=component_id_value_object.from_str(component_id),
                componentName=component_name_value_object.from_str(request.componentName),
                componentDescription=component_description_value_object.from_str(request.componentDescription),
                componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
                    platform=request.componentPlatform,
                    supported_architectures=request.componentSupportedArchitectures,
                    supported_os_versions=request.componentSupportedOsVersions,
                ),
                createdBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return api_gateway.Response(
            status_code=HTTPStatus.CREATED,
            body=api_model.CreateComponentResponse(componentId=component_id),
            headers=common.NO_STORE,
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.get("/projects/<project_id>/components")
    def list_components(project_id: str):
        authorize(project_id, READ_SCOPE)
        components = dependencies.component_domain_qry_srv.get_components(project_id_value_object.from_str(project_id))
        return api_model.ComponentPage(
            components=[api_model.Component.model_validate(item.model_dump()) for item in components]
        )

    @tracer.capture_method
    @router.get("/projects/<project_id>/components/<component_id>")
    def get_component(project_id: str, component_id: str):
        authorize(project_id, READ_SCOPE)
        require_component(project_id, component_id)
        component = dependencies.component_domain_qry_srv.get_component(
            component_id_value_object.from_str(component_id)
        )
        return api_model.ComponentResponse(component=api_model.Component.model_validate(component.model_dump()))

    @tracer.capture_method
    @router.put("/projects/<project_id>/components/<component_id>")
    def update_component(project_id: str, component_id: str, request: api_model.UpdateComponentRequest):
        client_id = authorize(project_id, WRITE_SCOPE)
        require_component(project_id, component_id)
        dependencies.command_bus.handle(
            update_component_command.UpdateComponentCommand(
                componentId=component_id_value_object.from_str(component_id),
                componentDescription=component_description_value_object.from_str(request.componentDescription),
                lastUpdatedBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return api_gateway.Response(status_code=HTTPStatus.OK, body={}, headers=common.NO_STORE)

    @tracer.capture_method
    @router.delete("/projects/<project_id>/components/<component_id>")
    def archive_component(project_id: str, component_id: str):
        client_id = authorize(project_id, WRITE_SCOPE)
        require_component(project_id, component_id)
        dependencies.command_bus.handle(
            archive_component_command.ArchiveComponentCommand(
                projectId=project_id_value_object.from_str(project_id),
                componentId=component_id_value_object.from_str(component_id),
                lastUpdatedBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return api_gateway.Response(status_code=HTTPStatus.OK, body={}, headers=common.NO_STORE)

    return router
