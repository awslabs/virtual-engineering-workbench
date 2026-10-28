from unittest import mock

import pytest
import requests

from app.packaging.adapters.services.projects_api_service_client_project_access_service import (
    ProjectsApiServiceClientProjectAccessService,
)
from app.packaging.domain.exceptions.s2s_exception import ProjectAccessDenied, ProjectAccessUnavailable
from app.shared.api import aws_api


@pytest.fixture()
def api():
    return mock.create_autospec(spec=aws_api.AWSAPIBase)


def service(api):
    return ProjectsApiServiceClientProjectAccessService(api=api)


def assignment(status="ACTIVE", client_id="client-1", project_id="proj-1"):
    return {
        "assignment": {
            "clientId": client_id,
            "projectId": project_id,
            "status": status,
        }
    }


def test_require_access_accepts_exact_active_assignment(api):
    api.call_api.return_value = assignment()

    service(api).require_access("client-1", "proj-1")

    api.call_api.assert_called_once_with(
        path="internal/projects/proj-1/clients/client-1",
        http_method="GET",
    )


def test_require_access_quotes_path_segments(api):
    api.call_api.return_value = assignment(client_id="client/one", project_id="proj/one")

    service(api).require_access("client/one", "proj/one")

    api.call_api.assert_called_once_with(
        path="internal/projects/proj%2Fone/clients/client%2Fone",
        http_method="GET",
    )


@pytest.mark.parametrize(
    "response",
    [
        assignment(status="REVOKED"),
        {"assignment": None},
        {},
        assignment(client_id="another-client"),
        assignment(project_id="another-project"),
    ],
)
def test_require_access_denies_non_matching_or_inactive_assignment(api, response):
    api.call_api.return_value = response

    with pytest.raises(ProjectAccessDenied) as exc_info:
        service(api).require_access("client-1", "proj-1")

    assert exc_info.value.code == "PROJECT_ACCESS_DENIED"
    assert exc_info.value.retryable is False


def test_require_access_maps_not_found_to_denied(api):
    response = requests.Response()
    response.status_code = 404
    api.call_api.side_effect = requests.HTTPError(response=response)

    with pytest.raises(ProjectAccessDenied):
        service(api).require_access("client-1", "proj-1")


@pytest.mark.parametrize(
    "error",
    [
        requests.HTTPError(response=requests.Response()),
        aws_api.RetryableServiceException("Projects unavailable"),
        RuntimeError("invalid upstream response"),
    ],
)
def test_require_access_maps_other_upstream_failures_to_unavailable(api, error):
    if isinstance(error, requests.HTTPError):
        error.response.status_code = 500
    api.call_api.side_effect = error

    with pytest.raises(ProjectAccessUnavailable) as exc_info:
        service(api).require_access("client-1", "proj-1")

    assert exc_info.value.code == "PROJECT_ACCESS_UNAVAILABLE"
    assert exc_info.value.retryable is True
