import boto3
from aws_lambda_powertools import logging
from mypy_boto3_cloudformation import client as cf_client
from mypy_boto3_ec2 import client as ec2_client
from mypy_boto3_servicecatalog import client
from mypy_boto3_ssm import client as ssm_client
from pydantic import BaseModel, ConfigDict

from app.provisioning.adapters.query_services import (
    aws_networking_query_service,
    dynamodb_provisioned_products_query_service,
    dynamodb_versions_query_service,
    projects_api_query_service,
)
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_migrations import (
    migrations_config,
)
from app.provisioning.adapters.services import aws_parameter_service as ssm_parameter_service_v2
from app.provisioning.adapters.services import (
    ec2_instance_management_service,
    ec2_instance_management_service_in_mem_cached,
    sc_products_service,
    sc_products_service_in_mem_cached,
)
from app.provisioning.domain.command_handlers.product_provisioning import (
    cleanup_provisioned_products,
)
from app.provisioning.domain.command_handlers.provisioned_product_state import (
    initiate_batch_stop,
    sync,
)
from app.provisioning.domain.commands.product_provisioning import (
    cleanup_provisioned_products_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_batch_stop_command,
    sync_provisioned_product_state_command,
)
from app.provisioning.domain.query_services import (
    projects_domain_query_service,
    provisioned_products_domain_query_service,
)
from app.provisioning.entrypoints.scheduled_jobs_handler import config
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
from app.shared.middleware import event_handler


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    provisioned_products_domain_qry_srv: provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService
    projects_domain_query_service: projects_domain_query_service.ProjectsDomainQueryService
    provisioned_product_cleanup_config: str
    model_config = ConfigDict(arbitrary_types_allowed=True)


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: event_handler.ScheduledJobEventResolver,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    ssm_api_instance = ssm_parameter_service.SSMApi(region=app_config.get_default_region(), session=session)

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

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_projects_api_url(),
        region=app_config.get_default_region(),
        logger=logger,
    )

    projects_api_qs = projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)
    projects_domain_qs = projects_domain_query_service.ProjectsDomainQueryService(projects_qry_srv=projects_api_qs)

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

    provisioned_product_cleanup_config = app_config.get_provisioned_product_cleanup_config()

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

    def _get_sc_boto_client(aws_account_id: str, region: str, user_id: str) -> client.ServiceCatalogClient:
        return _get_boto_client_for(
            client_name="servicecatalog",
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

    products_srv = sc_products_service_in_mem_cached.ServiceCatalogProductsServiceCachedInMemory(
        inner=sc_products_service.ServiceCatalogProductsService(
            cf_boto_client_provider=_get_cf_boto_client,
            sc_boto_client_provider=_get_sc_boto_client,
            logger=logger,
        ),
        request_context_manager=app,
        sc_boto_client_provider=_get_sc_boto_client,
    )

    instance_mgmt_srv = ec2_instance_management_service_in_mem_cached.EC2InstanceManagementServiceCachedInMemory(
        inner=ec2_instance_management_service.EC2InstanceManagementService(
            ec2_boto_client_provider=_get_ec2_boto_client
        ),
        request_context_manager=app,
        ec2_boto_client_provider=_get_ec2_boto_client,
    )

    def _sync_handler_factory():
        def _handle(command):
            sync.handle(
                command=command,
                instance_mgmt_srv=instance_mgmt_srv,
                logger=logger,
                pp_qry_srv=provisioned_products_qs,
                products_srv=products_srv,
                publisher=publisher,
            )

        return _handle

    def _cleanup_provisioned_products_command_handler_factory():
        def _handle(
            command: cleanup_provisioned_products_command.CleanupProvisionedProductsCommand,
        ):
            return cleanup_provisioned_products.handle(
                command=command,
                provisioned_products_qry_srv=provisioned_products_qs,
                logger=logger,
                publisher=publisher,
            )

        return _handle

    def _initiate_batch_stop_handler_factory():
        def _handle(command):
            initiate_batch_stop.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                pp_qry_srv=provisioned_products_qs,
            )

        return _handle

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            sync_provisioned_product_state_command.SyncProvisionedProductStateCommand,
            _sync_handler_factory(),
        )
        .register_handler(
            cleanup_provisioned_products_command.CleanupProvisionedProductsCommand,
            _cleanup_provisioned_products_command_handler_factory(),
        )
        .register_handler(
            initiate_provisioned_product_batch_stop_command.InitiateProvisionedProductBatchStopCommand,
            _initiate_batch_stop_handler_factory(),
        )
    )
    return Dependencies(
        command_bus=command_bus,
        provisioned_products_domain_qry_srv=provisioned_products_domain_qs,
        projects_domain_query_service=projects_domain_qs,
        provisioned_product_cleanup_config=provisioned_product_cleanup_config,
    )
