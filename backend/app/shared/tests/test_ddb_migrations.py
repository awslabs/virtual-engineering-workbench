import json
import logging
from datetime import datetime, timedelta, timezone
from unittest import mock

import assertpy
import pytest

from app.shared.adapters.unit_of_work_v2 import dynamodb_migrations


def test_migrations_when_there_are_none_should_not_do_anything(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
    )

    # ACT
    migrations.migrate()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_empty()


def test_migrations_when_no_migrations_in_db_should_run(mock_dynamodb, backend_app_dynamodb_table, test_table_name):
    # ARRANGE
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
    ).register_migration(
        name="001.TestMigration",
        script=lambda table: table.put_item(Item={"PK": "001.TestMigration", "SK": "001.TestMigration"}),
    )

    # ACT
    migrations.migrate()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(2)
    assertpy.assert_that(items["Items"]).contains({"PK": "001.TestMigration", "SK": "001.TestMigration"})
    assertpy.assert_that(items["Items"]).contains(
        {
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {
                    "name": "001.TestMigration",
                    "sequence": 0,
                    "state": "COMPLETED",
                    "createDate": mock.ANY,
                    "lastAttemptDate": mock.ANY,
                }
            ],
        }
    )


def test_migrations_when_has_migrations_in_db_should_run_new(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item={
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": "2022-01-01T00:00:00"}
            ],
        }
    )

    migrations = (
        dynamodb_migrations.DynamoDBMigrator(
            ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
        )
        .register_migration(
            name="001.TestMigration",
            script=lambda table: table.put_item(Item={"PK": "001.TestMigration", "SK": "001.TestMigration"}),
        )
        .register_migration(
            name="002.TestMigration-2",
            script=lambda table: table.put_item(Item={"PK": "002.TestMigration 2", "SK": "002.TestMigration 2"}),
        )
    )

    # ACT
    migrations.migrate()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(2)
    assertpy.assert_that(items["Items"]).contains({"PK": "002.TestMigration 2", "SK": "002.TestMigration 2"})
    assertpy.assert_that(items["Items"]).contains(
        {
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 3,
            "migrationScripts": [
                {
                    "name": "001.TestMigration",
                    "sequence": 0,
                    "state": "COMPLETED",
                    "createDate": mock.ANY,
                    "lastAttemptDate": None,
                },
                {
                    "name": "002.TestMigration-2",
                    "sequence": 1,
                    "state": "COMPLETED",
                    "createDate": mock.ANY,
                    "lastAttemptDate": mock.ANY,
                },
            ],
        }
    )


def test_migrations_when_has_migrations_in_db_should_not_run_old(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item={
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": "2022-01-01T00:00:00"}
            ],
        }
    )

    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
    ).register_migration(
        name="001.TestMigration",
        script=lambda table: table.put_item(Item={"PK": "001.TestMigration", "SK": "001.TestMigration"}),
    )

    # ACT
    migrations.migrate()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(1)
    assertpy.assert_that(items["Items"]).contains(
        {
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": mock.ANY}
            ],
        }
    )


def test_migrations_when_migrations_out_of_sync_should_raise(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item={
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": "2022-01-01T00:00:00"}
            ],
        }
    )

    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
    ).register_migration(
        name="001.TestMigrationNameChange",
        script=lambda table: table.put_item(Item={"PK": "001.TestMigration", "SK": "001.TestMigration"}),
    )

    # ACT
    with pytest.raises(Exception) as exc:
        migrations.migrate()

    # ASSERT
    assertpy.assert_that(str(exc.value)).contains(
        "Migration 001.TestMigrationNameChange is not in the correct order. Expected 001.TestMigration"
    )


def test_migrations_when_has_failed_migrations_should_retry(mock_dynamodb, backend_app_dynamodb_table, test_table_name):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item={
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {"name": "001.TestMigration", "sequence": 0, "state": "FAILED", "createDate": "2022-01-01T00:00:00"}
            ],
        }
    )

    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
    ).register_migration(
        name="001.TestMigration",
        script=lambda table: table.put_item(Item={"PK": "001.TestMigration", "SK": "001.TestMigration"}),
    )

    # ACT
    migrations.migrate()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(2)
    assertpy.assert_that(items["Items"]).contains({"PK": "001.TestMigration", "SK": "001.TestMigration"})
    assertpy.assert_that(items["Items"]).contains(
        {
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 3,
            "migrationScripts": [
                {
                    "name": "001.TestMigration",
                    "sequence": 0,
                    "state": "COMPLETED",
                    "createDate": mock.ANY,
                    "lastAttemptDate": mock.ANY,
                }
            ],
        }
    )


def test_migrations_when_migration_fails_should_mark_new_migrations_as_failed(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    migrations = (
        dynamodb_migrations.DynamoDBMigrator(
            ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
        )
        .register_migration(
            name="001.FailingMigration",
            script=lambda _: (_ for _ in ()).throw(Exception("Test")),
        )
        .register_migration(
            name="002.TestMigration",
            script=lambda table: table.put_item(Item={"PK": "002.TestMigration", "SK": "002.TestMigration"}),
        )
    )

    # ACT: the failure is raised, after the states are saved
    with pytest.raises(dynamodb_migrations.MigrationFailedError, match="001.FailingMigration"):
        migrations.migrate()

    # ASSERT
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(1)
    assertpy.assert_that(items["Items"]).contains(
        {
            "PK": "MIGRATION",
            "SK": "MIGRATION",
            "sequenceNo": 1,
            "migrationScripts": [
                {
                    "name": "001.FailingMigration",
                    "sequence": 0,
                    "state": "FAILED",
                    "createDate": mock.ANY,
                    "lastAttemptDate": mock.ANY,
                },
                {
                    "name": "002.TestMigration",
                    "sequence": 1,
                    "state": "FAILED",
                    "createDate": mock.ANY,
                    "lastAttemptDate": None,
                },
            ],
        }
    )


def _failed_migration_item(last_attempt_date: datetime) -> dict:
    return {
        "PK": "MIGRATION",
        "SK": "MIGRATION",
        "sequenceNo": 1,
        "migrationScripts": [
            {
                "name": "001.TestMigration",
                "sequence": 0,
                "state": "FAILED",
                "createDate": "2022-01-01T00:00:00+00:00",
                "lastAttemptDate": last_attempt_date.isoformat(),
            }
        ],
    }


def test_migrations_when_failed_migration_attempted_recently_should_raise_without_retrying(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item=_failed_migration_item(last_attempt_date=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    script = mock.Mock()
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=test_table_name,
        logger=mock.create_autospec(spec=logging.Logger),
        retry_backoff=timedelta(minutes=5),
    ).register_migration(name="001.TestMigration", script=script)

    # ACT
    with pytest.raises(dynamodb_migrations.MigrationFailedError, match="001.TestMigration"):
        migrations.migrate()

    # ASSERT
    script.assert_not_called()
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(1)
    assertpy.assert_that(items["Items"][0]["sequenceNo"]).is_equal_to(1)
    assertpy.assert_that(items["Items"][0]["migrationScripts"][0]["state"]).is_equal_to("FAILED")


def test_migrations_when_failed_migration_back_off_passed_should_retry(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item=_failed_migration_item(last_attempt_date=datetime.now(timezone.utc) - timedelta(minutes=10))
    )
    script = mock.Mock()
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=test_table_name,
        logger=mock.create_autospec(spec=logging.Logger),
        retry_backoff=timedelta(minutes=5),
    ).register_migration(name="001.TestMigration", script=script)

    # ACT
    migrations.migrate()

    # ASSERT
    script.assert_called_once()
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"][0]["migrationScripts"][0]["state"]).is_equal_to("COMPLETED")


@pytest.mark.parametrize("recently_failed", [False, True])
def test_migrations_when_migration_failed_error_raised_should_publish_metric(
    recently_failed, mock_dynamodb, backend_app_dynamodb_table, test_table_name, capsys, monkeypatch
):
    # ARRANGE
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "TestNamespace")
    if recently_failed:
        backend_app_dynamodb_table.put_item(Item=_failed_migration_item(last_attempt_date=datetime.now(timezone.utc)))
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb, table_name=test_table_name, logger=mock.create_autospec(spec=logging.Logger)
    ).register_migration(
        name="001.TestMigration",
        script=lambda _: (_ for _ in ()).throw(Exception("Test")),
    )

    # ACT
    with pytest.raises(dynamodb_migrations.MigrationFailedError):
        migrations.migrate()

    # ASSERT
    metric = json.loads(capsys.readouterr().out.strip())
    assertpy.assert_that(metric).contains_entry({dynamodb_migrations.MIGRATION_FAILED_METRIC_NAME: [1.0]})
    assertpy.assert_that(metric).contains_entry({"TableName": test_table_name})


def _running_migration_item(create_date: str, last_attempt_date: str | None) -> dict:
    script = {"name": "001.TestMigration", "sequence": 0, "state": "RUNNING", "createDate": create_date}
    if last_attempt_date:
        script["lastAttemptDate"] = last_attempt_date
    return {"PK": "MIGRATION", "SK": "MIGRATION", "sequenceNo": 1, "migrationScripts": [script]}


@pytest.mark.parametrize(
    "create_date,last_attempt_minutes_ago",
    [
        # Claimed by a retry that died 20 minutes ago
        ("2022-01-01T00:00:00+00:00", 20),
        # Entry written before lastAttemptDate existed, without a timezone
        ("2022-01-01T00:00:00", None),
    ],
)
def test_migrations_when_running_migration_is_stale_should_retry(
    create_date, last_attempt_minutes_ago, mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    last_attempt_date = (
        (datetime.now(timezone.utc) - timedelta(minutes=last_attempt_minutes_ago)).isoformat()
        if last_attempt_minutes_ago
        else None
    )
    backend_app_dynamodb_table.put_item(Item=_running_migration_item(create_date, last_attempt_date))
    script = mock.Mock()
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=test_table_name,
        logger=mock.create_autospec(spec=logging.Logger),
        stale_running_timeout=timedelta(minutes=15),
    ).register_migration(name="001.TestMigration", script=script)

    # ACT
    migrations.migrate()

    # ASSERT
    script.assert_called_once()
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"]).is_length(1)
    assertpy.assert_that(items["Items"][0]["migrationScripts"][0]["state"]).is_equal_to("COMPLETED")


def test_migrations_when_running_migration_is_recent_should_raise_without_running(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item=_running_migration_item(
            create_date="2022-01-01T00:00:00+00:00",
            last_attempt_date=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        )
    )
    script = mock.Mock()
    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=test_table_name,
        logger=mock.create_autospec(spec=logging.Logger),
        stale_running_timeout=timedelta(minutes=15),
    ).register_migration(name="001.TestMigration", script=script)

    # ACT
    with pytest.raises(Exception, match="already a migration in progress"):
        migrations.migrate()

    # ASSERT
    script.assert_not_called()
    items = backend_app_dynamodb_table.scan()
    assertpy.assert_that(items["Items"][0]["sequenceNo"]).is_equal_to(1)
    assertpy.assert_that(items["Items"][0]["migrationScripts"][0]["state"]).is_equal_to("RUNNING")


def test_migrations_when_retrying_failed_migration_should_save_claim_time_before_running(
    mock_dynamodb, backend_app_dynamodb_table, test_table_name
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item=_failed_migration_item(last_attempt_date=datetime.now(timezone.utc) - timedelta(minutes=10))
    )
    saved_while_running = {}

    def script(table):
        item = table.get_item(Key={"PK": "MIGRATION", "SK": "MIGRATION"})["Item"]
        saved_while_running.update(item["migrationScripts"][0])

    migrations = dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=test_table_name,
        logger=mock.create_autospec(spec=logging.Logger),
        retry_backoff=timedelta(minutes=5),
    ).register_migration(name="001.TestMigration", script=script)

    # ACT
    migrations.migrate()

    # ASSERT: a later start can tell how old this claim is if the execution dies mid-script
    assertpy.assert_that(saved_while_running["state"]).is_equal_to("RUNNING")
    claimed_at = datetime.fromisoformat(saved_while_running["lastAttemptDate"])
    assertpy.assert_that(datetime.now(timezone.utc) - claimed_at).is_less_than(timedelta(minutes=1))
