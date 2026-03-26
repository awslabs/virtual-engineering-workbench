import json
import logging
import os
from unittest import mock

import assertpy
import boto3
import moto
import pytest
from attr import dataclass

from app.projects.adapters.repository import dynamo_entity_config
from app.projects.domain.model import project, project_assignment
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work as shared_dynamodb_unit_of_work_v2

TEST_REGION = "us-east-1"
TEST_TABLE_NAME = "test-table"
GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
GSI_NAME_AWS_ACCOUNTS = "gsi_aws_accounts"
GSI_NAME_ENTITIES = "gsi_entities_by_sort_key"


@pytest.fixture
def lambda_context():
    @dataclass
    class context:
        function_name = "test"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:eu-west-1:000000000:function:test"
        aws_request_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    return context


@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = TEST_REGION
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION
    os.environ["POWERTOOLS_METRICS_NAMESPACE"] = "Test"
    os.environ["POWERTOOLS_SERVICE_NAME"] = "Projects"
    os.environ["TABLE_NAME"] = TEST_TABLE_NAME
    os.environ["GSI_NAME_INVERTED_PK"] = GSI_NAME_INVERTED_PK
    os.environ["GSI_NAME_AWS_ACCOUNTS"] = GSI_NAME_AWS_ACCOUNTS
    os.environ["GSI_NAME_ENTITIES"] = GSI_NAME_ENTITIES


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name=TEST_REGION)


@pytest.fixture(autouse=True)
def backend_app_dynamodb_table(mock_dynamodb):
    table = mock_dynamodb.create_table(
        TableName=TEST_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "awsAccountId", "AttributeType": "S"},
            {"AttributeName": "entity", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI_NAME_INVERTED_PK,
                "KeySchema": [{"AttributeName": "SK", "KeyType": "HASH"}, {"AttributeName": "PK", "KeyType": "RANGE"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_AWS_ACCOUNTS,
                "KeySchema": [
                    {"AttributeName": "awsAccountId", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_ENTITIES,
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    table.meta.client.get_waiter("table_exists").wait(TableName=TEST_TABLE_NAME)
    return table


@pytest.fixture()
def populate_users(unit_of_work_mock_v2):
    with unit_of_work_mock_v2:
        for i in range(2):
            project_id = f"proj-000{i}"
            unit_of_work_mock_v2.get_repository(project.ProjectPrimaryKey, project.Project).add(
                project.Project(
                    projectId=project_id,
                    projectName=f"Project {i}",
                    isActive=True,
                )
            )
            for j in range(5):
                unit_of_work_mock_v2.get_repository(
                    project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
                ).add(
                    project_assignment.Assignment(
                        userId=f"USER{j}",
                        projectId=project_id,
                        roles=[project_assignment.Role.ADMIN],
                    )
                )
            if i % 2 == 0:
                unit_of_work_mock_v2.get_repository(
                    project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
                ).add(
                    project_assignment.Assignment(
                        userId=f"PROJ{i}UNIQUE{i}",
                        projectId=project_id,
                        roles=[project_assignment.Role.PLATFORM_USER],
                    )
                )
            else:
                unit_of_work_mock_v2.get_repository(
                    project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
                ).add(
                    project_assignment.Assignment(
                        userId=f"PROJ{i}UNIQUE{i}",
                        projectId=project_id,
                        roles=[project_assignment.Role.BETA_USER],
                    )
                )
                unit_of_work_mock_v2.get_repository(
                    project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
                ).add(
                    project_assignment.Assignment(
                        userId=f"PROJ{i}UNIQUE{i}2",
                        projectId=project_id,
                        roles=[project_assignment.Role.POWER_USER],
                    )
                )

        unit_of_work_mock_v2.commit()


@pytest.fixture()
def unit_of_work_mock_v2(mock_logger, mock_dynamodb, backend_app_dynamodb_table):
    return shared_dynamodb_unit_of_work_v2.DynamoDBUnitOfWork(
        table_name=TEST_TABLE_NAME,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=TEST_TABLE_NAME).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture()
def mock_logger():
    mock_logger = mock.create_autospec(spec=logging.Logger)
    return mock_logger


def test_when_there_are_users_should_produce_metrics(lambda_context, populate_users, capsys):
    # ARRANGE
    from app.projects.entrypoints.scheduled_metric_producer import handler

    # ACT
    handler.handler({}, lambda_context)

    # ASSERT
    captured_stdout, captured_stderr = capsys.readouterr()
    log_entries = captured_stdout.split("\n")
    log_entries_dict = [json.loads(s) for s in log_entries if s]
    project_0_metric_users = next(
        m for m in log_entries_dict if "Program" in m and m["Program"] == "Project 0" and "TotalAssignedUsers" in m
    )
    project_1_metric_users = next(
        m for m in log_entries_dict if "Program" in m and m["Program"] == "Project 1" and "TotalAssignedUsers" in m
    )

    totals = next(m for m in log_entries_dict if "TotalVEWUsers" in m)

    assertpy.assert_that(project_0_metric_users).contains_entry({"TotalAssignedUsers": [6.0]})
    assertpy.assert_that(project_1_metric_users).contains_entry({"TotalAssignedUsers": [7.0]})

    assertpy.assert_that(totals).contains_entry({"TotalVEWUsers": [8.0]})
