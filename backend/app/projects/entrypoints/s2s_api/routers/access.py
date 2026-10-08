from aws_lambda_powertools.event_handler.exceptions import ForbiddenError

from app.projects.domain.model.service_client_assignment import ServiceClientAssignmentStatus


def require_scope(router, scope: str):
    claims = router.current_event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    if scope not in str(claims.get("scope", "")).split():
        raise ForbiddenError("Required scope is missing")


def require_project_access(router, query_service, project_id: str, scope: str):
    require_scope(router, scope)
    client_id = router.context["user_principal"].user_name
    assignment = query_service.get_service_client_assignment(project_id, client_id)
    if assignment is None or assignment.status != ServiceClientAssignmentStatus.ACTIVE:
        raise ForbiddenError("Client is not assigned to project")


def require_bootstrap_or_project_access(router, query_service, project_id: str):
    claims = router.current_event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    scopes = str(claims.get("scope", "")).split()
    client_id = router.context["user_principal"].user_name
    assignment = query_service.get_service_client_assignment(project_id, client_id)
    if (
        "clients/projects/client_assignment.write" in scopes
        and assignment
        and assignment.status == ServiceClientAssignmentStatus.ACTIVE
    ):
        return
    if "clients/projects/client_assignment.bootstrap" in scopes:
        if query_service.get_project_by_id(project_id) is None:
            raise ForbiddenError("Project does not exist")
        assignments = query_service.list_service_client_assignments(project_id)
        if any(item.status == ServiceClientAssignmentStatus.ACTIVE for item in assignments):
            raise ForbiddenError("Bootstrap is limited to orphan projects")
        return
    raise ForbiddenError("Client is not assigned to project")
