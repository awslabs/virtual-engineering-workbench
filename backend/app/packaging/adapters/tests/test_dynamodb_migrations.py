import assertpy
import pytest

from app.packaging.adapters.repository.dynamo_entity_migrations import migrations_config
from app.shared.adapters.unit_of_work_v2 import dynamodb_migrations

TEST_TABLE_NAME = "test-migration-table"
TEST_GSI_ENTITIES = "gsi_entities"


@pytest.fixture()
def migration_table(mock_dynamodb):
    """Table with entity GSI for migration queries, without imageUpstreamId GSI.
    Real DynamoDB silently skips NULL-typed GSI key attributes; moto rejects them."""
    table = mock_dynamodb.create_table(
        TableName=TEST_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "entity", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": TEST_GSI_ENTITIES,
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


def test_001_image_add_image_source_pipeline(
    mock_dynamodb,
    migration_table,
    mock_logger,
):
    # ARRANGE
    with migration_table.batch_writer() as batch:
        # Image without imageSource — should be migrated
        batch.put_item(
            Item={
                "PK": "PROJECT#proj-001",
                "SK": "IMAGE#image-001",
                "entity": "IMAGE",
                "imageUpstreamId": "ami-111",
                "status": "CREATED",
            }
        )

        # Image without imageSource and with None imageUpstreamId — should be migrated + attribute removed
        batch.put_item(
            Item={
                "PK": "PROJECT#proj-001",
                "SK": "IMAGE#image-002",
                "entity": "IMAGE",
                "imageUpstreamId": None,
                "status": "CREATED",
            }
        )

        # Image that already has imageSource — should be skipped
        batch.put_item(
            Item={
                "PK": "PROJECT#proj-001",
                "SK": "IMAGE#image-003",
                "entity": "IMAGE",
                "imageSource": "EXISTING_AMI",
                "imageUpstreamId": "ami-333",
                "status": "CREATED",
            }
        )

        # Non-image entity — should be skipped
        batch.put_item(
            Item={
                "PK": "PROJECT#proj-001",
                "SK": "RECIPE#reci-001",
                "entity": "RECIPE",
                "status": "CREATED",
            }
        )

    # ACT
    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=TEST_TABLE_NAME,
        logger=mock_logger,
    ).register_migrations(migrations_config(gsi_entities=TEST_GSI_ENTITIES)).migrate()

    # ASSERT
    item_1 = migration_table.get_item(Key={"PK": "PROJECT#proj-001", "SK": "IMAGE#image-001"}).get("Item")
    assertpy.assert_that(item_1.get("imageSource")).is_equal_to("PIPELINE")
    assertpy.assert_that(item_1.get("imageUpstreamId")).is_equal_to("ami-111")

    item_2 = migration_table.get_item(Key={"PK": "PROJECT#proj-001", "SK": "IMAGE#image-002"}).get("Item")
    assertpy.assert_that(item_2.get("imageSource")).is_equal_to("PIPELINE")
    assertpy.assert_that(item_2.get("imageUpstreamId")).is_none()

    item_3 = migration_table.get_item(Key={"PK": "PROJECT#proj-001", "SK": "IMAGE#image-003"}).get("Item")
    assertpy.assert_that(item_3.get("imageSource")).is_equal_to("EXISTING_AMI")

    recipe = migration_table.get_item(Key={"PK": "PROJECT#proj-001", "SK": "RECIPE#reci-001"}).get("Item")
    assertpy.assert_that(recipe.get("imageSource")).is_none()


def test_001_idempotent_on_second_run(
    mock_dynamodb,
    migration_table,
    mock_logger,
):
    # ARRANGE
    migration_table.put_item(
        Item={
            "PK": "PROJECT#proj-001",
            "SK": "IMAGE#image-001",
            "entity": "IMAGE",
            "imageUpstreamId": "ami-111",
            "status": "CREATED",
        }
    )

    migrator_kwargs = dict(ddb_resource=mock_dynamodb, table_name=TEST_TABLE_NAME, logger=mock_logger)
    config = migrations_config(gsi_entities=TEST_GSI_ENTITIES)

    # ACT — run twice
    dynamodb_migrations.DynamoDBMigrator(**migrator_kwargs).register_migrations(config).migrate()
    dynamodb_migrations.DynamoDBMigrator(**migrator_kwargs).register_migrations(config).migrate()

    # ASSERT — still correct
    item = migration_table.get_item(Key={"PK": "PROJECT#proj-001", "SK": "IMAGE#image-001"}).get("Item")
    assertpy.assert_that(item.get("imageSource")).is_equal_to("PIPELINE")
    assertpy.assert_that(item.get("imageUpstreamId")).is_equal_to("ami-111")
