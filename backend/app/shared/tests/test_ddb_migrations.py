import logging
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
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": mock.ANY}
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
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": mock.ANY},
                {"name": "002.TestMigration-2", "sequence": 1, "state": "COMPLETED", "createDate": mock.ANY},
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
                {"name": "001.TestMigration", "sequence": 0, "state": "COMPLETED", "createDate": mock.ANY}
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
                {"name": "001.FailingMigration", "sequence": 0, "state": "FAILED", "createDate": mock.ANY},
                {"name": "002.TestMigration", "sequence": 1, "state": "FAILED", "createDate": mock.ANY},
            ],
        }
    )
