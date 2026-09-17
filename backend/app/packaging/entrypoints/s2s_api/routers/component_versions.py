from http import HTTPStatus

from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler import api_gateway, content_types

from app.packaging.domain.commands.component import (
    create_component_version_command,
    release_component_version_command,
    retire_component_version_command,
    update_component_version_command,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_license_dashboard_url_value_object,
    component_software_vendor_value_object,
    component_software_version_notes_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_release_type_value_object,
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.packaging.entrypoints.s2s_api import bootstrapper
from app.packaging.entrypoints.s2s_api.model import api_model
from app.packaging.entrypoints.s2s_api.routers import common

tracer = Tracer()

READ_SCOPE = "clients/packaging/component.read"
WRITE_SCOPE = "clients/packaging/component.write"
RELEASE_SCOPE = "clients/packaging/component.release"


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

    def require_version(component_id: str, version_id: str) -> None:
        dependencies.component_version_domain_qry_srv.require_component_version_in_component(
            component_id_value_object.from_str(component_id), component_version_id_value_object.from_str(version_id)
        )

    def version_kwargs(request, *, project_id: str, component_id: str) -> dict:
        kwargs = {
            "projectId": project_id_value_object.from_str(project_id),
            "componentId": component_id_value_object.from_str(component_id),
            "componentVersionDescription": component_version_description_value_object.from_str(
                request.componentVersionDescription
            ),
            "componentVersionYamlDefinition": component_version_yaml_definition_value_object.from_str(
                request.componentVersionYamlDefinition
            ),
            "componentVersionDependencies": component_version_dependencies_value_object.from_list(
                request.componentVersionDependencies or []
            ),
            "softwareVendor": component_software_vendor_value_object.from_str(request.softwareVendor),
            "softwareVersion": component_software_version_value_object.from_str(request.softwareVersion),
        }
        if request.licenseDashboard:
            kwargs["licenseDashboard"] = component_license_dashboard_url_value_object.from_str(request.licenseDashboard)
        if request.notes:
            kwargs["notes"] = component_software_version_notes_value_object.from_str(request.notes)
        return kwargs

    def action_response(version_id: str, status: HTTPStatus) -> api_gateway.Response:
        return api_gateway.Response(
            status_code=status,
            body=api_model.ComponentVersionActionResponse(componentVersionId=version_id),
            headers={**common.NO_STORE, "Retry-After": "5"} if status == HTTPStatus.ACCEPTED else common.NO_STORE,
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.post("/projects/<project_id>/components/<component_id>/versions")
    def create_component_version(project_id: str, component_id: str, request: api_model.CreateComponentVersionRequest):
        client_id = authorize(project_id, WRITE_SCOPE)
        require_component(project_id, component_id)
        kwargs = version_kwargs(request, project_id=project_id, component_id=component_id)
        kwargs.update(
            componentVersionReleaseType=component_version_release_type_value_object.from_str(
                request.componentVersionReleaseType
            ),
            createdBy=user_id_value_object.from_str(f"service:{client_id}"),
        )
        result = dependencies.command_bus.handle(
            create_component_version_command.CreateComponentVersionCommand(**kwargs)
        )
        return action_response(result["componentVersionId"], HTTPStatus.ACCEPTED)

    @tracer.capture_method
    @router.get("/projects/<project_id>/components/<component_id>/versions")
    def list_component_versions(project_id: str, component_id: str):
        authorize(project_id, READ_SCOPE)
        require_component(project_id, component_id)
        versions = dependencies.component_version_domain_qry_srv.get_component_versions(
            component_id_value_object.from_str(component_id)
        )
        return api_model.ComponentVersionPage(
            component_versions=[api_model.ComponentVersion.model_validate(item.model_dump()) for item in versions]
        )

    @tracer.capture_method
    @router.get("/projects/<project_id>/components/<component_id>/versions/<version_id>")
    def get_component_version(project_id: str, component_id: str, version_id: str):
        authorize(project_id, READ_SCOPE)
        require_component(project_id, component_id)
        require_version(component_id, version_id)
        component_key = component_id_value_object.from_str(component_id)
        version_key = component_version_id_value_object.from_str(version_id)
        raw_version = dependencies.component_version_qry_srv.get_component_version(component_id, version_id)
        if raw_version.componentVersionS3Uri:
            version, yaml_definition, yaml_definition_b64 = (
                dependencies.component_version_domain_qry_srv.get_component_version(component_key, version_key)
            )
        else:
            version, yaml_definition, yaml_definition_b64 = raw_version, None, None
        return api_model.ComponentVersionResponse(
            component_version=api_model.ComponentVersion.model_validate(version.model_dump()),
            yaml_definition=yaml_definition,
            yaml_definition_b64=yaml_definition_b64,
        )

    @tracer.capture_method
    @router.put("/projects/<project_id>/components/<component_id>/versions/<version_id>")
    def update_component_version(
        project_id: str, component_id: str, version_id: str, request: api_model.UpdateComponentVersionRequest
    ):
        client_id = authorize(project_id, WRITE_SCOPE)
        require_component(project_id, component_id)
        require_version(component_id, version_id)
        kwargs = version_kwargs(request, project_id=project_id, component_id=component_id)
        kwargs.update(
            componentVersionId=component_version_id_value_object.from_str(version_id),
            lastUpdatedBy=user_id_value_object.from_str(f"service:{client_id}"),
        )
        result = dependencies.command_bus.handle(
            update_component_version_command.UpdateComponentVersionCommand(**kwargs)
        )
        return action_response(result["componentVersionId"], HTTPStatus.ACCEPTED)

    @tracer.capture_method
    @router.delete("/projects/<project_id>/components/<component_id>/versions/<version_id>")
    def retire_component_version(project_id: str, component_id: str, version_id: str):
        client_id = authorize(project_id, WRITE_SCOPE)
        require_component(project_id, component_id)
        require_version(component_id, version_id)
        result = dependencies.command_bus.handle(
            retire_component_version_command.RetireComponentVersionCommand(
                componentId=component_id_value_object.from_str(component_id),
                componentVersionId=component_version_id_value_object.from_str(version_id),
                serviceAuthorized=True,
                lastUpdatedBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return action_response(result["componentVersionId"], HTTPStatus.ACCEPTED)

    @tracer.capture_method
    @router.post("/projects/<project_id>/components/<component_id>/versions/<version_id>/release")
    def release_component_version(project_id: str, component_id: str, version_id: str):
        client_id = authorize(project_id, RELEASE_SCOPE)
        require_component(project_id, component_id)
        require_version(component_id, version_id)
        result = dependencies.command_bus.handle(
            release_component_version_command.ReleaseComponentVersionCommand(
                projectId=project_id_value_object.from_str(project_id),
                componentId=component_id_value_object.from_str(component_id),
                componentVersionId=component_version_id_value_object.from_str(version_id),
                lastUpdatedBy=user_id_value_object.from_str(f"service:{client_id}"),
            )
        )
        return action_response(result["componentVersionId"], HTTPStatus.OK)

    return router
