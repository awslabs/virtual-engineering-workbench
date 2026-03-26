import asyncio
import logging

from app.authorization.domain.commands import sync_assignments_command
from app.authorization.domain.exceptions import domain_exception
from app.authorization.domain.ports import (
    assignments_query_service,
    projects_query_service,
)
from app.authorization.domain.read_models import project, project_assignment
from app.shared.adapters.boto import paging_utils
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.utils import async_io

MAX_TRANSACTION_SIZE = 100


def handle(
    command: sync_assignments_command.SyncAssignmentsCommand,
    projects_qs: projects_query_service.ProjectsQueryService,
    assignments_qs: assignments_query_service.AssignmentsQueryService,
    uow: unit_of_work.UnitOfWork,
    logger: logging.Logger,
):
    projects = __get_all_projects(projects_qs=projects_qs)

    projects_bc_assignments, authorization_bc_assignments = async_io.run_concurrently(
        __get_projects_bc_assignments(projects_qs=projects_qs, projects=projects),
        __get_authorization_bc_assignments(assignments_qs=assignments_qs, projects=projects),
    )

    if (
        error := next(
            iter(
                [err for err in [projects_bc_assignments, authorization_bc_assignments] if isinstance(err, Exception)]
            ),
            None,
        )
    ) and error is not None:
        logger.error("Error when fetching assignments", exc_info=error)
        raise domain_exception.DomainException("Error when fetching assignments") from error

    assignments_dict = {
        f"{assignment.userId}#{assignment.projectId}": {"projects": assignment}
        for assignment in projects_bc_assignments
    }

    for auth_assignment in authorization_bc_assignments:
        assignments_dict[f"{auth_assignment.userId}#{auth_assignment.projectId}"] = {
            **assignments_dict.get(f"{auth_assignment.userId}#{auth_assignment.projectId}", {}),
            "authorization": auth_assignment,
        }

    with uow:
        assignment_repo = uow.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment)

        for assignment in assignments_dict.values():
            assignment_in_auth = assignment.get("authorization", None)
            assignment_in_projects = assignment.get("projects", None)

            if assignment_in_projects is not None and assignment_in_auth is None:
                assignment_repo.add(assignment_in_projects)
            if assignment_in_projects is None and assignment_in_auth is not None:
                assignment_repo.remove(
                    project_assignment.AssignmentPrimaryKey(
                        userId=assignment_in_auth.userId,
                        projectId=assignment_in_auth.projectId,
                    )
                )

            if (
                assignment_in_projects is not None
                and assignment_in_auth is not None
                and (
                    assignment_in_auth.roles != assignment_in_projects.roles
                    or assignment_in_auth.userEmail != assignment_in_projects.userEmail
                    or assignment_in_auth.activeDirectoryGroups != assignment_in_projects.activeDirectoryGroups
                    or assignment_in_auth.groupMemberships != assignment_in_projects.groupMemberships
                )
            ):

                assignment_in_auth.roles = assignment_in_projects.roles
                assignment_in_auth.userEmail = assignment_in_projects.userEmail
                assignment_in_auth.activeDirectoryGroups = assignment_in_projects.activeDirectoryGroups
                assignment_in_auth.groupMemberships = assignment_in_projects.groupMemberships

                assignment_repo.update_entity(
                    project_assignment.AssignmentPrimaryKey(
                        userId=assignment_in_auth.userId, projectId=assignment_in_auth.projectId
                    ),
                    assignment_in_auth,
                )

        uow.commit()


def __get_all_projects(projects_qs: projects_query_service.ProjectsQueryService) -> list[project.Project]:
    projects: list[project.Project] = []

    page_token = None
    while (
        projects_response := projects_qs.get_projects(page=paging_utils.PageInfo(page_size=100, page_token=page_token))
    ) and projects_response.page_token is not None:
        projects.extend(projects_response.items)
        page_token = projects_response.page_token
    projects.extend(projects_response.items)

    return projects


async def __get_projects_bc_assignments(
    projects_qs: projects_query_service.ProjectsQueryService, projects: list[project.Project]
):
    async_results = await asyncio.gather(
        *[
            async_io.run_async(__get_projects_bc_assignments_subroutine(projects_qs, project.projectId))
            for project in projects
        ],
        return_exceptions=True,
    )

    if (error := next(iter([err for err in async_results if isinstance(err, Exception)]), None)) and error is not None:
        raise error

    return [assignment for async_result in async_results for assignment in async_result]


async def __get_authorization_bc_assignments(
    assignments_qs: assignments_query_service.AssignmentsQueryService, projects: list[project.Project]
):
    async_results = await asyncio.gather(
        *[
            async_io.run_async(__get_authorization_bc_assignments_subroutine(assignments_qs, project.projectId))
            for project in projects
        ],
        return_exceptions=True,
    )

    if (error := next(iter([err for err in async_results if isinstance(err, Exception)]), None)) and error is not None:
        raise error

    return [assignment for async_result in async_results for assignment in async_result]


def __get_projects_bc_assignments_subroutine(
    projects_qs: projects_query_service.ProjectsQueryService,
    project_id: str,
):

    def __inner() -> list[project_assignment.Assignment]:
        assignments = []

        page_token = None
        while (
            assignments_response := projects_qs.get_project_assignments(
                project_id=project_id, page=paging_utils.PageInfo(page_size=500, page_token=page_token)
            )
        ) and assignments_response.page_token is not None:
            assignments.extend(assignments_response.items)
            page_token = assignments_response.page_token

        assignments.extend(assignments_response.items)

        return assignments

    return __inner


def __get_authorization_bc_assignments_subroutine(
    assignments_qs: assignments_query_service.AssignmentsQueryService,
    project_id: str,
):

    def __inner() -> list[project_assignment.Assignment]:
        return assignments_qs.get_project_assignments(project_id=project_id)

    return __inner
