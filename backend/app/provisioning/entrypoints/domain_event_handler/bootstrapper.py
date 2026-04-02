import boto3
from aws_lambda_powertools import logging
from mypy_boto3_cloudformation import client as cf_client
from mypy_boto3_ec2 import client as ec2_client
from mypy_boto3_ecs import client as ecs_client
from mypy_boto3_servicecatalog import client as sc_client
from mypy_boto3_ssm import client as ssm_client
from pydantic import BaseModel, ConfigDict

from app.provisioning.adapters.query_services import (
    dynamodb_products_query_service,
    dynamodb_provisioned_products_query_service,
    dynamodb_versions_query_service,
)
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_migrations import (
    migrations_config,
)
from app.provisioning.adapters.services import (
    aws_parameter_service,
    ec2_instance_management_service,
    ecs_container_management_service,
    sc_products_service,
)
from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.command_handlers.product_provisioning import (
    complete_launch,
    complete_removal,
    complete_update,
    deprovision_product,
    fail_launch,
    fail_removal,
    fail_update,
    provision_product,
    start_update,
    stop_after_update,
    stop_for_update,
    update_product,
)
from app.provisioning.domain.command_handlers.provisioned_product_configuration import fail as fail_configuration
from app.provisioning.domain.command_handlers.provisioned_product_state import (
    complete_start,
    complete_stop,
    initiate_stop,
    start,
    stop,
)
from app.provisioning.domain.commands.product_provisioning import (
    complete_product_launch_command,
    complete_provisioned_product_removal_command,
    complete_provisioned_product_update,
    deprovision_provisioned_product_command,
    fail_product_launch_command,
    fail_provisioned_product_removal_command,
    fail_provisioned_product_update,
    provision_product_command,
    start_provisioned_product_update_command,
    stop_provisioned_product_after_update_complete_command,
    stop_provisioned_product_for_update_command,
    update_provisioned_product_command,
)
from app.provisioning.domain.commands.provisioned_product_configuration import (
    fail_provisioned_product_configuration_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
    initiate_provisioned_product_stop_command,
    start_provisioned_product_command,
    stop_provisioned_product_command,
)
from app.provisioning.entrypoints.domain_event_handler import config
from app.shared.adapters.auth import temporary_credential_provider
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_migrations,
    dynamodb_unit_of_work,
)
from app.shared.api import aws_events_api, aws_scheduler_api
from app.shared.ddd import aggregate
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger
from app.shared.middleware import event_handler


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    model_config = ConfigDict(arbitrary_types_allowed=True)


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
    scheduler_client = session.client("scheduler", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=scheduler_client,
        bounded_context_name=app_config.get_bounded_context_name(),
        role_arn=app_config.get_lambda_iam_role(),
        event_bus_arn=app_config.get_domain_event_bus_name(),
    )

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    mb = message_bus_metrics.MessageBusMetrics(
        inner=event_bridge_message_bus.EventBridgeMessageBus(
            events_api=events_api,
            scheduler_api=scheduler_api,
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

    provisioned_products_qs = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
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
    ).register_migrations(migrations_config(provisioned_products_qs=provisioned_products_qs)).migrate()

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
            client_name="cloudformation",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    def _get_sc_boto_client(aws_account_id: str, region: str, user_id: str) -> sc_client.ServiceCatalogClient:
        return _get_boto_client_for(
            client_name="servicecatalog",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    def _get_ssm_boto_client(aws_account_id: str, region: str, user_id: str) -> ssm_client.SSMClient:
        return _get_boto_client_for(
            client_name="ssm",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    def _get_sm_boto_client(aws_account_id: str, region: str, user_id: str) -> ssm_client.SSMClient:
        return _get_boto_client_for(
            client_name="secretsmanager",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    def _get_ec2_boto_client(aws_account_id: str, region: str, user_id: str) -> ec2_client.EC2Client:
        return _get_boto_client_for(
            client_name="ec2",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    def _get_ecs_boto_client(aws_account_id: str, region: str, user_id: str) -> ecs_client.ECSClient:
        return _get_boto_client_for(
            client_name="ecs",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    products_srv = sc_products_service.ServiceCatalogProductsService(
        cf_boto_client_provider=_get_cf_boto_client,
        sc_boto_client_provider=_get_sc_boto_client,
        logger=logger,
    )

    parameter_srv = aws_parameter_service.AWSParameterService(
        ssm_boto_client_provider=_get_ssm_boto_client,
        sm_boto_client_provider=_get_sm_boto_client,
    )

    instance_mgmt_srv = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=_get_ec2_boto_client
    )

    container_mgmt_srv = ecs_container_management_service.ECSContainerManagementService(
        ecs_boto_client_provider=_get_ecs_boto_client, logger=logger
    )

    subnet_selector = networking_helpers.get_provisioning_subnet_selector(
        app_config.get_provisioning_subnet_selector(),
        tag=app_config.get_provisioning_subnet_selector_tag(),
    )

    def __provision_product_handler_factory(command):
        provision_product.handle(
            command=command,
            publisher=publisher,
            products_srv=products_srv,
            virtual_targets_qs=provisioned_products_qs,
            parameter_srv=parameter_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            logger=logger,
            spoke_account_vpc_id_param_name=app_config.get_spoke_account_vpc_id_param_name(),
            subnet_selector=subnet_selector,
            authorize_user_ip_address_param_value=app_config.get_authorize_user_ip_address_param_value(),
            uow=uow,
        )

    def __stop_provisioned_product_for_update_handler(command):
        stop_for_update.handle(
            command=command,
            publisher=publisher,
            provisioned_products_qs=provisioned_products_qs,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
            logger=logger,
            parameter_srv=parameter_srv,
            spoke_account_vpc_id_param_name=app_config.get_spoke_account_vpc_id_param_name(),
            authorize_user_ip_address_param_value=app_config.get_authorize_user_ip_address_param_value(),
        )

    def __update_provisioned_product_handler(command):
        update_product.handle(
            command=command,
            publisher=publisher,
            products_srv=products_srv,
            provisioned_products_qs=provisioned_products_qs,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
            logger=logger,
            versions_qs=versions_qry_srv,
            parameter_srv=parameter_srv,
            spoke_account_vpc_id_param_name=app_config.get_spoke_account_vpc_id_param_name(),
            subnet_selector=subnet_selector,
            uow=uow,
        )

    def __deprovision_product_handler(command):
        deprovision_product.handle(
            command=command,
            publisher=publisher,
            products_srv=products_srv,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
        )

    def __complete_launch_handler(command):
        complete_launch.handle(
            command=command,
            publisher=publisher,
            products_srv=products_srv,
            provisioned_products_qs=provisioned_products_qs,
            logger=logger,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
            products_qry_srv=product_qry_srv,
            versions_qry_srv=versions_qry_srv,
        )

    def __fail_launch_handler(command):
        fail_launch.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            products_srv=products_srv,
        )

    def __complete_upgrade_handler(command):
        complete_update.handle(
            command=command,
            publisher=publisher,
            products_srv=products_srv,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
            versions_qs=versions_qry_srv,
        )

    def __fail_upgrade_handler(command):
        fail_update.handle(
            command=command,
            publisher=publisher,
            provisioned_products_qs=provisioned_products_qs,
            logger=logger,
            products_srv=products_srv,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
        )

    def __complete_removal_handler(command):
        complete_removal.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
        )

    def __fail_removal_handler(command):
        fail_removal.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            products_srv=products_srv,
        )

    def __start_handler(command):
        start.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
            parameter_srv=parameter_srv,
            spoke_account_vpc_id_param_name=app_config.get_spoke_account_vpc_id_param_name(),
            authorize_user_ip_address_param_value=app_config.get_authorize_user_ip_address_param_value(),
        )

    def __stop_handler(command):
        stop.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
        )

    def __complete_start_handler(command):
        complete_start.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
        )

    def __complete_stop_handler(command):
        complete_stop.handle(
            command=command,
            publisher=publisher,
            virtual_targets_qs=provisioned_products_qs,
            logger=logger,
            instance_mgmt_srv=instance_mgmt_srv,
            container_mgmt_srv=container_mgmt_srv,
        )

    def __fail_configuration_handler(command):
        fail_configuration.handle(
            command=command,
            publisher=publisher,
            provisioned_products_qry_srv=provisioned_products_qs,
            logger=logger,
        )

    def __stop_provisioned_product_after_update_handler(command):
        stop_after_update.handle(
            command=command,
            logger=logger,
            publisher=publisher,
            provisioned_products_qs=provisioned_products_qs,
        )

    def __initiate_stop_provisioned_product_handler(command):
        initiate_stop.handle(
            command=command,
            publisher=publisher,
            logger=logger,
            virtual_targets_qs=provisioned_products_qs,
        )

    def _start_update_handler(command):
        start_update.handle(
            command=command,
            publisher=publisher,
            logger=logger,
            provisioned_products_qs=provisioned_products_qs,
            versions_qs=versions_qry_srv,
        )

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            provision_product_command.ProvisionProductCommand,
            __provision_product_handler_factory,
        )
        .register_handler(
            stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand,
            __stop_provisioned_product_for_update_handler,
        )
        .register_handler(
            update_provisioned_product_command.UpdateProvisionedProductCommand,
            __update_provisioned_product_handler,
        )
        .register_handler(
            deprovision_provisioned_product_command.DeprovisionProvisionedProductCommand,
            __deprovision_product_handler,
        )
        .register_handler(
            complete_product_launch_command.CompleteProductLaunchCommand,
            __complete_launch_handler,
        )
        .register_handler(
            fail_product_launch_command.FailProductLaunchCommand,
            __fail_launch_handler,
        )
        .register_handler(
            complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand,
            __complete_removal_handler,
        )
        .register_handler(
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
            __fail_removal_handler,
        )
        .register_handler(
            start_provisioned_product_command.StartProvisionedProductCommand,
            __start_handler,
        )
        .register_handler(
            stop_provisioned_product_command.StopProvisionedProductCommand,
            __stop_handler,
        )
        .register_handler(
            complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
            __complete_start_handler,
        )
        .register_handler(
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
            __complete_stop_handler,
        )
        .register_handler(
            complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand,
            __complete_upgrade_handler,
        )
        .register_handler(
            fail_provisioned_product_update.FailProvisionedProductUpdateCommand,
            __fail_upgrade_handler,
        )
        .register_handler(
            fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand,
            __fail_configuration_handler,
        )
        .register_handler(
            stop_provisioned_product_after_update_complete_command.StopProvisionedProductAfterUpdateCompleteCommand,
            __stop_provisioned_product_after_update_handler,
        )
        .register_handler(
            initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand,
            __initiate_stop_provisioned_product_handler,
        )
        .register_handler(
            start_provisioned_product_update_command.StartProvisionedProductUpdateCommand,
            _start_update_handler,
        )
    )

    return Dependencies(
        command_bus=command_bus,
    )
