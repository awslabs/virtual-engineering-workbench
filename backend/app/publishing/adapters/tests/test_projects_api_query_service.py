from unittest import mock

import assertpy

from app.publishing.adapters.query_services import projects_api_query_service


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_projects_returns_correct_projects(mock_api):
    # ARRANGE

    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "projects": [
            {"projectId": "proj-id-1", "projectName": "proj-name-1", "projectDescription": "proj-desc-1"},
            {"projectId": "proj-id-2", "projectName": "proj-name-2", "projectDescription": "proj-desc-2"},
            {"projectId": "proj-id-3", "projectName": "proj-name-3", "projectDescription": "proj-desc-3"},
        ]
    }

    # ACT
    projects = project_api_qry_srv.get_projects()

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/projects",
        http_method="GET",
        query_params={"pageSize": "100"},
    )
    assertpy.assert_that(projects).is_not_none()
    assertpy.assert_that(projects).is_length(3)
    assertpy.assert_that(projects[0].projectId).is_equal_to("proj-id-1")


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_project_by_id_returns_correct_project(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "projects": [
            {"projectId": "proj-id-1", "projectName": "proj-name-1", "projectDescription": "proj-desc-1"},
            {"projectId": "proj-id-2", "projectName": "proj-name-2", "projectDescription": "proj-desc-2"},
            {"projectId": "proj-id-3", "projectName": "proj-name-3", "projectDescription": "proj-desc-3"},
        ]
    }

    # ACT
    project = project_api_qry_srv.get_project("proj-id-2")

    # ASSERT
    assertpy.assert_that(project).is_not_none()
    assertpy.assert_that(project.projectId).is_equal_to("proj-id-2")


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_aws_account_by_id_returns_correct_account(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "projectAccounts": [
            {
                "id": "000",
                "awsAccountId": "0012345678900",
                "stage": "dev",
                "region": "us-east-1",
                "accountStatus": "Active",
            },
            {
                "id": "111",
                "awsAccountId": "000000000000",
                "stage": "dev",
                "region": "eu-west-3",
                "accountStatus": "Onboarding",
            },
        ],
    }

    # ACT
    account = project_api_qry_srv.get_aws_account_by_id("proj-id-1", "111")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/accounts",
        http_method="GET",
        query_params={"pageSize": "100", "projectId": "proj-id-1"},
    )
    assertpy.assert_that(account).is_not_none()
    assertpy.assert_that(account.dict()).is_equal_to(
        {
            "id": "111",
            "awsAccountId": "000000000000",
            "stage": "dev",
            "region": "eu-west-3",
        }
    )


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_aws_accounst_by_status_returns_correct_account(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "projectAccounts": [
            {
                "id": "000",
                "awsAccountId": "0012345678900",
                "stage": "dev",
                "region": "us-east-1",
                "accountStatus": "Active",
            },
            {
                "id": "111",
                "awsAccountId": "000000000000",
                "stage": "dev",
                "region": "eu-west-3",
                "accountStatus": "Onboarding",
            },
        ],
    }

    # ACT
    accounts = project_api_qry_srv.get_aws_accounts_by_status("proj-id-1", ["Active"])

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/accounts",
        http_method="GET",
        query_params={
            "pageSize": "100",
            "projectId": "proj-id-1",
        },
    )
    assertpy.assert_that(accounts).is_not_none()
    assertpy.assert_that(accounts).is_length(1)
    assertpy.assert_that(accounts[0].dict()).is_equal_to(
        {
            "id": "000",
            "awsAccountId": "0012345678900",
            "stage": "dev",
            "region": "us-east-1",
        }
    )


@mock.patch("app.shared.api.aws_api.AWSAPI")
def test_get_user_assignments_count_return_assignments_count(mock_api):
    # ARRANGE
    project_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=mock_api)
    mock_api.call_api.return_value = {
        "assignments": [
            {
                "projectId": "proj-id-1",
                "roles": ["role-1"],
                "activeDirectoryGroups": ["active-group-1"],
                "activeDirectoryGroupStatus": "active",
            }
        ]
    }

    # ACT
    assignments_count = project_api_qry_srv.get_user_assignments_count("user-1")

    # ASSERT
    mock_api.call_api.assert_called_once_with(
        path="internal/user/assignments",
        http_method="GET",
        query_params={"pageSize": "100", "userId": "user-1"},
    )
    assertpy.assert_that(assignments_count).is_not_none()
    assertpy.assert_that(assignments_count).is_equal_to(1)
