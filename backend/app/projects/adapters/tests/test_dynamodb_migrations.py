import datetime
import uuid

import assertpy
from boto3.dynamodb.conditions import Attr

from app.projects.adapters.repository.dynamo_entity_migrations import migrations_config
from app.projects.domain.model import project, project_account
from app.shared.adapters.unit_of_work_v2 import dynamodb_migrations


def test_migrations_should_set_project_id_and_sequence_to_all_accounts(
    mock_dynamodb, backend_app_dynamodb_table, mock_logger, test_table_name, gsi_entities, mock_ddb_repo
):
    # ARRANGE

    projects = []
    for _ in range(5):
        projects.append(
            project.Project(
                projectId=str(uuid.uuid4()),
                projectName="test-name",
                projectDescription="test-description",
                isActive=True,
                createDate=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                lastUpdateDate=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        )

    accounts = []
    project_acc_id_map = {}

    for idx in range(50):
        account = project_account.ProjectAccount(
            awsAccountId=str(uuid.uuid4()),
            accountType="USER",
            accountName="fake",
            accountDescription="fake desc",
            createDate=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            lastUpdateDate=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            accountStatus=project_account.ProjectAccountStatusEnum.Creating,
            technologyId="uuid-abc",
            stage="dev",
            projectId=projects[idx % 5].projectId,
        )
        accounts.append(account)
        project_acc_id_map[account.awsAccountId] = projects[idx % 5].projectId

    with mock_ddb_repo:
        for p in projects:
            mock_ddb_repo.get_repository(project.ProjectPrimaryKey, project.Project).add(p)

        for account in accounts:
            mock_ddb_repo.get_repository(project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount).add(
                account
            )

        mock_ddb_repo.commit()

    with mock_ddb_repo:
        for account in accounts:
            project_id = account.projectId
            account.projectId = "-"
            mock_ddb_repo.get_repository(
                project_account.ProjectAccountPrimaryKey, project_account.ProjectAccount
            ).update_entity(
                project_account.ProjectAccountPrimaryKey(
                    projectId=project_id,
                    id=account.id,
                ),
                account,
            )

        mock_ddb_repo.commit()

    # ACT
    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=test_table_name,
        logger=mock_logger,
    ).register_migrations(migrations_config(gsi_entities=gsi_entities)).migrate()

    # ASSERT

    accounts_in_db = backend_app_dynamodb_table.scan(
        FilterExpression=Attr("PK").begins_with("PROJECT#") & Attr("SK").begins_with("ACCOUNT#")
    ).get("Items")

    for acc in accounts_in_db:
        assertpy.assert_that(acc.get("projectId")).is_not_none()
        assertpy.assert_that(acc.get("projectId")).is_equal_to(project_acc_id_map.get(acc.get("awsAccountId")))
        assertpy.assert_that(acc.get("sequenceNo")).is_not_none()
        assertpy.assert_that(acc.get("sequenceNo")).is_equal_to(0)

    projects_in_db = backend_app_dynamodb_table.scan(
        FilterExpression=Attr("PK").begins_with("PROJECT#") & Attr("SK").begins_with("PROJECT#")
    ).get("Items")

    for proj in projects_in_db:
        assertpy.assert_that(proj.get("sequenceNo")).is_not_none()
        assertpy.assert_that(proj.get("sequenceNo")).is_equal_to(0)
