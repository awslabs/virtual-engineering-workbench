from unittest import mock

import assertpy

from app.authorization.adapters.query_services import projects_api_query_service
from app.authorization.domain.read_models import project, project_assignment
from app.shared.adapters.boto import paging_utils


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_user_assignments_returns_correct_assignments(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "assignments": [
            {
                "roles": ["ADMIN", "PLATFORM_USER"],
                "userEmail": "user1@example.com",
            },
            {
                "roles": ["PLATFORM_USER"],
                "userEmail": "user1@example.com",
            },
        ]
    }

    # ACT
    assignments = project_api_qry_srv.get_user_assignments("user1")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/user/assignments",
        http_method="GET",
        query_params={"pageSize": "20", "userId": "user1", "nextToken": None},
    )

    assertpy.assert_that(assignments).is_not_none()
    assertpy.assert_that(assignments).is_length(2)

    # Verify first assignment
    assertpy.assert_that(assignments[0]).is_instance_of(project_assignment.Assignment)
    assertpy.assert_that(assignments[0].userId).is_equal_to("user1")
    assertpy.assert_that(assignments[0].roles).is_equal_to(["ADMIN", "PLATFORM_USER"])
    assertpy.assert_that(assignments[0].userEmail).is_equal_to("user1@example.com")

    # Verify second assignment
    assertpy.assert_that(assignments[1].roles).is_equal_to(["PLATFORM_USER"])


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_user_assignments_returns_empty_list_when_no_assignments(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {"assignments": []}

    # ACT
    assignments = project_api_qry_srv.get_user_assignments("user1")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/user/assignments",
        http_method="GET",
        query_params={"pageSize": "20", "userId": "user1", "nextToken": None},
    )
    assertpy.assert_that(assignments).is_not_none()
    assertpy.assert_that(assignments).is_empty()


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_user_assignments_handles_missing_assignments_key(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {}  # Response without assignments key

    # ACT
    assignments = project_api_qry_srv.get_user_assignments("user1")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/user/assignments",
        http_method="GET",
        query_params={"pageSize": "20", "userId": "user1", "nextToken": None},
    )
    assertpy.assert_that(assignments).is_not_none()
    assertpy.assert_that(assignments).is_empty()


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_projects_should_return_projects_paged(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "projects": [
            {
                "projectId": "proj-0",
                "projectName": "test 0",
                "projectDescription": "Descr 0",
                "isActive": True,
                "createDate": "2025-04-25",
                "lastUpdateDate": "2025-04-25",
            },
            {
                "projectId": "proj-1",
                "projectName": "test 1",
                "projectDescription": "Descr 1",
                "isActive": False,
                "createDate": "2025-04-25",
                "lastUpdateDate": "2025-04-25",
            },
        ],
        "nextToken": "next-token",
    }

    # ACT
    projects = project_api_qry_srv.get_projects(page=paging_utils.PageInfo(page_size=500, page_token="token"))

    # ASSERT

    assertpy.assert_that(projects).is_not_none()
    assertpy.assert_that(projects.page_token).is_equal_to("next-token")
    assertpy.assert_that(projects.items).is_length(2)
    assertpy.assert_that(projects.items).contains_only(
        project.Project(projectId="proj-0"), project.Project(projectId="proj-1")
    )

    mock_api.call_api.assert_called_once_with(
        path="internal/projects",
        http_method="GET",
        query_params={"pageSize": 500, "nextToken": "token"},
    )


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_project_assignments_returns_project_assignments_paged(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "assignments": [
            {
                "userId": "u-0",
                "roles": ["ADMIN", "PLATFORM_USER"],
                "userEmail": "user1@example.com",
            },
            {
                "userId": "u-1",
                "roles": ["PLATFORM_USER"],
                "userEmail": "user1@example.com",
            },
        ],
        "nextToken": "next-token",
    }

    # ACT
    assignments = project_api_qry_srv.get_project_assignments(
        project_id="proj-0", page=paging_utils.PageInfo(page_size=500, page_token="token")
    )

    # ASSERT

    assertpy.assert_that(assignments).is_not_none()
    assertpy.assert_that(assignments.page_token).is_equal_to("next-token")
    assertpy.assert_that(assignments.items).is_length(2)

    mock_api.call_api.assert_called_once_with(
        path="internal/projects/proj-0/users",
        http_method="GET",
        query_params={"pageSize": 500, "nextToken": "token"},
    )
