import boto3
import boto3.session
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from mypy_boto3_ssm import client as ssm_client
from pydantic import BaseModel, ConfigDict

from app.provisioning.adapters.query_services import (
    aws_networking_query_service,
    dynamodb_products_query_service,
    dynamodb_provisioned_products_query_service,
    dynamodb_versions_query_service,
    projects_api_query_service,
)
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.services import aws_parameter_service as ssm_parameter_service_v2
from app.provisioning.domain.command_handlers.product_provisioning import (
    launch,
    remove,
)
from app.provisioning.domain.command_handlers.provisioned_product_state import (
    initiate_start,
    initiate_stop,
)
from app.provisioning.domain.commands.product_provisioning import (
    launch_product_command,
    remove_provisioned_product_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_start_command,
    initiate_provisioned_product_stop_command,
)
from app.provisioning.domain.query_services import (
    products_domain_query_service,
    provisioned_products_domain_query_service,
    versions_domain_query_service,
)
from app.provisioning.entrypoints.s2s_api import config
from app.shared.adapters.auth import temporary_credential_provider
from app.shared.adapters.feature_toggling import backend_feature_toggles
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.api import aws_api, aws_events_api, ssm_parameter_service
from app.shared.ddd import aggregate
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    products_domain_qry_srv: products_domain_query_service.ProductsDomainQueryService
    versions_domain_qry_srv: versions_domain_query_service.VersionsDomainQueryService
    virtual_targets_domain_qry_srv: provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService
    model_config = ConfigDict(arbitrary_types_allowed=True)


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: temporary_credential_provider.SupportsContextManager,
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

    ssm_api_instance = ssm_parameter_service.SSMApi(region=app_config.get_default_region(), session=session)

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

    products_qry_srv = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
    )

    networking_qry_srv = aws_networking_query_service.AWSNetworkingService(
        ssm_api=ssm_api_instance,
        network_ip_map_param_name=app_config.get_network_ip_map_param_name(),
        logger=logger,
        available_networks_param_name=app_config.get_available_networks_param_name(),
    )

    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_qry_srv,
        networking_qry_srv=networking_qry_srv,
    )

    versions_qry_srv = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_query_by_sc_pa_id=app_config.get_gsi_name_query_by_alt_key(),
    )

    versions_domain_qry_srv = versions_domain_query_service.VersionsDomainQueryService(version_qry_srv=versions_qry_srv)

    provisioned_products_qry_srv = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_primary_key(),
        gsi_custom_query_by_service_catalog_id=app_config.get_gsi_name_query_by_alt_key(),
        default_page_size=app_config.get_default_page_size(),
        gsi_custom_query_by_user_id=app_config.get_gsi_name_query_by_user_key(),
        gsi_custom_query_all=app_config.get_gsi_name_query_by_alt_key_2(),
        gsi_custom_query_by_product_id=app_config.get_gsi_name_query_by_alt_keys_3(),
        gsi_custom_query_by_project_id=app_config.get_gsi_name_query_by_alt_keys_4(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_alt_keys_5(),
    )

    temp_cred_provider = temporary_credential_provider.TemporaryCredentialProvider(
        sts_client=session.client("sts", region_name=app_config.get_default_region()),
        ctx=app,
    )

    experimental_provisioned_product_per_project_limit = int(
        parameters.get_parameter(app_config.get_experimental_provisioned_product_per_project_limit_param_name())
    )

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_projects_api_url(),
        region=app_config.get_default_region(),
        logger=logger,
    )
    projects_api_qs = projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)

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

    parameter_srv = ssm_parameter_service_v2.AWSParameterService(
        ssm_boto_client_provider=_get_ssm_boto_client,
        sm_boto_client_provider=_get_sm_boto_client,
    )

    provisioned_products_domain_qry_srv = (
        provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
            provisioned_products_qry_srv=provisioned_products_qry_srv,
            version_qry_srv=versions_qry_srv,
            networking_qry_srv=networking_qry_srv,
            parameter_srv=parameter_srv,
        )
    )

    be_feature_toggles_srv = backend_feature_toggles.from_environment_variables()

    publisher = aggregate.AggregatePublisher(
        mb=mb,
        uow=uow,
    )

    def __launch_provisioned_product_handler(command):
        launch.handle(
            command=command,
            publisher=publisher,
            products_qs=products_qry_srv,
            versions_qs=versions_qry_srv,
            logger=logger,
            provisioned_products_qs=provisioned_products_qry_srv,
            uow=uow,
            feature_toggles_srv=be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=experimental_provisioned_product_per_project_limit,
            projects_qs=projects_api_qs,
        )

    def __remove_provisioned_product_command_handler(command):
        remove.handle(
            command=command,
            publisher=publisher,
            logger=logger,
            virtual_targets_qs=provisioned_products_qry_srv,
        )

    def __initiate_start_provisioned_product_command_handler(command):
        initiate_start.handle(
            command=command,
            publisher=publisher,
            logger=logger,
            virtual_targets_qs=provisioned_products_qry_srv,
        )

    def __initiate_stop_provisioned_product_command_handler(command):
        initiate_stop.handle(
            command=command,
            publisher=publisher,
            logger=logger,
            virtual_targets_qs=provisioned_products_qry_srv,
        )

    cmd_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            remove_provisioned_product_command.RemoveProvisionedProductCommand,
            __remove_provisioned_product_command_handler,
        )
        .register_handler(
            launch_product_command.LaunchProductCommand,
            __launch_provisioned_product_handler,
        )
        .register_handler(
            initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand,
            __initiate_start_provisioned_product_command_handler,
        )
        .register_handler(
            initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand,
            __initiate_stop_provisioned_product_command_handler,
        )
    )

    return Dependencies(
        command_bus=cmd_bus,
        products_domain_qry_srv=products_domain_qry_srv,
        versions_domain_qry_srv=versions_domain_qry_srv,
        virtual_targets_domain_qry_srv=provisioned_products_domain_qry_srv,
    )
