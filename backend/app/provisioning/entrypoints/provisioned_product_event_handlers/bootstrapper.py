import boto3
from aws_lambda_powertools import logging
from mypy_boto3_cloudformation import client as cf_client
from mypy_boto3_ec2 import client as ec2_client
from mypy_boto3_ecs import client as ecs_client
from mypy_boto3_servicecatalog import client
from mypy_boto3_ssm import client as ssm_client
from pydantic import BaseModel

from app.provisioning.adapters.query_services import (
    dynamodb_products_query_service,
    dynamodb_provisioned_products_query_service,
    dynamodb_versions_query_service,
)
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_migrations import migrations_config
from app.provisioning.adapters.services import (
    ec2_instance_management_service,
    ecs_container_management_service,
    sc_products_service,
)
from app.provisioning.domain.command_handlers.product_provisioning import (
    complete_launch,
    complete_removal,
    complete_update,
    fail_launch,
    fail_removal,
    fail_update,
)
from app.provisioning.domain.commands.product_provisioning import (
    complete_product_launch_command,
    complete_provisioned_product_removal_command,
    complete_provisioned_product_update,
    fail_product_launch_command,
    fail_provisioned_product_removal_command,
    fail_provisioned_product_update,
)
from app.provisioning.domain.ports import provisioned_products_query_service
from app.provisioning.entrypoints.provisioned_product_event_handlers import config
from app.shared.adapters.auth import temporary_credential_provider
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_migrations, dynamodb_unit_of_work
from app.shared.api import aws_events_api
from app.shared.ddd import aggregate
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger
from app.shared.middleware import event_handler


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    products_service: sc_products_service.ServiceCatalogProductsService
    provisioned_products_query_service: provisioned_products_query_service.ProvisionedProductsQueryService

    class Config:
        arbitrary_types_allowed = True


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: event_handler.EventBridgeEventResolver,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    events_client = session.client("events", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    mb = message_bus_metrics.MessageBusMetrics(
        inner=event_bridge_message_bus.EventBridgeMessageBus(
            events_api=events_api,
            event_bus_name=app_config.get_domain_event_bus_name(),
            bounded_context_name=app_config.get_bounded_context_name(),
            logger=logger,
        ),
        metrics_client=metrics_client,
        logger=logger,
    )

    temp_cred_provider = temporary_credential_provider.TemporaryCredentialProvider(
        sts_client=session.client("sts", region_name=app_config.get_default_region()),
        ctx=app,
    )

    publisher = aggregate.AggregatePublisher(
        mb=mb,
        uow=uow,
    )

    pp_query_service = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_primary_key(),
        gsi_custom_query_by_service_catalog_id=app_config.get_gsi_name_query_by_alt_key(),
        gsi_custom_query_by_user_id=app_config.get_gsi_name_query_by_user_key(),
        gsi_custom_query_all=app_config.get_gsi_name_query_by_alt_key_2(),
        gsi_custom_query_by_product_id=app_config.get_gsi_name_query_by_alt_keys_3(),
        gsi_custom_query_by_project_id=app_config.get_gsi_name_query_by_alt_keys_4(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_alt_keys_5(),
    )

    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=dynamodb,
        table_name=app_config.get_table_name(),
        logger=logger,
    ).register_migrations(migrations_config(provisioned_products_qs=pp_query_service)).migrate()

    versions_qry_srv = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=app_config.get_gsi_name_query_by_alt_key(),
    )

    product_qry_srv = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
    )

    def _get_boto_client_for(client_name: str, aws_account_id: str, region: str, user_id: str):
        (
            access_key_id,
            secret_access_key,
            session_token,
        ) = temp_cred_provider.get_for(
            aws_account_id=aws_account_id,
            role_name=app_config.get_provisioning_target_account_role(),
            session_name=user_id,
        )
        return session.client(
            client_name,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
        )

    def _get_cf_boto_client(aws_account_id: str, region: str, user_id: str) -> cf_client.CloudFormationClient:
        return _get_boto_client_for(
            client_name="cloudformation", aws_account_id=aws_account_id, region=region, user_id=user_id
        )

    def _get_sc_boto_client(aws_account_id: str, region: str, user_id: str) -> client.ServiceCatalogClient:
        return _get_boto_client_for(
            client_name="servicecatalog", aws_account_id=aws_account_id, region=region, user_id=user_id
        )

    def _get_ssm_boto_client(aws_account_id: str, region: str, user_id: str) -> ssm_client.SSMClient:
        return _get_boto_client_for(client_name="ssm", aws_account_id=aws_account_id, region=region, user_id=user_id)

    def _get_ec2_boto_client(aws_account_id: str, region: str, user_id: str) -> ec2_client.EC2Client:
        return _get_boto_client_for(client_name="ec2", aws_account_id=aws_account_id, region=region, user_id=user_id)

    def _get_ecs_boto_client(aws_account_id: str, region: str, user_id: str) -> ecs_client.ECSClient:
        return _get_boto_client_for(client_name="ecs", aws_account_id=aws_account_id, region=region, user_id=user_id)

    products_srv = sc_products_service.ServiceCatalogProductsService(
        cf_boto_client_provider=_get_cf_boto_client, sc_boto_client_provider=_get_sc_boto_client, logger=logger
    )

    instance_mgmt_srv = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=_get_ec2_boto_client
    )

    container_mgmt_srv = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=_get_ecs_boto_client, logger=logger
    )

    def _complete_launch_handler_factory():
        def _handle(command):
            complete_launch.handle(
                command=command,
                publisher=publisher,
                products_srv=products_srv,
                provisioned_products_qs=pp_query_service,
                logger=logger,
                instance_mgmt_srv=instance_mgmt_srv,
                container_mgmt_srv=container_mgmt_srv,
                products_qry_srv=product_qry_srv,
                versions_qry_srv=versions_qry_srv,
            )

        return _handle

    def _fail_launch_handler_factory():
        def _handle(command):
            fail_launch.handle(
                command=command,
                publisher=publisher,
                virtual_targets_qs=pp_query_service,
                logger=logger,
                products_srv=products_srv,
            )

        return _handle

    def _complete_upgrade_handler_factory():
        def _handle(command):
            complete_update.handle(
                command=command,
                publisher=publisher,
                products_srv=products_srv,
                virtual_targets_qs=pp_query_service,
                container_mgmt_srv=container_mgmt_srv,
                logger=logger,
                instance_mgmt_srv=instance_mgmt_srv,
                versions_qs=versions_qry_srv,
            )

        return _handle

    def _fail_upgrade_handler_factory():
        def _handle(command):
            fail_update.handle(
                command=command,
                publisher=publisher,
                provisioned_products_qs=pp_query_service,
                logger=logger,
                products_srv=products_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                container_mgmt_srv=container_mgmt_srv,
            )

        return _handle

    def _complete_removal_handler_factory():
        def _handle(command):
            complete_removal.handle(
                command=command,
                publisher=publisher,
                virtual_targets_qs=pp_query_service,
                logger=logger,
            )

        return _handle

    def _fail_removal_handler_factory():
        def _handle(command):
            fail_removal.handle(
                command=command,
                publisher=publisher,
                virtual_targets_qs=pp_query_service,
                logger=logger,
                products_srv=products_srv,
            )

        return _handle

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
        )
        .register_handler(
            complete_product_launch_command.CompleteProductLaunchCommand,
            _complete_launch_handler_factory(),
        )
        .register_handler(
            fail_product_launch_command.FailProductLaunchCommand,
            _fail_launch_handler_factory(),
        )
        .register_handler(
            complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand,
            _complete_upgrade_handler_factory(),
        )
        .register_handler(
            fail_provisioned_product_update.FailProvisionedProductUpdateCommand,
            _fail_upgrade_handler_factory(),
        )
        .register_handler(
            complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand,
            _complete_removal_handler_factory(),
        )
        .register_handler(
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
            _fail_removal_handler_factory(),
        )
    )

    return Dependencies(
        command_bus=command_bus,
        products_service=products_srv,
        provisioned_products_query_service=pp_query_service,
    )
