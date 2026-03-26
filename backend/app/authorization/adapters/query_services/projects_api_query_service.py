from typing import Any
from urllib.parse import quote

from app.authorization.domain.ports import projects_query_service
from app.authorization.domain.read_models import project, project_assignment
from app.shared.adapters.boto import paging_utils
from app.shared.api import aws_api


# has to be refactored: user assignments should move to this BC
class ProjectsApiQueryService(projects_query_service.ProjectsQueryService):
    def __init__(
        self,
        api: aws_api.AWSAPI,
    ):
        self._aws_api = api

    def get_user_assignments(self, user_id: str) -> list[project_assignment.Assignment]:
        done = False
        assignments = []
        next_token = None
        while not done:
            resp = self._get_user_assignments(user_id=user_id, next_token=next_token)
            assignments.extend(
                [
                    project_assignment.Assignment(
                        userId=user_id,
                        roles=a.get("roles", []),
                        userEmail=a.get("userEmail", ""),
                        projectId=a.get("projectId", ""),
                        activeDirectoryGroups=a.get("activeDirectoryGroups", []),
                    )
                    for a in resp.get("assignments", [])
                ]
            )
            next_token = resp.get("nextToken")
            if not next_token:
                done = True
        return assignments

    def get_projects(self, page: paging_utils.PageInfo) -> paging_utils.PagedResponse[project.Project]:

        get_projects_resp = self._aws_api.call_api(
            path="internal/projects",
            http_method="GET",
            query_params={"pageSize": page.page_size, "nextToken": page.page_token},
        )

        return paging_utils.PagedResponse[project.Project](
            items=[project.Project(projectId=resp.get("projectId")) for resp in get_projects_resp.get("projects")],
            page_token=get_projects_resp.get("nextToken", None),
        )

    def get_project_assignments(
        self, project_id: str, page: paging_utils.PageInfo
    ) -> paging_utils.PagedResponse[project_assignment.Assignment]:

        get_project_assignments_response = self._aws_api.call_api(
            path=f"internal/projects/{quote(project_id)}/users",
            http_method="GET",
            query_params={"pageSize": page.page_size, "nextToken": quote(page.page_token) if page.page_token else None},
        )

        return paging_utils.PagedResponse[project_assignment.Assignment](
            items=[
                project_assignment.Assignment.parse_obj({**resp, "projectId": project_id})
                for resp in get_project_assignments_response.get("assignments")
            ],
            page_token=get_project_assignments_response.get("nextToken", None),
        )

    def _get_user_assignments(self, user_id: str, next_token: Any) -> dict:
        params = {"pageSize": "20", "userId": user_id, "nextToken": next_token}

        return self._aws_api.call_api(
            path="internal/user/assignments",
            http_method="GET",
            query_params=params if params else None,
        )
