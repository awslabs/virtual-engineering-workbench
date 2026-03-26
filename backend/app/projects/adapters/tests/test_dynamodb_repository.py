from unittest import mock

import assertpy

from app.projects.domain.model import (
    enrolment,
    project,
    project_account,
    project_assignment,
    technology,
    user,
)


def test_account_repo_add_should_add_entity(mock_ddb_repo, get_account_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    acc = get_account_entity_mock(project_id="proj-123", id="acc-123")

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(acc)
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-123",
            "SK": "ACCOUNT#acc-123",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-123",
            "SK": "ACCOUNT#acc-123",
            "accountDescription": "fake desc",
            "accountName": "fake",
            "accountStatus": "Creating",
            "accountType": "USER",
            "awsAccountId": mock.ANY,
            "createDate": "2022-12-01T00:12:00+00:00",
            "lastOnboardingResult": None,
            "lastOnboardingErrorMessage": None,
            "id": "acc-123",
            "lastUpdateDate": "2022-12-01T00:12:00+00:00",
            "projectId": "proj-123",
            "region": "us-east-1",
            "sequenceNo": 0,
            "stage": "dev",
            "technologyId": "tech-123",
            "parameters": None,
        }
    )


def test_account_repo_update_should_update_entity(mock_ddb_repo, get_account_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    acc = get_account_entity_mock(project_id="proj-123", id="acc-123")
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(acc)
        mock_ddb_repo.commit()

    acc.accountName = "XXXX-updated"

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount
        ).update_entity(
            project_account.ProjectAccountPrimaryKey(projectId="proj-123", id="acc-123"),
            acc,
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-123",
            "SK": "ACCOUNT#acc-123",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-123",
            "SK": "ACCOUNT#acc-123",
            "accountDescription": "fake desc",
            "accountName": "XXXX-updated",
            "accountStatus": "Creating",
            "accountType": "USER",
            "awsAccountId": mock.ANY,
            "createDate": "2022-12-01T00:12:00+00:00",
            "lastOnboardingResult": None,
            "lastOnboardingErrorMessage": None,
            "id": "acc-123",
            "lastUpdateDate": "2022-12-01T00:12:00+00:00",
            "projectId": "proj-123",
            "region": "us-east-1",
            "sequenceNo": 1,
            "stage": "dev",
            "technologyId": "tech-123",
            "parameters": None,
        }
    )


def test_account_repo_remove_should_remove_entity(mock_ddb_repo, get_account_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    acc = get_account_entity_mock(project_id="proj-123", id="acc-123")
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(acc)
        mock_ddb_repo.commit()

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).remove(
            project_account.ProjectAccountPrimaryKey(projectId="proj-123", id="acc-123"),
        )
        mock_ddb_repo.commit()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items.get("Items")).is_length(0)


def test_project_repo_should_add_entity(mock_ddb_repo, get_project_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    proj = get_project_entity_mock(project_id="proj-123")

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).add(proj)
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-123",
            "SK": "PROJECT#proj-123",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-123",
            "SK": "PROJECT#proj-123",
            "createDate": "2022-12-01T00:12:00+00:00",
            "entity": "PROJECT",
            "isActive": True,
            "lastUpdateDate": "2022-12-01T00:12:00+00:00",
            "projectDescription": "test-description",
            "projectId": "proj-123",
            "projectName": "test-name",
            "sequenceNo": 0,
        }
    )


def test_project_repo_should_update_entity(mock_ddb_repo, get_project_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    proj = get_project_entity_mock(project_id="proj-123")
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).add(proj)
        mock_ddb_repo.commit()

    proj.projectName = "XXXX-updated"
    proj.isActive = False

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).update_entity(
            pk=project.ProjectPrimaryKey(projectId="proj-123"), entity=proj
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-123",
            "SK": "PROJECT#proj-123",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-123",
            "SK": "PROJECT#proj-123",
            "createDate": "2022-12-01T00:12:00+00:00",
            "entity": "PROJECT",
            "isActive": False,
            "lastUpdateDate": "2022-12-01T00:12:00+00:00",
            "projectDescription": "test-description",
            "projectId": "proj-123",
            "projectName": "XXXX-updated",
            "sequenceNo": 1,
        }
    )


def test_project_repo_get_when_does_not_exist_should_return_none(mock_ddb_repo):
    # ARRANGE
    proj = None

    # ACT
    with mock_ddb_repo:
        proj = mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).get(
            project.ProjectPrimaryKey(projectId="proj-0000")
        )

    # ASSERT

    assertpy.assert_that(proj).is_none()


def test_project_assignment_repo_should_add_entity(
    mock_ddb_repo, get_assignment_entity_mock, backend_app_dynamodb_table
):
    # ARRANGE
    assignment = get_assignment_entity_mock()

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
            assignment
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "USER#u-0000",
            "SK": "PROJECT#proj-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "USER#u-0000",
            "SK": "PROJECT#proj-0000",
            "activeDirectoryGroupStatus": "SUCCESS",
            "activeDirectoryGroups": [{"domain": "test-domain", "groupName": "test-group"}],
            "projectId": "proj-0000",
            "roles": ["PLATFORM_USER"],
            "userEmail": "bough@example.com",
            "userId": "u-0000",
        }
    )


def test_project_assignment_repo_should_update_entity(
    mock_ddb_repo, get_assignment_entity_mock, backend_app_dynamodb_table
):
    # ARRANGE
    assignment = get_assignment_entity_mock()
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
            assignment
        )
        mock_ddb_repo.commit()

    assignment.roles = [project_assignment.Role.ADMIN]

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(
            project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
        ).update_entity(
            pk=project_assignment.AssignmentPrimaryKey(userId="u-0000", projectId="proj-0000"),
            entity=assignment,
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "USER#u-0000",
            "SK": "PROJECT#proj-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "USER#u-0000",
            "SK": "PROJECT#proj-0000",
            "activeDirectoryGroupStatus": "SUCCESS",
            "activeDirectoryGroups": [{"domain": "test-domain", "groupName": "test-group"}],
            "projectId": "proj-0000",
            "roles": ["ADMIN"],
            "userEmail": "bough@example.com",
            "userId": "u-0000",
        }
    )


def test_project_assignment_repo_should_remove_entity(
    mock_ddb_repo, get_assignment_entity_mock, backend_app_dynamodb_table
):
    # ARRANGE
    assignment = get_assignment_entity_mock()
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
            assignment
        )
        mock_ddb_repo.commit()

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).remove(
            pk=project_assignment.AssignmentPrimaryKey(userId="u-0000", projectId="proj-0000")
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "USER#u-0000",
            "SK": "PROJECT#proj-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_none()


def test_project_assignment_repo_should_get_entity(
    mock_ddb_repo, get_assignment_entity_mock, backend_app_dynamodb_table
):
    # ARRANGE
    assignment = get_assignment_entity_mock()
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
            assignment
        )
        mock_ddb_repo.commit()

    # ACT
    with mock_ddb_repo:
        ent = mock_ddb_repo.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).get(
            pk=project_assignment.AssignmentPrimaryKey(userId="u-0000", projectId="proj-0000")
        )
        mock_ddb_repo.commit()

    # ASSERT
    assertpy.assert_that(ent).is_equal_to(assignment)


def test_technology_repo_should_add_entity(mock_ddb_repo, get_technology_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    tech = get_technology_entity_mock()

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(technology.TechnologyPrimaryKey, technology.Technology).add(tech)
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-0000",
            "SK": "TECHNOLOGY#tech-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-0000",
            "SK": "TECHNOLOGY#tech-0000",
            "createDate": "2025-02-14",
            "description": "desc",
            "id": "tech-0000",
            "lastUpdateDate": "2025-02-14",
            "name": "test",
            "project_id": "proj-0000",
        }
    )


def test_technology_repo_should_update_entity(mock_ddb_repo, get_technology_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    tech = get_technology_entity_mock()

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(technology.TechnologyPrimaryKey, technology.Technology).add(tech)
        mock_ddb_repo.commit()

    tech.name = "updated"

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(technology.TechnologyPrimaryKey, technology.Technology).update_entity(
            pk=technology.TechnologyPrimaryKey(project_id="proj-0000", id="tech-0000"),
            entity=tech,
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-0000",
            "SK": "TECHNOLOGY#tech-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-0000",
            "SK": "TECHNOLOGY#tech-0000",
            "createDate": "2025-02-14",
            "description": "desc",
            "id": "tech-0000",
            "lastUpdateDate": "2025-02-14",
            "name": "updated",
            "project_id": "proj-0000",
        }
    )


def test_enrolment_repo_should_add_entity(mock_ddb_repo, get_enrolment_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    tech = get_enrolment_entity_mock()

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(enrolment.EnrolmentPrimaryKey, enrolment.Enrolment).add(tech)
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-0000",
            "SK": "ENROLMENT#e-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-0000",
            "QPK": "USER#u-123",
            "QSK": "ENROLMENT#Pending#e-0000",
            "SK": "ENROLMENT#e-0000",
            "approver": None,
            "createDate": None,
            "id": "e-0000",
            "lastUpdateDate": None,
            "projectId": "proj-0000",
            "reason": None,
            "resolveDate": None,
            "sourceSystem": None,
            "status": "Pending",
            "ticketId": None,
            "ticketLink": None,
            "userEmail": None,
            "userId": "u-123",
        }
    )


def test_enrolment_repo_should_update_entity(mock_ddb_repo, get_enrolment_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    tech = get_enrolment_entity_mock()

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(enrolment.EnrolmentPrimaryKey, enrolment.Enrolment).add(tech)
        mock_ddb_repo.commit()

    tech.status = enrolment.EnrolmentStatus.Approved

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(enrolment.EnrolmentPrimaryKey, enrolment.Enrolment).update_entity(
            pk=enrolment.EnrolmentPrimaryKey(projectId="proj-0000", id="e-0000"),
            entity=tech,
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "PROJECT#proj-0000",
            "SK": "ENROLMENT#e-0000",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "PROJECT#proj-0000",
            "QPK": "USER#u-123",
            "QSK": "ENROLMENT#Approved#e-0000",
            "SK": "ENROLMENT#e-0000",
            "approver": None,
            "createDate": None,
            "id": "e-0000",
            "lastUpdateDate": None,
            "projectId": "proj-0000",
            "reason": None,
            "resolveDate": None,
            "sourceSystem": None,
            "status": "Approved",
            "ticketId": None,
            "ticketLink": None,
            "userEmail": None,
            "userId": "u-123",
        }
    )


def test_user_repo_should_add_entity(mock_ddb_repo, get_user_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    tech = get_user_entity_mock()

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(user.UserPrimaryKey, user.User).add(tech)
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "USER#user-123",
            "SK": "USER#user-123",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "USER#user-123",
            "SK": "USER#user-123",
            "activeDirectoryGroupStatus": "SUCCESS",
            "activeDirectoryGroups": [{"domain": "test", "groupName": "group"}],
            "entity": "USER",
            "userEmail": "bough@example.com",
            "userId": "user-123",
        }
    )


def test_user_repo_should_update_entity(mock_ddb_repo, get_user_entity_mock, backend_app_dynamodb_table):
    # ARRANGE
    tech = get_user_entity_mock()

    with mock_ddb_repo:
        mock_ddb_repo.get_repository(user.UserPrimaryKey, user.User).add(tech)
        mock_ddb_repo.commit()

    tech.activeDirectoryGroups = ([user.ActiveDirectoryGroup(domain="test", groupName="group-other")],)

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(user.UserPrimaryKey, user.User).update_entity(
            pk=user.UserPrimaryKey(userId="user-123"), entity=tech
        )
        mock_ddb_repo.commit()

    # ASSERT

    acc_db = backend_app_dynamodb_table.get_item(
        Key={
            "PK": "USER#user-123",
            "SK": "USER#user-123",
        }
    )

    assertpy.assert_that(acc_db.get("Item")).is_equal_to(
        {
            "PK": "USER#user-123",
            "SK": "USER#user-123",
            "activeDirectoryGroupStatus": "SUCCESS",
            "activeDirectoryGroups": [[{"domain": "test", "groupName": "group-other"}]],
            "entity": "USER",
            "userEmail": "bough@example.com",
            "userId": "user-123",
        }
    )
