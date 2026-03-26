import assertpy
from boto3.dynamodb.conditions import Attr

from app.provisioning.adapters.query_services import dynamodb_provisioned_products_query_service
from app.provisioning.adapters.repository.dynamo_entity_migrations import migrations_config
from app.provisioning.domain.model import provisioned_product
from app.shared.adapters.unit_of_work_v2 import dynamodb_migrations


def test_001_qpk_4_and_seq_no(
    mock_dynamodb,
    backend_app_dynamodb_table,
    mock_logger,
    mock_table_name,
    mock_ddb_repo,
    get_sample_provisioned_product,
    mock_gsi_inverted,
    mock_gsi_by_sc_id,
    mock_gsi_by_user_id,
    mock_gsi_by_entity,
    mock_gsi_by_product_id,
    mock_gsi_by_project_id,
    mock_gsi_by_status,
):
    # ARRANGE
    query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=mock_gsi_inverted,
        gsi_custom_query_by_service_catalog_id=mock_gsi_by_sc_id,
        gsi_custom_query_by_user_id=mock_gsi_by_user_id,
        gsi_custom_query_all=mock_gsi_by_entity,
        gsi_custom_query_by_product_id=mock_gsi_by_product_id,
        gsi_custom_query_by_project_id=mock_gsi_by_project_id,
        gsi_custom_query_by_status=mock_gsi_by_status,
    )

    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey, provisioned_product.ProvisionedProduct
        )

        for i in range(101):
            repo.add(get_sample_provisioned_product(provisioned_product_id=f"pp-{i}"))

        for db_item in mock_ddb_repo._context._db_items:
            item = db_item.get("Put").get("Item")
            item.pop("QPK_4")
            item.pop("sequenceNo")

        mock_ddb_repo.commit()

    # ACT
    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=mock_dynamodb,
        table_name=mock_table_name,
        logger=mock_logger,
    ).register_migrations(migrations_config(provisioned_products_qs=query_service)).migrate()

    # ASSERT
    all_items = backend_app_dynamodb_table.scan(
        FilterExpression=Attr("SK").begins_with("PROVISIONED_PRODUCT#"),
    )
    assertpy.assert_that(set([item.get("QPK_4") for item in all_items.get("Items")])).contains_only(
        "PROVISIONED_PRODUCT#PROVISIONING"
    )
    assertpy.assert_that(set([item.get("sequenceNo") for item in all_items.get("Items")])).contains_only(0)
