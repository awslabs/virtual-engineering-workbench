from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated

from aws_lambda_powertools import logging, tracing
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.openapi.models import Server
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.utilities import typing
from aws_xray_sdk.core import patch_all

from app.packaging.domain.commands.component import (
    archive_component_command,
    create_component_command,
    create_component_version_command,
    create_mandatory_components_list_command,
    release_component_version_command,
    retire_component_version_command,
    share_component_command,
    update_component_command,
    update_component_version_command,
    update_mandatory_components_list_command,
    validate_component_version_command,
)
from app.packaging.domain.commands.image import create_image_command, import_image_command
from app.packaging.domain.commands.marketplace import (
    accept_agreement_request_command,
    cancel_agreement_command,
    create_agreement_request_command,
)
from app.packaging.domain.commands.pipeline import (
    create_pipeline_command,
    retire_pipeline_command,
    update_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    archive_recipe_command,
    create_recipe_command,
    create_recipe_version_command,
    release_recipe_version_command,
    retire_recipe_version_command,
    update_recipe_version_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image.image_constants import (
    ImageSource,
    SubscriptionOwnership,
)
from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
    component_name_value_object,
    component_platform_value_object,
    component_supported_architecture_value_object,
    component_supported_os_version_value_object,
    component_system_configuration_value_object,
)
from app.packaging.domain.value_objects.component_version import (
    component_license_dashboard_url_value_object,
    component_software_vendor_value_object,
    component_software_version_notes_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_release_type_value_object,
    component_version_status_value_object,
    component_version_yaml_definition_value_object,
    components_versions_list_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
    component_version_test_execution_instance_id_value_object,
)
from app.packaging.domain.value_objects.image import (
    ami_id_value_object,
    image_id_value_object,
    image_name_value_object,
    image_source_value_object,
    os_version_value_object,
    platform_value_object,
    product_code_value_object,
    product_id_value_object,
)
from app.packaging.domain.value_objects.marketplace import (
    agreement_id_value_object,
    agreement_request_id_value_object,
    offer_id_value_object,
)
from app.packaging.domain.value_objects.pipeline import (
    pipeline_build_instance_types_value_object,
    pipeline_description_value_object,
    pipeline_id_value_object,
    pipeline_name_value_object,
    pipeline_schedule_value_object,
)
from app.packaging.domain.value_objects.recipe import (
    recipe_description_value_object,
    recipe_id_value_object,
    recipe_name_value_object,
    recipe_system_configuration_value_object,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
    recipe_version_description_value_object,
    recipe_version_id_value_object,
    recipe_version_integration_value_object,
    recipe_version_release_type_value_object,
    recipe_version_status_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_id_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.packaging.entrypoints.api import bootstrapper, config
from app.packaging.entrypoints.api.model import api_model
from app.packaging.entrypoints.api.model.api_model import (
    GetImageResponse,
    GetImagesResponse,
    UpdatePipelineResponse,
)
from app.shared.logging.helpers import clear_auth_headers
from app.shared.middleware import authorization, exception_handler
from app.shared.middleware.authorization import VirtualWorkbenchRoles
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig(**config.config)
default_region_name = app_config.get_default_region()
secret_name = app_config.get_audit_logging_key_name()

cors_config = api_gateway.CORSConfig(**app_config.cors_config)
app = api_gateway.APIGatewayRestResolver(
    cors=cors_config,
    strip_prefixes=app_config.get_strip_prefixes(),
    enable_validation=True,
)
app.use(middlewares=[authorization.require_auth_context])
app.enable_swagger(
    path="/_swagger",
    title="Packaging BC API",
    servers=[Server(url=f"{app_config.get_api_base_path()}")],
)

logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger)

TAG_COMPONENTS = "Components"
TAG_COMPONENT_VERSIONS = "Component Versions"
TAG_COMPONENT_TESTING = "Component Testing"
TAG_MANDATORY_COMPONENTS = "Mandatory Components"
TAG_PIPELINES = "Pipelines"
TAG_RECIPES = "Recipes"
TAG_RECIPE_VERSIONS = "Recipe Versions"
TAG_RECIPE_TESTING = "Recipe Testing"
TAG_IMAGES = "Images"
TAG_MARKETPLACE = "Marketplace"


@tracer.capture_method
@app.get("/projects/<project_id>/components", tags=[TAG_COMPONENTS])
def get_components(
    project_id: str,
) -> api_gateway.Response[api_model.GetComponentsResponse]:
    """Lists components associated to a specific project."""

    components = dependencies.component_domain_qry_srv.get_components(
        project_id=project_id_value_object.from_str(project_id),
    )

    components_parsed = [api_model.Component.model_validate(component.model_dump()) for component in components]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentsResponse(components=components_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/components", tags=[TAG_COMPONENTS])
def create_component(
    request: api_model.CreateComponentRequest,
    project_id: str,
) -> api_gateway.Response[api_model.CreateComponentResponse]:
    """Creates a component."""

    component_id = component_id_value_object.generate_component_id()
    command = create_component_command.CreateComponentCommand(
        projectId=project_id_value_object.from_str(project_id),
        componentId=component_id_value_object.from_str(component_id),
        componentName=component_name_value_object.from_str(request.componentName),
        componentDescription=component_description_value_object.from_str(request.componentDescription),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform=request.componentPlatform,
            supported_architectures=request.componentSupportedArchitectures,
            supported_os_versions=request.componentSupportedOsVersions,
        ),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateComponentResponse(componentId=component_id),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/components/<component_id>", tags=[TAG_COMPONENTS])
def share_component(
    request: api_model.ShareComponentRequest,
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.ShareComponentResponse]:
    """Shares a component with a list of projects."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    command = share_component_command.ShareComponentCommand(
        projectIds=[project_id_value_object.from_str(project) for project in request.projectIds],
        componentId=component_id_value_object.from_str(component_id),
        userRoles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ShareComponentResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/components/<component_id>", tags=[TAG_COMPONENTS])
def get_component(
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.GetComponentResponse]:
    """Get a specific component."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    component = dependencies.component_domain_qry_srv.get_component(
        component_id=component_id_value_object.from_str(component_id),
    )

    component_association = dependencies.component_domain_qry_srv.get_component_project_associations(
        component_id=component_id_value_object.from_str(component_id),
    )

    component_parsed = api_model.Component.model_validate(component.model_dump())
    associated_projects = [api_model.AssociatedProject.model_validate(ca.model_dump()) for ca in component_association]
    component_metadata = api_model.ComponentMetadata(associatedProjects=associated_projects)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentResponse(component=component_parsed, metadata=component_metadata),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/components/<component_id>", tags=[TAG_COMPONENTS])
def update_component(
    request: api_model.UpdateComponentRequest,
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.UpdateComponentResponse]:
    """Update a component name and description."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    command = update_component_command.UpdateComponentCommand(
        componentId=component_id_value_object.from_str(component_id),
        componentDescription=component_description_value_object.from_str(request.componentDescription),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateComponentResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/components/<component_id>", tags=[TAG_COMPONENTS])
def archive_component(
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.ArchiveComponentResponse]:
    """Archive a specific component."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    command = archive_component_command.ArchiveComponentCommand(
        projectId=project_id_value_object.from_str(project_id),
        componentId=component_id_value_object.from_str(component_id),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ArchiveComponentResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/components/<component_id>/versions",
    tags=[TAG_COMPONENT_VERSIONS],
)
def get_component_versions(
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.GetComponentVersionsResponse]:
    """Lists versions associated to a specific component."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    component_versions = dependencies.component_version_domain_qry_srv.get_component_versions(
        component_id=component_id_value_object.from_str(component_id),
    )

    component_versions_parsed = [
        api_model.ComponentVersion.model_validate(component_version.model_dump())
        for component_version in component_versions
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentVersionsResponse(component_versions=component_versions_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/components/<component_id>/versions",
    tags=[TAG_COMPONENT_VERSIONS],
)
def create_component_version(
    request: api_model.CreateComponentVersionRequest,
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.CreateComponentVersionResponse]:
    """Creates a component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    kwargs = {
        "projectId": project_id_value_object.from_str(project_id),
        "componentId": component_id_value_object.from_str(component_id),
        "componentVersionDescription": component_version_description_value_object.from_str(
            request.componentVersionDescription
        ),
        "componentVersionReleaseType": component_version_release_type_value_object.from_str(
            request.componentVersionReleaseType
        ),
        "componentVersionYamlDefinition": component_version_yaml_definition_value_object.from_str(
            request.componentVersionYamlDefinition
        ),
        "componentVersionDependencies": (
            component_version_dependencies_value_object.from_list(request.componentVersionDependencies)
            if request.componentVersionDependencies
            else component_version_dependencies_value_object.from_list([])
        ),
        "softwareVendor": component_software_vendor_value_object.from_str(request.softwareVendor),
        "softwareVersion": component_software_version_value_object.from_str(request.softwareVersion),
        "createdBy": user_id_value_object.from_str(app.context.get("user_principal").user_name),
    }

    if request.licenseDashboard:
        kwargs["licenseDashboard"] = component_license_dashboard_url_value_object.from_str(request.licenseDashboard)

    if request.notes:
        kwargs["notes"] = component_software_version_notes_value_object.from_str(request.notes)

    command = create_component_version_command.CreateComponentVersionCommand(**kwargs)

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateComponentVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/components/<component_id>/validate-version",
    tags=[TAG_COMPONENT_VERSIONS],
)
def validate_component_version(
    request: api_model.ValidateComponentVersionRequest,
    project_id: str,
    component_id: str,
) -> api_gateway.Response[api_model.ValidateComponentVersionResponse]:
    """Validates a component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    command = validate_component_version_command.ValidateComponentVersionCommand(
        componentId=component_id_value_object.from_str(component_id),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            request.componentVersionYamlDefinition
        ),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ValidateComponentVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/components/<component_id>/versions/<version_id>",
    tags=[TAG_COMPONENT_VERSIONS],
)
def get_component_version(
    project_id: str,
    component_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.GetComponentVersionResponse]:
    """Get a specific component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    component_version, yaml_definition_obj, yaml_definition_b64 = (
        dependencies.component_version_domain_qry_srv.get_component_version(
            component_id=component_id_value_object.from_str(component_id),
            version_id=component_version_id_value_object.from_str(version_id),
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentVersionResponse(
            component_version=api_model.ComponentVersion.model_validate(component_version.model_dump()),
            yaml_definition=yaml_definition_obj,
            yaml_definition_b64=yaml_definition_b64,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/components-versions", tags=[TAG_COMPONENT_VERSIONS])
def get_components_versions(
    project_id: str,
    arch_param: Annotated[list[str] | None, Query(alias="arch")] = None,
    global_param: Annotated[list[str] | None, Query(alias="global")] = None,
    os_param: Annotated[list[str] | None, Query(alias="os")] = None,
    platform_param: Annotated[list[str] | None, Query(alias="platform")] = None,
    status_param: Annotated[list[str] | None, Query(alias="status")] = None,
) -> api_gateway.Response[api_model.GetComponentsVersionsResponse]:
    """Get all components versions given a status, platform, OS version, and architecture."""

    kwargs = {
        "architecture": component_supported_architecture_value_object.from_str(
            arch_param.pop() if arch_param else None
        ),
        "os": component_supported_os_version_value_object.from_str(os_param.pop() if os_param else None),
        "platform": component_platform_value_object.from_str(platform_param.pop() if platform_param else None),
        "statuses": (
            [component_version_status_value_object.from_str(status) for status in status_param]
            if status_param
            else [component_version_status_value_object.from_str(None)]
        ),
        "project_id": project_id_value_object.from_str(project_id),
    }
    if (
        any(
            [
                user_role_value_object.from_str(item).value == VirtualWorkbenchRoles.Admin
                for item in app.context.get("user_principal").user_roles
            ]
        )
        and (global_param.pop() if global_param else None) == "true"
    ):
        del kwargs["project_id"]
    components_versions_summary = dependencies.component_version_domain_qry_srv.get_all_components_versions(**kwargs)
    components_versions_summary_parsed = [
        api_model.ComponentVersionSummary.model_validate(component_version.model_dump())
        for component_version in components_versions_summary
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentsVersionsResponse(components_versions_summary=components_versions_summary_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/components/<component_id>/versions/<version_id>",
    tags=[TAG_COMPONENT_VERSIONS],
)
def release_component_version(
    project_id: str,
    component_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.ReleaseComponentVersionResponse]:
    """Releases a component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    command = release_component_version_command.ReleaseComponentVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        componentId=component_id_value_object.from_str(component_id),
        componentVersionId=component_version_id_value_object.from_str(version_id),
        userRoles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ReleaseComponentVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put(
    "/projects/<project_id>/components/<component_id>/versions/<version_id>",
    tags=[TAG_COMPONENT_VERSIONS],
)
def update_component_version(
    request: api_model.UpdateComponentVersionRequest,
    project_id: str,
    component_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.UpdateComponentVersionResponse]:
    """Updates a component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    kwargs = {
        "projectId": project_id_value_object.from_str(project_id),
        "componentId": component_id_value_object.from_str(component_id),
        "componentVersionId": component_version_id_value_object.from_str(version_id),
        "componentVersionDescription": component_version_description_value_object.from_str(
            request.componentVersionDescription
        ),
        "componentVersionYamlDefinition": component_version_yaml_definition_value_object.from_str(
            request.componentVersionYamlDefinition
        ),
        "componentVersionDependencies": (
            component_version_dependencies_value_object.from_list(request.componentVersionDependencies)
            if request.componentVersionDependencies
            else component_version_dependencies_value_object.from_list([])
        ),
        "softwareVendor": component_software_vendor_value_object.from_str(request.softwareVendor),
        "softwareVersion": component_software_version_value_object.from_str(request.softwareVersion),
        "lastUpdatedBy": user_id_value_object.from_str(app.context.get("user_principal").user_name),
    }

    if request.licenseDashboard:
        kwargs["licenseDashboard"] = component_license_dashboard_url_value_object.from_str(request.licenseDashboard)
    if request.notes:
        kwargs["notes"] = component_software_version_notes_value_object.from_str(request.notes)
    command = update_component_version_command.UpdateComponentVersionCommand(**kwargs)

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateComponentVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/components/<component_id>/versions/<version_id>/test-executions",
    tags=[TAG_COMPONENT_TESTING],
)
def get_component_version_test_executions(
    project_id: str,
    component_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.GetComponentVersionTestExecutionsResponse]:
    """Lists test executions associated to a specific component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )
    dependencies.component_version_domain_qry_srv.require_component_version_in_component(
        component_id=component_id_value_object.from_str(component_id),
        version_id=component_version_id_value_object.from_str(version_id),
    )

    component_version_test_execution_summaries = (
        dependencies.component_version_test_execution_domain_qry_srv.get_component_version_test_execution_summaries(
            version_id=component_version_id_value_object.from_str(version_id),
        )
    )

    component_version_test_execution_summaries_parsed = [
        api_model.ComponentVersionTestExecutionSummary.model_validate(
            component_version_test_execution_summary.model_dump()
        )
        for component_version_test_execution_summary in component_version_test_execution_summaries
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentVersionTestExecutionsResponse(
            component_version_test_execution_summaries=component_version_test_execution_summaries_parsed
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/components/<component_id>/versions/<version_id>/test-executions/<test_execution_id>/<instance_id>/logs-url",
    tags=[TAG_COMPONENT_TESTING],
)
def get_component_version_test_execution_logs_url(
    project_id: str,
    component_id: str,
    version_id: str,
    test_execution_id: str,
    instance_id: str,
) -> api_gateway.Response[api_model.GetComponentVersionTestExecutionLogsUrlResponse]:
    """Get logs url of a specific component version test execution."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )
    dependencies.component_version_domain_qry_srv.require_component_version_in_component(
        component_id=component_id_value_object.from_str(component_id),
        version_id=component_version_id_value_object.from_str(version_id),
    )

    s3_presigned_url = (
        dependencies.component_version_test_execution_domain_qry_srv.get_component_version_test_execution_logs_url(
            version_id=component_version_id_value_object.from_str(version_id),
            test_execution_id=component_version_test_execution_id_value_object.from_str(test_execution_id),
            instance_id=component_version_test_execution_instance_id_value_object.from_str(instance_id),
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetComponentVersionTestExecutionLogsUrlResponse(logs_url=s3_presigned_url),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete(
    "/projects/<project_id>/components/<component_id>/versions/<version_id>",
    tags=[TAG_COMPONENT_VERSIONS],
)
def retire_component_version(
    project_id: str, component_id: str, version_id: str
) -> api_gateway.Response[api_model.RetireComponentVersionResponse]:
    """Retire a specific component version."""

    dependencies.component_domain_qry_srv.require_component_in_project(
        project_id=project_id_value_object.from_str(project_id),
        component_id=component_id_value_object.from_str(component_id),
    )

    command = retire_component_version_command.RetireComponentVersionCommand(
        componentId=component_id_value_object.from_str(component_id),
        componentVersionId=component_version_id_value_object.from_str(version_id),
        userRoles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RetireComponentVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/mandatory-components-list", tags=[TAG_MANDATORY_COMPONENTS])
def get_mandatory_components_list(
    project_id: str,
    supported_architecture: Annotated[list[str] | None, Query(alias="mandatoryComponentsListArchitecture")] = None,
    supported_os_version: Annotated[list[str] | None, Query(alias="mandatoryComponentsListOsVersion")] = None,
    platform: Annotated[list[str] | None, Query(alias="mandatoryComponentsListPlatform")] = None,
) -> api_gateway.Response[api_model.GetMandatoryComponentsListResponse]:
    """Get a mandatory components list given a platform, OS version, and architecture."""
    arch_vo = component_supported_architecture_value_object.from_str(
        supported_architecture.pop() if supported_architecture else None
    )
    os_vo = component_supported_os_version_value_object.from_str(
        supported_os_version.pop() if supported_os_version else None
    )
    platform_vo = component_platform_value_object.from_str(platform.pop() if platform else None)

    mandatory_components_list = dependencies.mandatory_components_list_domain_qry_srv.get_mandatory_components_list(
        architecture=arch_vo,
        os=os_vo,
        platform=platform_vo,
    )

    if mandatory_components_list is None:
        return api_gateway.Response(
            status_code=HTTPStatus.OK,
            body=api_model.GetMandatoryComponentsListResponse(
                mandatoryComponentsList=api_model.MandatoryComponentsList(
                    mandatoryComponentsListPlatform=platform_vo.value,
                    mandatoryComponentsListOsVersion=os_vo.value,
                    mandatoryComponentsListArchitecture=arch_vo.value,
                    prependedComponentsVersions=[],
                    appendedComponentsVersions=[],
                )
            ),
            content_type=content_types.APPLICATION_JSON,
        )

    prepended_components = [
        comp.model_dump()
        for comp in mandatory_components_list.mandatoryComponentsVersions
        if comp.position == "PREPEND"
    ]
    appended_components = [
        comp.model_dump() for comp in mandatory_components_list.mandatoryComponentsVersions if comp.position == "APPEND"
    ]

    mandatory_components_list_parsed = api_model.MandatoryComponentsList(
        mandatoryComponentsListPlatform=mandatory_components_list.mandatoryComponentsListPlatform,
        mandatoryComponentsListOsVersion=mandatory_components_list.mandatoryComponentsListOsVersion,
        mandatoryComponentsListArchitecture=mandatory_components_list.mandatoryComponentsListArchitecture,
        prependedComponentsVersions=prepended_components,
        appendedComponentsVersions=appended_components,
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetMandatoryComponentsListResponse(mandatoryComponentsList=mandatory_components_list_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/mandatory-components-list", tags=[TAG_MANDATORY_COMPONENTS])
def create_mandatory_components_list(
    request: api_model.CreateMandatoryComponentsListRequest,
    project_id: str,
) -> api_gateway.Response[api_model.CreateMandatoryComponentsListResponse]:
    """Create a mandatory components list given a platform, OS version, and architecture."""

    command = create_mandatory_components_list_command.CreateMandatoryComponentsListCommand(
        mandatoryComponentsListArchitecture=component_supported_architecture_value_object.from_str(
            request.mandatoryComponentsListArchitecture
        ),
        mandatoryComponentsListOsVersion=component_supported_os_version_value_object.from_str(
            request.mandatoryComponentsListOsVersion
        ),
        mandatoryComponentsListPlatform=component_platform_value_object.from_str(
            request.mandatoryComponentsListPlatform
        ),
        prependedComponentsVersions=components_versions_list_value_object.from_list(
            request.prependedComponentsVersions
        ),
        appendedComponentsVersions=components_versions_list_value_object.from_list(request.appendedComponentsVersions),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateMandatoryComponentsListResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/mandatory-components-list", tags=[TAG_MANDATORY_COMPONENTS])
def update_mandatory_components_list(
    request: api_model.UpdateMandatoryComponentsListRequest,
    project_id: str,
) -> api_gateway.Response[api_model.UpdateMandatoryComponentsListResponse]:
    """Update a mandatory components list given a platform, OS version, and architecture."""

    command = update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand(
        mandatoryComponentsListArchitecture=component_supported_architecture_value_object.from_str(
            request.mandatoryComponentsListArchitecture
        ),
        mandatoryComponentsListOsVersion=component_supported_os_version_value_object.from_str(
            request.mandatoryComponentsListOsVersion
        ),
        mandatoryComponentsListPlatform=component_platform_value_object.from_str(
            request.mandatoryComponentsListPlatform
        ),
        prependedComponentsVersions=components_versions_list_value_object.from_list(
            request.prependedComponentsVersions
        ),
        appendedComponentsVersions=components_versions_list_value_object.from_list(request.appendedComponentsVersions),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateMandatoryComponentsListResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/mandatory-components-lists", tags=[TAG_MANDATORY_COMPONENTS])
def get_mandatory_components_lists(
    project_id: str,
) -> api_gateway.Response[api_model.GetMandatoryComponentsListsResponse]:
    """Get all the available mandatory components lists."""

    mandatory_components_lists = dependencies.mandatory_components_list_domain_qry_srv.get_mandatory_components_lists()

    mandatory_components_lists_parsed = []
    for mandatory_components_list in mandatory_components_lists:
        prepended_components = [
            comp.model_dump()
            for comp in mandatory_components_list.mandatoryComponentsVersions
            if comp.position == "PREPEND"
        ]
        appended_components = [
            comp.model_dump()
            for comp in mandatory_components_list.mandatoryComponentsVersions
            if comp.position == "APPEND"
        ]

        mandatory_components_lists_parsed.append(
            api_model.MandatoryComponentsList(
                mandatoryComponentsListPlatform=mandatory_components_list.mandatoryComponentsListPlatform,
                mandatoryComponentsListOsVersion=mandatory_components_list.mandatoryComponentsListOsVersion,
                mandatoryComponentsListArchitecture=mandatory_components_list.mandatoryComponentsListArchitecture,
                prependedComponentsVersions=prepended_components,
                appendedComponentsVersions=appended_components,
            )
        )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetMandatoryComponentsListsResponse(mandatoryComponentsLists=mandatory_components_lists_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/recipes", tags=[TAG_RECIPES])
def create_recipe(
    request: api_model.CreateRecipeRequest,
    project_id: str,
) -> api_gateway.Response[api_model.CreateRecipeResponse]:
    """Creates a recipe."""

    command = create_recipe_command.CreateRecipeCommand(
        projectId=project_id_value_object.from_str(project_id),
        recipeName=recipe_name_value_object.from_str(request.recipeName),
        recipeDescription=recipe_description_value_object.from_str(request.recipeDescription),
        recipeSystemConfiguration=recipe_system_configuration_value_object.from_attrs(
            platform=request.recipePlatform,
            architecture=request.recipeArchitecture,
            os_version=request.recipeOsVersion,
        ),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateRecipeResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/recipes", tags=[TAG_RECIPES])
def get_recipes(
    project_id: str,
) -> api_gateway.Response[api_model.GetRecipesResponse]:
    """Lists recipes associated to a specific project."""

    recipes = dependencies.recipe_domain_qry_srv.get_recipes(
        project_id=project_id_value_object.from_str(project_id),
    )

    recipes_parsed = [api_model.Recipe.model_validate(recipe.model_dump()) for recipe in recipes]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipesResponse(recipes=recipes_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/recipes/<recipe_id>", tags=[TAG_RECIPES])
def get_recipe(
    project_id: str,
    recipe_id: str,
) -> api_gateway.Response[api_model.GetRecipeResponse]:
    """Get a specific recipe."""

    recipe = dependencies.recipe_domain_qry_srv.get_recipe(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipeResponse(recipe=api_model.Recipe.model_validate(recipe.model_dump())),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/recipes/<recipe_id>/versions", tags=[TAG_RECIPE_VERSIONS])
def create_recipe_version(
    request: api_model.CreateRecipeVersionRequest,
    project_id: str,
    recipe_id: str,
) -> api_gateway.Response[api_model.CreateRecipeVersionResponse]:
    """Creates a recipe version."""

    command = create_recipe_version_command.CreateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        recipeId=recipe_id_value_object.from_str(recipe_id),
        recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
            request.recipeComponentsVersions
        ),
        recipeVersionDescription=recipe_version_description_value_object.from_str(request.recipeVersionDescription),
        recipeVersionReleaseType=recipe_version_release_type_value_object.from_str(request.recipeVersionReleaseType),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(request.recipeVersionVolumeSize),
        recipeVersionIntegrations=recipe_version_integration_value_object.from_str_array(
            request.recipeVersionIntegrations or []
        ),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateRecipeVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/recipes/<recipe_id>", tags=[TAG_RECIPES])
def archive_recipe(
    project_id: str,
    recipe_id: str,
) -> api_gateway.Response[api_model.ArchiveRecipeResponse]:
    """Archive a specific recipe."""
    command = archive_recipe_command.ArchiveRecipeCommand(
        projectId=project_id_value_object.from_str(project_id),
        recipeId=recipe_id_value_object.from_str(recipe_id),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ArchiveRecipeResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/recipes/<recipe_id>/versions", tags=[TAG_RECIPE_VERSIONS])
def get_recipe_versions(
    project_id: str,
    recipe_id: str,
) -> api_gateway.Response[api_model.GetRecipeVersionsResponse]:
    """Lists versions associated to a specific recipe."""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    recipe_versions = dependencies.recipe_version_domain_qry_srv.get_recipe_versions(
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    recipe_versions_parsed = [
        api_model.RecipeVersion.model_validate(recipe_version.model_dump()) for recipe_version in recipe_versions
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipeVersionsResponse(recipe_versions=recipe_versions_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete(
    "/projects/<project_id>/recipes/<recipe_id>/versions/<version_id>",
    tags=[TAG_RECIPE_VERSIONS],
)
def retire_recipe_version(
    project_id: str, recipe_id: str, version_id: str
) -> api_gateway.Response[api_model.RetireRecipeVersionResponse]:
    """Retire a specific recipe version."""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    command = retire_recipe_version_command.RetireRecipeVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        recipeId=recipe_id_value_object.from_str(recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(version_id),
        userRoles=[user_role_value_object.from_str(role) for role in app.context.get("user_principal").user_roles],
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RetireRecipeVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/recipes/<recipe_id>/versions/<version_id>",
    tags=[TAG_RECIPE_VERSIONS],
)
def get_recipe_version(
    project_id: str, recipe_id: str, version_id: str
) -> api_gateway.Response[api_model.GetRecipeVersionResponse]:
    """Get a specific recipe version."""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    recipe_version = dependencies.recipe_version_domain_qry_srv.get_recipe_version(
        recipe_id=recipe_id_value_object.from_str(recipe_id),
        version_id=recipe_version_id_value_object.from_str(version_id),
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipeVersionResponse(
            recipe_version=api_model.RecipeVersion.model_validate(recipe_version.model_dump())
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put(
    "/projects/<project_id>/recipes/<recipe_id>/versions/<version_id>",
    tags=[TAG_RECIPE_VERSIONS],
)
def update_recipe_version(
    request: api_model.UpdateRecipeVersionRequest,
    project_id: str,
    recipe_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.UpdateRecipeVersionResponse]:
    """Updates a specific recipe version"""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    command = update_recipe_version_command.UpdateRecipeVersionCommand(
        projectId=project_id_value_object.from_str(project_id),
        recipeId=recipe_id_value_object.from_str(recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(version_id),
        recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
            request.recipeComponentsVersions
        ),
        recipeVersionIntegrations=recipe_version_integration_value_object.from_str_array(
            request.recipeVersionIntegrations or []
        ),
        recipeVersionDescription=recipe_version_description_value_object.from_str(request.recipeVersionDescription),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(request.recipeVersionVolumeSize),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateRecipeVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post(
    "/projects/<project_id>/recipes/<recipe_id>/versions/<version_id>",
    tags=[TAG_RECIPE_VERSIONS],
)
def release_recipe_version(
    project_id: str,
    recipe_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.ReleaseRecipeVersionResponse]:
    """Releases a specific recipe version"""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )

    command = release_recipe_version_command.ReleaseRecipeVersionCommand(
        recipeId=recipe_id_value_object.from_str(recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(version_id),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )
    dependencies.command_bus.handle(command)
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ReleaseRecipeVersionResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/recipes/<recipe_id>/versions/<version_id>/test-executions",
    tags=[TAG_RECIPE_TESTING],
)
def get_recipe_version_test_executions(
    project_id: str,
    recipe_id: str,
    version_id: str,
) -> api_gateway.Response[api_model.GetRecipeVersionTestExecutionsResponse]:
    """Lists test executions associated to a specific recipe version."""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )
    dependencies.recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
        recipe_id=recipe_id_value_object.from_str(recipe_id),
        version_id=recipe_version_id_value_object.from_str(version_id),
    )

    recipe_version_test_execution_summaries = (
        dependencies.recipe_version_test_execution_domain_qry_srv.get_recipe_version_test_execution_summaries(
            version_id=recipe_version_id_value_object.from_str(version_id)
        )
    )

    recipe_version_test_execution_summaries_parsed = [
        api_model.RecipeVersionTestExecutionSummary.model_validate(recipe_version_test_execution_summary.model_dump())
        for recipe_version_test_execution_summary in recipe_version_test_execution_summaries
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipeVersionTestExecutionsResponse(
            recipe_version_test_execution_summaries=recipe_version_test_execution_summaries_parsed
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get(
    "/projects/<project_id>/recipes/<recipe_id>/versions/<version_id>/test-executions/<test_execution_id>/logs-url",
    tags=[TAG_RECIPE_TESTING],
)
def get_recipe_version_test_execution_logs_url(
    project_id: str, recipe_id: str, version_id: str, test_execution_id: str
) -> api_gateway.Response[api_model.GetRecipeVersionTestExecutionLogsUrlResponse]:
    """Get logs url a specific recipe version test execution."""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id),
    )
    dependencies.recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
        recipe_id=recipe_id_value_object.from_str(recipe_id),
        version_id=recipe_version_id_value_object.from_str(version_id),
    )

    s3_presigned_url = (
        dependencies.recipe_version_test_execution_domain_qry_srv.get_recipe_version_test_execution_logs_url(
            version_id=recipe_version_id_value_object.from_str(version_id),
            test_execution_id=recipe_version_test_execution_id_value_object.from_str(test_execution_id),
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipeVersionTestExecutionLogsUrlResponse(logs_url=s3_presigned_url),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/pipelines", tags=[TAG_PIPELINES])
def create_pipeline(
    request: api_model.CreatePipelineRequest,
    project_id: str,
) -> api_gateway.Response[api_model.CreatePipelineResponse]:
    """Creates a pipeline."""

    dependencies.recipe_domain_qry_srv.require_recipe_in_project(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(request.recipeId),
    )
    dependencies.recipe_version_domain_qry_srv.require_recipe_version_in_recipe(
        recipe_id=recipe_id_value_object.from_str(request.recipeId),
        version_id=recipe_version_id_value_object.from_str(request.recipeVersionId),
    )

    command = create_pipeline_command.CreatePipelineCommand(
        projectId=project_id_value_object.from_str(project_id),
        buildInstanceTypes=pipeline_build_instance_types_value_object.from_list(request.buildInstanceTypes),
        pipelineDescription=pipeline_description_value_object.from_str(request.pipelineDescription),
        pipelineName=pipeline_name_value_object.from_str(request.pipelineName),
        pipelineSchedule=pipeline_schedule_value_object.from_str(request.pipelineSchedule),
        recipeId=recipe_id_value_object.from_str(request.recipeId),
        recipeVersionId=recipe_version_id_value_object.from_str(request.recipeVersionId),
        createdBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
        productId=(product_id_value_object.from_str(request.productId) if request.productId else None),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreatePipelineResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/pipelines", tags=[TAG_PIPELINES])
def get_pipelines(
    project_id: str,
) -> api_gateway.Response[api_model.GetPipelinesResponse]:
    """Lists pipelines associated to a specific project."""

    pipelines = dependencies.pipeline_domain_qry_srv.get_pipelines(
        project_id=project_id_value_object.from_str(project_id),
    )

    pipelines_parsed = [api_model.Pipeline.model_validate(pipeline.model_dump()) for pipeline in pipelines]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetPipelinesResponse(pipelines=pipelines_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/pipelines/<pipeline_id>", tags=[TAG_PIPELINES])
def get_pipeline(
    project_id: str,
    pipeline_id: str,
) -> api_gateway.Response[api_model.GetPipelineResponse]:
    """Get a specific pipeline."""

    pipeline = dependencies.pipeline_domain_qry_srv.get_pipeline(
        project_id=project_id_value_object.from_str(project_id),
        pipeline_id=pipeline_id_value_object.from_str(pipeline_id),
    )

    pipeline_parsed = api_model.Pipeline.model_validate(pipeline.model_dump())

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetPipelineResponse(pipeline=pipeline_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/pipelines/<pipeline_id>", tags=[TAG_PIPELINES])
def retire_pipeline(
    project_id: str,
    pipeline_id: str,
) -> api_gateway.Response[api_model.RetirePipelineResponse]:
    """Retire a specific pipeline."""

    command = retire_pipeline_command.RetirePipelineCommand(
        projectId=project_id_value_object.from_str(project_id),
        pipelineId=pipeline_id_value_object.from_str(pipeline_id),
        lastUpdateBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
    )

    dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RetirePipelineResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/pipelines/<pipeline_id>", tags=[TAG_PIPELINES])
def update_pipeline(
    request: api_model.UpdatePipelineRequest,
    project_id: str,
    pipeline_id: str,
) -> api_gateway.Response[UpdatePipelineResponse]:
    """Updates a pipeline."""
    kwargs = {}
    if request.pipelineSchedule:
        kwargs["pipelineSchedule"] = pipeline_schedule_value_object.from_str(request.pipelineSchedule)
    if request.buildInstanceTypes:
        kwargs["buildInstanceTypes"] = pipeline_build_instance_types_value_object.from_list(request.buildInstanceTypes)
    if request.recipeVersionId:
        kwargs["recipeVersionId"] = recipe_version_id_value_object.from_str(request.recipeVersionId)
    kwargs["productId"] = product_id_value_object.from_str(request.productId) if request.productId else None
    command = update_pipeline_command.UpdatePipelineCommand(
        projectId=project_id_value_object.from_str(project_id),
        pipelineId=pipeline_id_value_object.from_str(pipeline_id),
        lastUpdatedBy=user_id_value_object.from_str(app.context.get("user_principal").user_name),
        **kwargs,
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdatePipelineResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/recipes-versions", tags=[TAG_RECIPE_VERSIONS])
def get_recipes_versions(
    project_id: str,
    status: str,
) -> api_gateway.Response[api_model.GetRecipesVersionsResponse]:
    """Get all recipe versions given a status"""

    recipes_versions_summary = dependencies.recipe_version_domain_qry_srv.get_all_recipes_versions(
        status=recipe_version_status_value_object.from_str(status),
        project_id=project_id_value_object.from_str(project_id),
    )
    recipes_versions_summary_parsed = [
        api_model.RecipeVersionSummary.model_validate(recipe_version.model_dump())
        for recipe_version in recipes_versions_summary
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetRecipesVersionsResponse(recipes_versions_summary=recipes_versions_summary_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/images", tags=[TAG_IMAGES])
def create_image(
    request: api_model.CreateImageRequest,
    project_id: str,
) -> api_gateway.Response[api_model.CreateImageResponse]:
    """Creates an image."""

    command = create_image_command.CreateImageCommand(
        projectId=project_id_value_object.from_str(project_id),
        pipelineId=pipeline_id_value_object.from_str(request.pipelineId),
    )

    dependencies.command_bus.handle(command=command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CreateImageResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/images", tags=[TAG_IMAGES])
def get_images(
    project_id: str,
) -> api_gateway.Response[GetImagesResponse]:
    """Lists images associated to a specific project."""

    image_source_filter = app.current_event.get_query_string_value(name="imageSource")
    status_filter = app.current_event.get_query_string_value(name="status")

    images = dependencies.image_domain_qry_srv.get_images(
        project_id=project_id_value_object.from_str(project_id),
        image_source=image_source_filter,
        status=status_filter,
    )

    images_parsed = [
        api_model.Image.model_validate({**image.model_dump(), "imageBuildVersion": str(image.imageBuildVersion)})
        for image in images
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetImagesResponse(images=images_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/images/<image_id>", tags=[TAG_IMAGES])
def get_image(
    project_id: str,
    image_id: str,
) -> api_gateway.Response[GetImageResponse]:
    """Get a specific image."""

    image = dependencies.image_domain_qry_srv.get_image(
        project_id=project_id_value_object.from_str(project_id),
        image_id=image_id_value_object.from_str(image_id),
    )

    image_parsed = api_model.Image.model_validate(
        {**image.model_dump(), "imageBuildVersion": str(image.imageBuildVersion)}
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetImageResponse(image=image_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/importable-amis", tags=[TAG_IMAGES])
def list_importable_amis(
    project_id: str,
) -> api_gateway.Response[api_model.ListImportableAmisResponse]:
    """Lists AMIs from the Image Service account that can be imported."""
    all_amis = dependencies.ami_validation_svc.list_available_amis()
    existing_upstream_ids = {
        img.imageUpstreamId
        for img in dependencies.image_domain_qry_srv.get_images(project_id_value_object.from_str(project_id))
        if img.imageUpstreamId
    }
    importable = [
        api_model.ImportableAmi(
            amiId=ami.amiId,
            name=ami.name,
            platform=ami.platform,
            architecture=ami.architecture,
            state=ami.state,
        )
        for ami in all_amis
        if ami.amiId not in existing_upstream_ids
    ]
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ListImportableAmisResponse(amis=importable),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/images/import", tags=[TAG_IMAGES])
def import_image(
    request: api_model.ImportImageRequest,
    project_id: str,
) -> api_gateway.Response[api_model.ImportImageResponse]:
    """Imports an existing or marketplace AMI into VEW."""
    project_id_value = project_id_value_object.from_str(project_id)
    image_source = image_source_value_object.from_str(request.imageSource)
    ami_id = ami_id_value_object.from_str(request.amiId)

    marketplace_product_code = None
    license_configuration_arn = None
    subscription_ownership = None
    regional_ami_ids = None
    home_region = None
    license_grant_allowed = False
    marketplace_listing_id = None

    if image_source.value == ImageSource.AWS_PUBLISHED_AMI:
        # Only the listing is taken from the caller. The command handler
        # resolves it again and derives the rest of the metadata from the AMI.
        marketplace_listing_id = request.marketplaceMetadata.listingId if request.marketplaceMetadata else None

    if image_source.value == ImageSource.MARKETPLACE_PRODUCT:
        requested_metadata = request.marketplaceMetadata
        if not requested_metadata:
            raise domain_exception.DomainException(
                "marketplaceMetadata with productCode is required for MARKETPLACE_PRODUCT."
            )

        subscriptions = dependencies.marketplace_subscription_qry_svc.discover(project_id=project_id_value)
        matching_subscriptions = [
            subscription
            for subscription in subscriptions
            if (
                subscription.hubRegionAmiId == ami_id.value
                and subscription.productCode == requested_metadata.productCode
            )
        ]
        if len(matching_subscriptions) != 1:
            raise domain_exception.DomainException(
                "Marketplace subscription is unavailable or no longer matches "
                f"AMI {ami_id.value} and product code {requested_metadata.productCode}. "
                "Refresh Marketplace subscriptions and try again."
            )

        subscription = matching_subscriptions[0]
        ami_id = ami_id_value_object.from_str(subscription.hubRegionAmiId)
        marketplace_product_code = product_code_value_object.from_str(subscription.productCode)
        license_configuration_arn = subscription.licenseConfigurationArn
        subscription_ownership = SubscriptionOwnership(subscription.subscriptionOwnership)
        regional_ami_ids = subscription.regionalAmiIds
        home_region = subscription.homeRegion
        license_grant_allowed = subscription.licenseGrantAllowed

    command = import_image_command.ImportImageCommand(
        projectId=project_id_value,
        imageSource=image_source,
        amiId=ami_id,
        imageName=image_name_value_object.from_str(request.imageName),
        imageDescription=request.imageDescription,
        platform=platform_value_object.from_str(request.platform),
        osVersion=os_version_value_object.from_str(request.osVersion),
        componentVersionDetails=[
            c.model_dump() if hasattr(c, "model_dump") else c for c in (request.componentVersionDetails or [])
        ],
        marketplaceProductCode=marketplace_product_code,
        licenseConfigurationArn=license_configuration_arn,
        subscriptionOwnership=subscription_ownership,
        marketplaceListingId=marketplace_listing_id,
        regionalAmiIds=regional_ami_ids,
        homeRegion=home_region,
        licenseGrantAllowed=license_grant_allowed,
        imageServiceAccountId=dependencies.image_service_account_id,
    )

    image_id = dependencies.command_bus.handle(command)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ImportImageResponse(
            imageId=image_id,
            imageSource=request.imageSource,
            amiId=request.amiId,
            status="CREATED",
            createDate=datetime.now(timezone.utc).isoformat(),
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/marketplace/subscriptions", tags=[TAG_IMAGES])
def discover_marketplace_subscriptions(
    project_id: str,
) -> api_gateway.Response[api_model.DiscoverMarketplaceSubscriptionsResponse]:
    """Discovers active Marketplace subscriptions in the hub account."""
    subscriptions = dependencies.marketplace_subscription_qry_svc.discover(
        project_id=project_id_value_object.from_str(project_id),
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.DiscoverMarketplaceSubscriptionsResponse(
            subscriptions=[
                api_model.DiscoveredMarketplaceSubscription.model_validate(s.model_dump()) for s in subscriptions
            ],
            discoveredAt=datetime.now(timezone.utc).isoformat(),
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/images/aws-published/resolve", tags=[TAG_IMAGES])
def resolve_aws_published_ami(
    request: api_model.ResolveAwsPublishedAmiRequest,
    project_id: str,
) -> api_gateway.Response[api_model.ResolveAwsPublishedAmiResponse]:
    """Resolves an AWS-published Marketplace listing to the AMI(s) to import.

    Read-only. Returns 400 when the listing references more than one product
    and when no AMI can be identified for the product. When ``unambiguous``
    is false the caller must let the user pick from ``candidates``; nothing
    is guessed.
    """
    result = dependencies.aws_published_ami_qry_svc.resolve_listing(
        project_id=project_id_value_object.from_str(project_id),
        listing_id=request.listingId,
    )
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ResolveAwsPublishedAmiResponse.model_validate(result.model_dump()),
        content_type=content_types.APPLICATION_JSON,
    )


# --- In-VEW Marketplace procurement endpoints ---


@app.get("/projects/<project_id>/marketplace/purchase-options", tags=[TAG_MARKETPLACE])
def list_marketplace_purchase_options(
    project_id: str,
) -> api_gateway.Response[api_model.ListPurchaseOptionsResponse]:
    """List AWS Marketplace AMI purchase options available to this VEW."""
    project_id_value_object.from_str(project_id)
    options = dependencies.marketplace_offer_discovery_svc.list_purchase_options()
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ListPurchaseOptionsResponse(
            purchaseOptions=[api_model.MarketplacePurchaseOptionResponseItem(**o.model_dump()) for o in options]
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@app.get("/projects/<project_id>/marketplace/offers/<offer_id>", tags=[TAG_MARKETPLACE])
def get_marketplace_offer(
    project_id: str,
    offer_id: str,
) -> api_gateway.Response[api_model.GetMarketplaceOfferResponse]:
    """Return full offer detail (proposal, seller, pricing, associated products) and
    every attached term so the buyer UI can render a quote-review page.
    """
    project_id_value_object.from_str(project_id)
    offer_id_vo = offer_id_value_object.from_str(offer_id)
    offer = dependencies.marketplace_offer_discovery_svc.get_offer(offer_id_vo.value)
    terms = dependencies.marketplace_offer_discovery_svc.get_offer_terms(offer_id_vo.value)
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetMarketplaceOfferResponse(
            offerId=offer.offerId,
            catalog=offer.catalog,
            offerName=offer.offerName,
            agreementProposalId=offer.agreementProposalId,
            sellerOfRecordDisplayName=offer.sellerOfRecordDisplayName,
            sellerOfRecordProfileId=offer.sellerOfRecordProfileId,
            pricingModelType=offer.pricingModelType,
            pricingModelDisplayName=offer.pricingModelDisplayName,
            expirationTime=offer.expirationTime,
            availableFromTime=offer.availableFromTime,
            associatedProducts=[
                api_model.MarketplaceOfferProductAssociationResponseItem(**p.model_dump())
                for p in offer.associatedProducts
            ],
            terms=[api_model.MarketplaceOfferTermResponseItem(**t.model_dump()) for t in terms],
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@app.post("/projects/<project_id>/marketplace/offers/<offer_id>/quotes", tags=[TAG_MARKETPLACE])
def create_marketplace_quote(
    project_id: str,
    offer_id: str,
    request: api_model.CreateAgreementRequestRequest,
) -> api_gateway.Response[api_model.CreateAgreementRequestResponse]:
    """Create a Marketplace agreement request (the buyer's quote). Returns
    the short-lived ``agreementRequestId`` the caller confirms via the
    ``.../accept`` endpoint.
    """
    command = create_agreement_request_command.CreateAgreementRequestCommand(
        projectId=project_id_value_object.from_str(project_id),
        offerId=offer_id_value_object.from_str(offer_id),
        requestedTerms=request.requestedTerms,
        clientToken=request.clientToken,
    )
    quote = dependencies.command_bus.handle(command=command)
    charge = quote.chargeSummary
    return api_gateway.Response(
        status_code=HTTPStatus.CREATED,
        body=api_model.CreateAgreementRequestResponse(
            agreementRequestId=quote.agreementRequestId,
            # Serialised as strings: AWS returns these as BoundedString and
            # a JSON number would risk a float round-trip on money. All
            # three are None for usage-based pricing, where AWS has no
            # up-front total.
            estimatedAgreementValue=(
                str(charge.newAgreementValue) if charge and charge.newAgreementValue is not None else None
            ),
            estimatedAgreementValueAfterTax=(
                str(charge.newAgreementValueAfterTax)
                if charge and charge.newAgreementValueAfterTax is not None
                else None
            ),
            estimatedCurrencyCode=charge.currencyCode if charge else None,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@app.post(
    "/marketplace/quotes/<agreement_request_id>/accept",
    tags=[TAG_MARKETPLACE],
)
def accept_marketplace_quote(
    agreement_request_id: str,
) -> api_gateway.Response[api_model.AcceptAgreementRequestResponse]:
    """Confirm a previously created agreement request. Returns the durable
    ``agreementId`` under which the buyer's subscription now lives.

    Account-scoped: accepting a quote commits the buyer *account* to an AWS
    Marketplace agreement, so the route carries no ``projectId``; see
    ``cancel_marketplace_agreement`` for the authorization model.
    """
    command = accept_agreement_request_command.AcceptAgreementRequestCommand(
        agreementRequestId=agreement_request_id_value_object.from_str(agreement_request_id),
    )
    agreement_id = dependencies.command_bus.handle(command=command)
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.AcceptAgreementRequestResponse(agreementId=agreement_id),
        content_type=content_types.APPLICATION_JSON,
    )


@app.delete(
    "/marketplace/agreements/<agreement_id>",
    tags=[TAG_MARKETPLACE],
)
def cancel_marketplace_agreement(
    agreement_id: str,
) -> api_gateway.Response[api_model.CancelAgreementResponse]:
    """Cancel an active Marketplace agreement.

    Account-scoped, not project-scoped: a Marketplace agreement is an
    account-level AWS resource. The buyer account holds one set of
    subscriptions and AWS exposes no project dimension on them, so there is
    no project that owns a given agreement and no project to authorize
    against. Authorization is a platform-level check (admin of at least one
    project), the same for accept, list and cancel.
    """
    command = cancel_agreement_command.CancelAgreementCommand(
        agreementId=agreement_id_value_object.from_str(agreement_id),
    )
    dependencies.command_bus.handle(command=command)
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.CancelAgreementResponse(agreementId=agreement_id),
        content_type=content_types.APPLICATION_JSON,
    )


@app.get(
    "/marketplace/agreements",
    tags=[TAG_MARKETPLACE],
)
@tracer.capture_method
def list_marketplace_agreements() -> api_gateway.Response[api_model.ListMarketplaceAgreementsResponse]:
    """List the buyer account's active AWS Marketplace agreements (AMI-only).

    Account-scoped: it returns every active AMI agreement in the buyer AWS
    account, because a Marketplace agreement has no project dimension to
    filter by. The route therefore carries no ``projectId``, and
    authorization is the platform-level check described on
    ``cancel_marketplace_agreement``.

    Uses ``AwsMarketplaceDiscoveryService.list_active_agreements()``. The
    AMI-only invariant is enforced inside the adapter after the call,
    because SearchAgreements rejects a ``ResourceType`` filter combined
    with ``Status``.

    Each row is enriched with human-readable ``productName``,
    ``offerName``, and ``pricingModelType`` via one ``GetOffer`` call per
    agreement (the offer response also carries the associated product's
    name, so a separate ``GetProduct`` call is not needed). Enrichment is
    best-effort: any per-row failure yields ``None`` for the enrichment
    fields but the row still appears in the response so the UI can fall
    back to showing raw IDs.
    """
    agreements = dependencies.marketplace_discovery_svc.list_active_agreements()

    enriched_items: list[api_model.MarketplaceAgreementResponseItem] = []
    for a in agreements:
        product_name: str | None = None
        offer_name: str | None = None
        pricing_model_type: str | None = None
        try:
            offer = dependencies.marketplace_offer_discovery_svc.get_offer(a.offerId)
            offer_name = offer.offerName
            pricing_model_type = offer.pricingModelType
            # The offer response carries the associated products' names —
            # find the association whose productId matches this agreement's
            # productId and use its productName. Falls back to the first
            # association's name if no direct match (rare: the AMI-only guard
            # rejects multi-product offers at quote time, so agreements
            # created through VEW are single-product).
            match = next(
                (p for p in offer.associatedProducts if p.productId == a.productId),
                offer.associatedProducts[0] if offer.associatedProducts else None,
            )
            product_name = match.productName if match else None
        except Exception as e:
            logger.warning(
                "Enrichment failed for agreement %s (offer %s): %s — falling back to raw IDs",
                a.agreementId,
                a.offerId,
                e,
            )

        enriched_items.append(
            api_model.MarketplaceAgreementResponseItem(
                agreementId=a.agreementId,
                productId=a.productId,
                offerId=a.offerId,
                status=a.status,
                acceptanceDate=a.acceptanceDate,
                productName=product_name,
                offerName=offer_name,
                pricingModelType=pricing_model_type,
            )
        )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ListMarketplaceAgreementsResponse(agreements=enriched_items),
        content_type=content_types.APPLICATION_JSON,
    )


# --- Public catalog browse endpoints (marketplace-discovery.SearchListings) ---


@app.get(
    "/projects/<project_id>/marketplace/listings",
    tags=[TAG_MARKETPLACE],
)
@tracer.capture_method
def search_marketplace_listings(
    project_id: str,
    search_text: Annotated[str | None, Query(alias="searchText")] = None,
    category: Annotated[list[str] | None, Query(alias="category")] = None,
    pricing_model: Annotated[list[str] | None, Query(alias="pricingModel")] = None,
    publisher: Annotated[list[str] | None, Query(alias="publisher")] = None,
    rating: Annotated[list[str] | None, Query(alias="rating")] = None,
    next_token: Annotated[str | None, Query(alias="nextToken")] = None,
    max_results: Annotated[int | None, Query(alias="maxResults")] = None,
) -> api_gateway.Response[api_model.SearchMarketplaceListingsResponse]:
    """Search the AWS Marketplace public catalog for AMI listings.

    Hard-locks ``FULFILLMENT_OPTION_TYPE=AMAZON_MACHINE_IMAGE`` and
    ``NUMBER_OF_PRODUCTS=SINGLE_PRODUCT`` server-side. Additional facet
    filters (category, pricing model, publisher, rating) are optional
    and pass through from the query string.
    """
    project_id_value_object.from_str(project_id)
    result = dependencies.marketplace_listing_discovery_svc.search_listings(
        search_text=search_text,
        category_filters=category,
        pricing_model_filters=pricing_model,
        publisher_filters=publisher,
        rating_filters=rating,
        next_token=next_token,
        max_results=max_results if max_results is not None else 25,
    )
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.SearchMarketplaceListingsResponse(
            listings=[
                api_model.MarketplaceListingSummaryItem.model_validate(li.model_dump()) for li in result.listings
            ],
            nextToken=result.nextToken,
            totalResults=result.totalResults,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@app.get(
    "/projects/<project_id>/marketplace/listings/<listing_id>",
    tags=[TAG_MARKETPLACE],
)
@tracer.capture_method
def get_marketplace_listing(
    project_id: str,
    listing_id: str,
) -> api_gateway.Response[api_model.GetMarketplaceListingResponse]:
    """Return full detail for a single Marketplace listing.

    Response includes ``primaryOfferId`` which the frontend hands off to
    the procurement wizard (``initialOfferId`` prop)
    to skip the browse-offers step and land the user on the
    review-terms page.
    """
    project_id_value_object.from_str(project_id)
    detail = dependencies.marketplace_listing_discovery_svc.get_listing(listing_id)
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetMarketplaceListingResponse.model_validate(detail.model_dump()),
        content_type=content_types.APPLICATION_JSON,
    )


@app.get(
    "/projects/<project_id>/marketplace/facets",
    tags=[TAG_MARKETPLACE],
)
@tracer.capture_method
def get_marketplace_facets(
    project_id: str,
) -> api_gateway.Response[api_model.GetMarketplaceFacetsResponse]:
    """Return the filter facets available on the AMI browse surface
    (Category, Pricing model, Publisher, Rating) with their value counts.

    Used by the browse UI to render the filter sidebar. Facets not
    useful for AMI-only browsing (PRICING_UNIT, DEPLOYED_ON_AWS,
    NUMBER_OF_PRODUCTS) are dropped by the adapter.
    """
    project_id_value_object.from_str(project_id)
    facet_set = dependencies.marketplace_listing_discovery_svc.search_facets()
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetMarketplaceFacetsResponse(
            facets={
                name: [api_model.MarketplaceFacetValueItem(**v.model_dump()) for v in values]
                for name, values in facet_set.facets.items()
            },
            totalResults=facet_set.totalResults,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/allowed-build-instance-types", tags=[TAG_PIPELINES])
def get_pipelines_allowed_build_types(
    project_id: str,
    recipe_id: Annotated[list[str] | None, Query(alias="recipeId")] = None,
) -> api_gateway.Response[api_model.GetPipelinesAllowedBuildTypesResponse]:
    """Lists all allowed build types for a certain recipe architecture chosen for the pipeline."""

    recipe = dependencies.recipe_domain_qry_srv.get_recipe(
        project_id=project_id_value_object.from_str(project_id),
        recipe_id=recipe_id_value_object.from_str(recipe_id.pop() if recipe_id else None),
    )

    recipe_parsed = api_model.Recipe.model_validate(recipe.model_dump())
    allowed_build_types = dependencies.pipeline_srv.get_pipeline_allowed_build_instance_types(
        architecture=recipe_parsed.recipeArchitecture
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetPipelinesAllowedBuildTypesResponse(pipelines_allowed_build_types=allowed_build_types),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@exception_handler.handle_exceptions(user_exceptions=[domain_exception.DomainException], cors_config=cors_config)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.ByAPI: "RestAPI"},
    enable_audit=True,
    region_name=default_region_name,
    secret_name=secret_name,
)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    logger.info(clear_auth_headers(event))
    return app.resolve(event, context)
