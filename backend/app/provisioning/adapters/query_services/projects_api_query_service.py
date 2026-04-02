import typing
from urllib.parse import quote

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.adapters.internal import constants
from app.provisioning.domain.ports import projects_query_service
from app.provisioning.domain.read_models import project, project_account, project_assignment
from app.shared.api import aws_api


class ProjectsApiQueryService(projects_query_service.ProjectsQueryService):
    def __init__(
        self,
        api: aws_api.AWSAPI,
    ):
        self._aws_api = api

    def get_aws_accounts_by_status(
        self,
        project_id: str,
        statuses: list,
        account_type: typing.Optional[str] = None,
        stage: typing.Optional[str] = None,
    ) -> list[project_account.ProjectAccount]:
        resp = self._get_accounts(project_id=project_id, account_type=account_type, account_stage=stage)
        try:
            project_accounts = [
                project_account.ProjectAccount(
                    id=pa["id"],
                    awsAccountId=pa["awsAccountId"],
                    stage=pa["stage"],
                    region=pa.get("region", None),
                )
                for pa in resp["projectAccounts"]
                if pa.get("accountStatus", "") in statuses
            ]
        except KeyError:
            raise adapter_exception.AdapterException(constants.NO_ACCOUNT_ASSIGNED)

        return project_accounts

    def get_aws_account_by_id(
        self,
        project_id: str,
        account_id: str,
    ) -> typing.Optional[project_account.ProjectAccount]:
        resp = self._get_accounts(project_id=project_id)
        try:
            account = next(
                iter(
                    [
                        project_account.ProjectAccount(
                            id=pa["id"],
                            awsAccountId=pa["awsAccountId"],
                            stage=pa["stage"],
                            region=pa.get("region", None),
                        )
                        for pa in resp["projectAccounts"]
                        if pa["id"] == account_id
                    ]
                ),
                None,
            )
        except KeyError:
            raise adapter_exception.AdapterException(constants.NO_ACCOUNT_ASSIGNED)

        return account

    def get_projects(self) -> list[project.Project]:
        resp = self._get_projects()
        projects = [
            project.Project(
                projectId=proj["projectId"],
                projectName=proj["projectName"],
                projectDescription=proj["projectDescription"],
            )
            for proj in resp["projects"]
        ]
        return projects

    def get_user_assignments_count(self, user_id: str) -> int:
        resp = self._get_user_assignments(user_id)
        return len(resp["assignments"]) if resp.get("assignments") else 0

    def get_project(self, project_id: str) -> project.Project:
        resp = self._get_projects()
        try:
            proj = next(iter([proj for proj in resp["projects"] if proj["projectId"] == project_id]), None)
        except KeyError:
            raise adapter_exception.AdapterException(constants.NO_PROJECT_FOUND_ERROR.format(projectId=project_id))

        return project.Project(
            projectId=proj["projectId"],
            projectName=proj["projectName"],
            projectDescription=proj["projectDescription"],
        )

    def get_project_assignment(self, project_id: str, user_id: str) -> project_assignment.ProjectAssignment | None:
        path_segments = [
            "internal",
            "projects",
            quote(project_id, safe=""),
            "users",
            quote(user_id, safe=""),
        ]

        response = self._aws_api.call_api(
            path="/".join(path_segments),
            http_method="GET",
        )

        return (
            project_assignment.ProjectAssignment.model_validate(response.get("assignment"))
            if response and response.get("assignment", None)
            else None
        )

    def _get_accounts(
        self,
        project_id: typing.Optional[str] = None,
        account_type: typing.Optional[str] = None,
        account_stage: typing.Optional[str] = None,
    ) -> dict:
        params = {"pageSize": "20"}

        if project_id:
            params["projectId"] = project_id
        if account_stage:
            params["stage"] = account_stage
        if account_type:
            params["accountType"] = account_type

        return self._aws_api.call_api(
            path="internal/accounts",
            http_method="GET",
            query_params=params if params else None,
        )

    def _get_projects(self) -> dict:
        params = {"pageSize": "20"}

        return self._aws_api.call_api(
            path="internal/projects",
            http_method="GET",
            query_params=params if params else None,
        )

    def _get_user_assignments(self, user_id: str) -> dict:
        params = {"pageSize": "20", "userId": user_id}

        return self._aws_api.call_api(
            path="internal/user/assignments",
            http_method="GET",
            query_params=params if params else None,
        )
