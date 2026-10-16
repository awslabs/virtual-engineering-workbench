from urllib.parse import quote

import requests

from app.packaging.domain.exceptions.s2s_exception import ProjectAccessDenied, ProjectAccessUnavailable
from app.packaging.domain.ports.service_client_project_access_service import ServiceClientProjectAccessService
from app.shared.api import aws_api


class ProjectsApiServiceClientProjectAccessService(ServiceClientProjectAccessService):
    def __init__(self, api: aws_api.AWSAPIBase) -> None:
        self._aws_api = api

    def require_access(self, client_id: str, project_id: str) -> None:
        path = "/".join(
            [
                "internal",
                "projects",
                quote(project_id, safe=""),
                "clients",
                quote(client_id, safe=""),
            ]
        )
        try:
            response = self._aws_api.call_api(path=path, http_method="GET")
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise ProjectAccessDenied() from exc
            raise ProjectAccessUnavailable() from exc
        except Exception as exc:
            raise ProjectAccessUnavailable() from exc

        assignment = response.get("assignment") if isinstance(response, dict) else None
        if not isinstance(assignment, dict) or not self._is_active_assignment(
            assignment,
            client_id=client_id,
            project_id=project_id,
        ):
            raise ProjectAccessDenied()

    @staticmethod
    def _is_active_assignment(assignment: dict, client_id: str, project_id: str) -> bool:
        return (
            assignment.get("clientId") == client_id
            and assignment.get("projectId") == project_id
            and assignment.get("status") == "ACTIVE"
        )
