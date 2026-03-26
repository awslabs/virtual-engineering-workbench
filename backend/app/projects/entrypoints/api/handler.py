import json
from http import HTTPStatus
from urllib.parse import unquote

from aws_lambda_powertools import logging, tracing
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.openapi.models import Server
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.shared.types import Annotated
from aws_lambda_powertools.utilities import typing
from aws_xray_sdk.core import patch_all

from app.projects.domain.commands.enrolments import (
    approve_enrolments_command,
    enrol_user_to_program_command,
    reject_enrolments_command,
)
from app.projects.domain.commands.project_accounts import (
    activate_project_account_command,
    deactivate_project_account_command,
    on_board_project_account_command,
    reonboard_project_account_command,
)
from app.projects.domain.commands.projects import (
    create_project_command,
    update_project_command,
)
from app.projects.domain.commands.technologies import (
    add_technology,
    delete_technology_command,
    update_technology_command,
)
from app.projects.domain.commands.users import (
    assign_user_command,
    reassign_user_command,
    unassign_user_command,
)
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import enrolment, project_account, project_assignment
from app.projects.domain.value_objects import (
    account_description_value_object,
    account_id_value_object,
    account_name_value_object,
    account_status_value_object,
    account_technology_id_value_object,
    account_type_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
    source_system_value_object,
    tech_id_value_object,
    user_email_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.projects.entrypoints.api import bootstrapper, config
from app.projects.entrypoints.api.model import api_model
from app.shared.adapters.boto import paging_utils
from app.shared.logging.helpers import clear_auth_headers
from app.shared.middleware import authorization, exception_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig(**config.config)
default_region_name = app_config.get_default_region()
secret_name = app_config.get_audit_logging_key_name()

cors_config = api_gateway.CORSConfig(**app_config.cors_config)
app = api_gateway.APIGatewayRestResolver(
    cors=cors_config,
    strip_prefixes=(app_config.get_strip_prefixes() if app_config.get_custom_dns_name() else []),
    enable_validation=True,
)
app.use(middlewares=[authorization.require_auth_context])
app.enable_swagger(
    path="/_swagger",
    title="Projects BC API",
    servers=[Server(url=f"{app_config.get_api_base_path()}")],
)

logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger)


@tracer.capture_method
@app.get("/projects")
def get_projects(
    page_size: Annotated[list[int] | None, Query(alias="pageSize")] = [10],
    next_token_str: Annotated[list[str | None] | None, Query(alias="nextToken")] = None,
) -> api_gateway.Response[api_model.GetProjectsResponse]:
    """Returns a list of all projects with paging."""

    user_principal_name = app.context.get("user_principal").user_name.upper()
    next_token = next_token_str.pop() if next_token_str else None

    projects, last_evaluated_key, assignments = dependencies.projects_query_service.list_projects(
        page_size=page_size.pop() if page_size else 10,
        next_token=json.loads(next_token) if next_token else None,
        user_id=user_principal_name,
    )

    enrolments, last_evaluated_key = dependencies.enrolment_query_service.list_enrolments_by_user(
        user_id=user_principal_name,
        page_size=50,
        next_token=None,
        status=enrolment.EnrolmentStatus.Pending,
    )

    projects_parsed = [api_model.Project.parse_obj(p.dict()) for p in projects]
    assignments_parsed = [api_model.ProjectAssignment.parse_obj(a.dict()) for a in assignments]
    enrolments_parsed = [api_model.ProjectEnrolment.parse_obj(e.dict()) for e in enrolments]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProjectsResponse(
            projects=projects_parsed,
            nextToken=last_evaluated_key,
            assignments=assignments_parsed,
            enrolments=enrolments_parsed,
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects")
def create_project(
    request: api_model.CreateProjectRequest,
) -> api_gateway.Response[api_model.CreateProjectResponse]:
    """Creates a new project."""
    user_principal_name = app.context.get("user_principal").user_name.upper()
    user_id = user_id_value_object.from_str(user_principal_name)

    project_id = dependencies.command_bus.handle(
        create_project_command.CreateProjectCommand(
            name=request.name,
            description=request.description,
            isActive=request.isActive,
        )
    )

    dependencies.command_bus.handle(
        assign_user_command.AssignUserCommand(
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id,
            roles=[user_role_value_object.from_str(project_assignment.Role.ADMIN.value)],
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.CREATED,
        body=api_model.CreateProjectResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>")
def get_project(
    project_id: str,
) -> api_gateway.Response[api_model.GetProjectResponse]:
    """Returns a project."""

    project = dependencies.projects_query_service.get_project_by_id(id=project_id)
    project_parsed = api_model.Project.parse_obj(project.dict())

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProjectResponse(project=project_parsed),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>")
def update_project(
    request: api_model.UpdateProjectRequest,
    project_id: str,
) -> api_gateway.Response[api_model.UpdateProjectResponse]:
    """Updates a project."""

    dependencies.command_bus.handle(
        update_project_command.UpdateProjectCommand(
            id=project_id_value_object.from_str(project_id),
            name=request.name,
            description=request.description,
            isActive=request.isActive,
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateProjectResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/accounts")
def get_project_accounts(
    project_id: str,
    account_type: Annotated[list[str] | None, Query(alias="accountType")] = None,
    stage: Annotated[list[str] | None, Query(alias="stage")] = None,
) -> api_gateway.Response[api_model.GetProjectAccountsResponse]:
    """Returns a list of project accounts. Clients can filter returned accounts per account type and/or stage."""

    project_accounts = dependencies.projects_query_service.list_project_accounts(
        project_id=project_id,
        account_type=account_type.pop() if account_type else None,
        stage=stage.pop() if stage else None,
    )
    project_accounts_parsed = [api_model.ProjectAccount.parse_obj(p) for p in project_accounts]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProjectAccountsResponse(projectAccounts=project_accounts_parsed, nextToken=None),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/accounts")
def onboard_project_account(
    request: api_model.OnBoardProjectAccountRequest,
    project_id: str,
) -> api_gateway.Response[api_model.OnBoardProjectAccountResponse]:
    """Starts AWS account on-boarding"""

    # TODO use value object pattern for stage values
    dependencies.command_bus.handle(
        on_board_project_account_command.OnBoardProjectAccountCommand(
            account_id=aws_account_id_value_object.from_str(request.awsAccountId),
            account_type=account_type_value_object.from_str(request.accountType),
            account_name=account_name_value_object.from_str(request.accountName),
            account_description=account_description_value_object.from_str(request.accountDescription),
            project_id=project_id_value_object.from_str(project_id),
            stage=request.stage,
            technology=account_technology_id_value_object.from_str(request.technologyId),
            region=region_value_object.from_str(request.region),
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.OnBoardProjectAccountResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/accounts")
def reonboard_project_account(
    request: api_model.ReonboardProjectAccountRequest,
    project_id: str,
) -> api_gateway.Response[api_model.ReonboardProjectAccountResponse]:
    """Restarts accounts onboarding"""
    for account_id in request.accountIds:
        dependencies.command_bus.handle(
            reonboard_project_account_command.ReonboardProjectAccountCommand(
                project_id=project_id_value_object.from_str(project_id),
                account_id=account_id_value_object.from_str(account_id),
            )
        )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ReonboardProjectAccountResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.patch("/projects/<project_id>/accounts/<account_id>")
def update_project_account(
    request: api_model.UpdateProjectAccountRequest,
    project_id: str,
    account_id: str,
) -> api_gateway.Response[api_model.UpdateProjectAccountResponse]:
    """Change project account
    Support changes:
    accountStatus: 'Active' | 'Inactive'
    """
    target_account_status = account_status_value_object.from_value_str(request.accountStatus)

    if target_account_status.value == project_account.ProjectAccountStatusEnum.Active:
        dependencies.command_bus.handle(
            activate_project_account_command.ActivateProjectAccountCommand(
                account_id=account_id_value_object.from_str(account_id),
                project_id=project_id_value_object.from_str(project_id),
                account_status=target_account_status,
            )
        )

    if target_account_status.value == project_account.ProjectAccountStatusEnum.Inactive:
        dependencies.command_bus.handle(
            deactivate_project_account_command.DeactivateProjectAccountCommand(
                account_id=account_id_value_object.from_str(account_id),
                project_id=project_id_value_object.from_str(project_id),
                account_status=target_account_status,
            )
        )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateProjectAccountResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/users")
def assign_project_user(
    request: api_model.AssignUserRequest,
    project_id: str,
) -> api_gateway.Response[api_model.AssignUserResponse]:
    """Assigns user to a project"""

    dependencies.command_bus.handle(
        assign_user_command.AssignUserCommand(
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id_value_object.from_str(request.userId),
            roles=[user_role_value_object.from_str(role) for role in request.roles or []],
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.AssignUserResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/users")
def get_project_users(
    project_id: str,
) -> api_gateway.Response[api_model.GetProjectAssignmentsResponse]:
    """Returns a list of project assignments with paging."""

    assignments = dependencies.projects_query_service.list_users_by_project(
        project_id=project_id,
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProjectAssignmentsResponse(
            assignments=[api_model.GetProjectAssignmentsResponseItem.parse_obj(a.dict()) for a in assignments],
        ),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/users/<user_id>")
def unassign_project_user(
    project_id: str,
    user_id: str,
) -> api_gateway.Response[api_model.UnAssignUserResponse]:
    """Removes user from a project"""

    cmd = unassign_user_command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str(project_id),
        user_ids=[user_id_value_object.from_str(user_id)],
    )
    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UnAssignUserResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/users")
def remove_project_users(
    request: api_model.RemoveUsersRequest, project_id: str
) -> api_gateway.Response[api_model.RemoveUsersResponse]:
    """Removes multiple users from a project/program"""

    user_ids = [user_id_value_object.from_str(user_id) for user_id in request.userIds]

    cmd = unassign_user_command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str(project_id),
        user_ids=user_ids,
    )
    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.RemoveUsersResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/users")
def reassign_project_user(
    request: api_model.ReAssignUsersRequest,
    project_id: str,
) -> api_gateway.Response[api_model.ReAssignUsersResponse]:
    """Reassigns users to a project"""

    user_principal_name = app.context.get("user_principal").user_name.upper()

    dependencies.command_bus.handle(
        reassign_user_command.ReAssignUserCommand(
            project_id=project_id_value_object.from_str(project_id),
            user_ids=[user_id_value_object.from_str(user_id) for user_id in request.userIds or []],
            initiating_user_id=user_id_value_object.from_str(user_principal_name),
            roles=[user_role_value_object.from_str(role) for role in request.roles or []],
        )
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.ReAssignUsersResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/users/<user_id>")
def get_user_roles(
    project_id: str,
    user_id: str,
) -> api_gateway.Response[api_model.GetUserRolesResponse]:
    """Returns a list of roles assigned to a user for a project."""

    project_assignment = dependencies.projects_query_service.get_user_assignment(
        project_id=project_id,
        user_id=user_id,
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetUserRolesResponse(roles=project_assignment.roles),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/technologies")
def list_technologies_for_project(
    project_id: str,
    page_size: Annotated[list[int] | None, Query(alias="pageSize")] = [0],
) -> api_gateway.Response[api_model.GetTechnologiesResponse]:
    """List all technologies for a given project/program"""

    techs = dependencies.technologies_query_service.list_technologies(
        project_id=project_id, page_size=page_size.pop() if page_size else 0
    )

    techs_response = [api_model.Technology.parse_obj(t) for t in techs]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetTechnologiesResponse(technologies=techs_response),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/technologies")
def add_technology_to_project(
    request: api_model.AddTechnologyRequest,
    project_id: str,
) -> api_gateway.Response[api_model.AddTechnologyResponse]:
    """Add a technology to a given project/program"""
    cmd = add_technology.AddTechnologyCommand(
        name=request.name,
        description=request.description,
        project_id=project_id_value_object.from_str(project_id),
    )
    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.AddTechnologyResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/technologies/<tech_id>")
def update_technology(
    request: api_model.UpdateTechnologyRequest,
    project_id: str,
    tech_id: str,
) -> api_gateway.Response[api_model.UpdateTechnologyResponse]:
    """Update name/description of a technology of a given project/program"""
    cmd = update_technology_command.UpdateTechnologyCommand(
        id=tech_id_value_object.from_str(tech_id),
        name=request.name,
        description=request.description,
        project_id=project_id_value_object.from_str(project_id),
    )
    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateTechnologyResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.delete("/projects/<project_id>/technologies/<tech_id>")
def delete_technology(
    project_id: str,
    tech_id: str,
) -> api_gateway.Response[api_model.DeleteTechnologyResponse]:
    """Delete a technology"""
    cmd = delete_technology_command.DeleteTechnologyCommand(
        id=tech_id_value_object.from_str(tech_id),
        project_id=project_id_value_object.from_str(project_id),
    )
    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.DeleteTechnologyResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.post("/projects/<project_id>/enrolments")
def enrol_user_to_project(
    request: api_model.EnrolUserRequest, project_id: str
) -> api_gateway.Response[api_model.EnrolUserResponse]:
    """Enrol a user to a given project/program"""

    user_principal_name = app.context.get("user_principal").user_name.upper()
    user_principal_email = app.context.get("user_principal").user_email

    cmd = enrol_user_to_program_command.EnrolUserToProgramCommand(
        project_id=project_id_value_object.from_str(project_id),
        user_id=user_id_value_object.from_str(user_principal_name),
        user_email=user_email_value_object.from_str(user_principal_email),
        source_system=source_system_value_object.from_str("VEW"),
    )

    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.EnrolUserResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.put("/projects/<project_id>/enrolments")
def update_enrolments_by_project(
    request: api_model.UpdateEnrolmentsRequest, project_id: str
) -> api_gateway.Response[api_model.UpdateEnrolmentsResponse]:
    """Update enrolments attributes for given project"""

    user_principal_name = app.context.get("user_principal").user_name.upper()

    if request.status == enrolment.EnrolmentStatus.Rejected:
        cmd = reject_enrolments_command.RejectEnrolmentsCommand(
            project_id=project_id,
            enrolment_ids=request.enrolmentIds or [],
            reason=request.reason or "",
            rejecter_id=user_id_value_object.from_str(user_principal_name),
        )
    else:
        cmd = approve_enrolments_command.ApproveEnrolmentsCommand(
            project_id=project_id,
            enrolment_ids=request.enrolmentIds or [],
            approver_id=user_id_value_object.from_str(user_principal_name),
        )

    dependencies.command_bus.handle(cmd)

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.UpdateEnrolmentsResponse(),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/projects/<project_id>/enrolments")
def list_enrolments_by_project(
    project_id: str,
    page_size: Annotated[list[int] | None, Query(alias="pageSize")] = [10],
    next_token_str: Annotated[list[str | None] | None, Query(alias="nextToken")] = None,
    status: Annotated[list[str] | None, Query(alias="status")] = None,
) -> api_gateway.Response[api_model.GetProjectEnrolmentsResponse]:
    """List all enrolments for a given project/program"""

    next_token = next_token_str.pop() if next_token_str else None

    enrolments, token = dependencies.enrolment_query_service.list_enrolments_by_project(
        project_id=project_id,
        page_size=page_size.pop() if page_size else 10,
        next_token=json.loads(next_token) if next_token else None,
        status=status.pop() if status else None,
    )

    enrolments_response = [
        api_model.GetProjectEnrolmentsResponseItem.parse_obj(enrolment_item) for enrolment_item in enrolments
    ]

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetProjectEnrolmentsResponse(nextToken=token, enrolments=enrolments_response),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/internal/accounts")
def get_project_accounts_internal() -> dict:
    """Returns a list of project accounts."""
    last_evaluated_key = None

    project_id = app.current_event.get_query_string_value("projectId")
    account_type = app.current_event.get_query_string_value("accountType")
    account_stage = app.current_event.get_query_string_value("stage")
    technology_id = app.current_event.get_query_string_value("technologyId")

    page_size = int(app.current_event.get_query_string_value("pageSize") or 10)
    next_token = app.current_event.get_query_string_value("nextToken")

    if project_id:
        project_accounts = dependencies.projects_query_service.list_project_accounts(
            project_id=project_id,
            account_type=account_type,
            stage=account_stage,
            technology_id=technology_id,
        )
    else:
        project_accounts, last_evaluated_key = dependencies.projects_query_service.list_all_accounts(
            page_size=page_size,
            next_token=json.loads(next_token) if next_token else None,
            account_type=account_type,
            stage=account_stage,
            technology_id=technology_id,
        )

    project_accounts_parsed = [api_model.ProjectAccount.parse_obj(p.dict()) for p in project_accounts]
    return api_model.GetProjectAccountsResponse(
        projectAccounts=project_accounts_parsed, nextToken=last_evaluated_key
    ).dict()


@tracer.capture_method
@app.get("/internal/projects")
def get_project_internal() -> dict:
    """Returns a list of projects."""
    page_size = int(app.current_event.get_query_string_value("pageSize"))
    next_token = app.current_event.get_query_string_value("nextToken")

    projects, last_evaluated_key, assignments = dependencies.projects_query_service.list_projects(
        page_size=page_size,
        next_token=next_token,
        user_id=None,
    )

    projects_parsed = [api_model.Project.parse_obj(p.dict()) for p in projects]
    response = api_model.GetProjectsResponse(projects=projects_parsed, nextToken=last_evaluated_key, assignments=None)
    return response.dict()


@tracer.capture_method
@app.get("/internal/projects/<project_id>/users")
def get_project_assignments_internal(
    project_id: str,
    page_size: Annotated[list[int] | None, Query(alias="pageSize")] = None,
    next_token: Annotated[list[str | None] | None, Query(alias="nextToken")] = None,
) -> dict:
    """Returns a list of project assignments."""

    assignments = []
    assignments_response = None
    if page_size:
        assignments_response = dependencies.projects_query_service.list_users_by_project_paged(
            project_id=project_id,
            page=paging_utils.PageInfo(
                page_size=page_size.pop(),
                page_token=(json.loads(unquote(next_token.pop())) if next_token else None),
            ),
        )
        assignments = assignments_response.items
    else:
        assignments = dependencies.projects_query_service.list_users_by_project(
            project_id=project_id,
        )

    response = api_model.GetProjectAssignmentsResponse(
        assignments=[api_model.GetProjectAssignmentsResponseItem.parse_obj(a.dict()) for a in assignments],
        nextToken=(
            json.dumps(assignments_response.page_token)
            if assignments_response and assignments_response.page_token
            else None
        ),
    )
    return response.dict()


@tracer.capture_method
@app.get("/internal/projects/<project_id>/users/<user_id>")
def get_project_user_assignment_internal(
    project_id: str, user_id: str
) -> api_gateway.Response[api_model.GetProjectAssignmentResponse]:
    """Returns a list of project assignments."""

    assignment = dependencies.projects_query_service.get_user_assignment(project_id=project_id, user_id=user_id.upper())

    response = api_model.GetProjectAssignmentResponse(
        assignment=(api_model.GetProjectAssignmentResponseItem.parse_obj(assignment) if assignment else None)
    )

    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=response,
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_method
@app.get("/internal/user/assignments")
def get_user_assignments_internal() -> dict:
    """Returns a list of user projects and assignments."""
    page_size = int(app.current_event.get_query_string_value("pageSize"))
    next_token = app.current_event.get_query_string_value("nextToken")
    user_id = app.current_event.get_query_string_value("userId")

    projects, last_evaluated_key, assignments = dependencies.projects_query_service.list_projects_by_user(
        page_size=page_size,
        next_token=next_token,
        user_id=user_id,
    )

    projects_parsed = [api_model.Project.parse_obj(p.dict()) for p in projects]
    assignments_parsed = [api_model.ProjectAssignment.parse_obj(a.dict()) for a in assignments]
    response = api_model.GetProjectsResponse(
        projects=projects_parsed,
        nextToken=last_evaluated_key,
        assignments=assignments_parsed,
    )
    return response.dict()


@tracer.capture_method
@app.get("/internal/user")
def get_user() -> dict:
    """Returns a list of user projects and assignments."""
    user_id = app.current_event.get_query_string_value("userId")

    user_entity = dependencies.projects_query_service.get_user(user_id=user_id)
    user_response = api_model.User.parse_obj(user_entity.dict())
    response = api_model.GetUserResponse(user=user_response)
    return response.dict()


@tracer.capture_method
@app.get("/internal/users")
def get_all_users_internal(
    page_size: Annotated[list[int] | None, Query(alias="pageSize")],
    next_token: Annotated[list[str] | None, Query(alias="nextToken")] = None,
) -> api_gateway.Response[api_model.GetUsersResponse]:
    """Returns a list of all users."""
    if next_token:
        next_token = unquote(next_token.pop())
        next_token = json.loads(next_token)

    page_size = page_size.pop() if page_size else None

    users, last_evaluated_key = dependencies.projects_query_service.get_all_users(
        page_size=page_size, next_token=next_token if next_token else None
    )
    last_evaluated_key = json.dumps(last_evaluated_key) if last_evaluated_key else None

    users_parsed = [api_model.User.parse_obj(p.dict()) for p in users]
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetUsersResponse(users=users_parsed, nextToken=last_evaluated_key),
        content_type=content_types.APPLICATION_JSON,
    )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@exception_handler.handle_exceptions(
    user_exceptions=[domain_exception.DomainException], cors_config=cors_config
)  # TODO: add custom user exceptions to the array
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
