import boto3
from aws_lambda_powertools import logging
from mypy_boto3_ssm import client as ssm_client
from pydantic import BaseModel

from app.provisioning.adapters.query_services import (
    aws_networking_query_service,
    dynamodb_maintenance_windows_query_service,
    dynamodb_provisioned_products_query_service,
    dynamodb_versions_query_service,
    projects_api_query_service,
)
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_migrations import (
    migrations_config,
)
from app.provisioning.adapters.services import aws_parameter_service as ssm_parameter_service_v2
from app.provisioning.domain.command_handlers.product_provisioning import remove
from app.provisioning.domain.command_handlers.user_profile import clean_up
from app.provisioning.domain.commands.product_provisioning import (
    remove_provisioned_product_command,
)
from app.provisioning.domain.commands.user_profile import cleanup_user_profile_command
from app.provisioning.domain.query_services import (
    provisioned_products_domain_query_service,
)
from app.provisioning.entrypoints.projects_event_handler import config
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
from app.shared.api import aws_api, aws_events_api, ssm_parameter_service
from app.shared.ddd import aggregate
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    provisioned_products_domain_qry_srv: provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService

    class Config:
        arbitrary_types_allowed = True


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: temporary_credential_provider.SupportsContextManager,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    ssm_api_instance = ssm_parameter_service.SSMApi(region=app_config.get_default_region(), session=session)

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

    publisher = aggregate.AggregatePublisher(
        mb=mb,
        uow=uow,
    )

    versions_qry_srv = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=app_config.get_gsi_name_query_by_alt_key(),
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

    networking_qry_srv = aws_networking_query_service.AWSNetworkingService(
        ssm_api=ssm_api_instance,
        network_ip_map_param_name=app_config.get_network_ip_map_param_name(),
        logger=logger,
        available_networks_param_name=app_config.get_available_networks_param_name(),
    )

    temp_cred_provider = temporary_credential_provider.TemporaryCredentialProvider(
        sts_client=session.client("sts", region_name=app_config.get_default_region()),
        ctx=app,
    )

    def _get_boto_client_for(client_name: str, aws_account_id: str, region: str, user_id: str):
        (
            access_key_id,
            secret_access_key,
            session_token,
        ) = temp_cred_provider.get_for(
            aws_account_id=aws_account_id,
            role_name=app_config.get_product_provisioning_role(),
            session_name=user_id,
        )
        return session.client(
            client_name,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
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

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_projects_api_url(),
        region=app_config.get_default_region(),
        logger=logger,
    )

    parameter_srv = ssm_parameter_service_v2.AWSParameterService(
        ssm_boto_client_provider=_get_ssm_boto_client,
        sm_boto_client_provider=_get_sm_boto_client,
    )

    provisioned_products_domain_qs = provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
        provisioned_products_qry_srv=provisioned_products_qs,
        version_qry_srv=versions_qry_srv,
        networking_qry_srv=networking_qry_srv,
        parameter_srv=parameter_srv,
    )

    maintenance_windows_qs = dynamodb_maintenance_windows_query_service.DynamoDBMaintenanceWindowsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_primary_key(),
    )

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_projects_api_url(),
        region=app_config.get_default_region(),
        logger=logger,
    )

    projects_api_qs = projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)

    def _remove_provisioned_product_handler_factory():
        def _handle(command):
            remove.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                virtual_targets_qs=provisioned_products_qs,
            )

        return _handle

    def _clean_up_user_profile_handler_factory():
        def _handle(command):
            clean_up.handle(
                command=command,
                publisher=publisher,
                uow=uow,
                maintenance_windows_qry_srv=maintenance_windows_qs,
                projects_qry_srv=projects_api_qs,
                logger=logger,
            )

        return _handle

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            remove_provisioned_product_command.RemoveProvisionedProductCommand,
            _remove_provisioned_product_handler_factory(),
        )
        .register_handler(
            cleanup_user_profile_command.CleanUpUserProfileCommand,
            _clean_up_user_profile_handler_factory(),
        )
    )

    return Dependencies(
        command_bus=command_bus,
        provisioned_products_domain_qry_srv=provisioned_products_domain_qs,
    )
