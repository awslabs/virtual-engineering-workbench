import boto3
import boto3.session
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from mypy_boto3_ec2 import client as ec2_client
from mypy_boto3_ssm import client as ssm_client
from pydantic import BaseModel, ConfigDict

from app.provisioning.adapters.query_services import (
    aws_networking_query_service,
    dynamodb_maintenance_windows_query_service,
    dynamodb_products_query_service,
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
)
from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.command_handlers.product_provisioning import (
    authorize_user_ip_address,
    launch,
    remove,
    remove_by_admin,
    start_update,
)
from app.provisioning.domain.command_handlers.provisioned_product_state import (
    initiate_start,
    initiate_stop,
    initiate_stop_by_admin,
)
from app.provisioning.domain.command_handlers.user_profile import update as update_user_profile_command_handler
from app.provisioning.domain.commands.product_provisioning import (
    authorize_user_ip_address_command,
    launch_product_command,
    remove_provisioned_product_command,
    remove_provisioned_products_command,
    start_provisioned_product_update_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_start_command,
    initiate_provisioned_product_stop_command,
    initiate_provisioned_products_stop_command,
)
from app.provisioning.domain.commands.user_profile import update_user_profile_command
from app.provisioning.domain.query_services import (
    products_domain_query_service,
    provisioned_products_domain_query_service,
    provisioning_infrastructure_domain_query_service,
    user_profile_domain_query_service,
    versions_domain_query_service,
)
from app.provisioning.entrypoints.api import config
from app.shared.adapters.auth import temporary_credential_provider
from app.shared.adapters.feature_toggling import (
    backend_feature_toggles,
    frontend_feature_toggles,
)
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
from app.shared.api import (
    aws_events_api,
    aws_scheduler_api,
    bounded_contexts,
    service_registry,
    ssm_parameter_service,
)
from app.shared.ddd import aggregate
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    application_version_frontend: str  # type: ignore[assignment] # noqa: E501)
    application_version_backend: str  # type: ignore[assignment] # noqa: E501)
    command_bus: command_bus.CommandBus
    products_domain_qry_srv: products_domain_query_service.ProductsDomainQueryService
    versions_domain_qry_srv: versions_domain_query_service.VersionsDomainQueryService
    virtual_targets_domain_qry_srv: provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService
    user_profile_domain_qry_srv: user_profile_domain_query_service.UserProfileDomainQueryService
    prov_infra_qry_srv: provisioning_infrastructure_domain_query_service.ProvisioningInfrastructureDomainQueryService
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

    scheduler_client = session.client("scheduler", region_name=app_config.get_default_region())
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=scheduler_client,
        bounded_context_name=app_config.get_bounded_context_name(),
        role_arn=app_config.get_lambda_iam_role(),
        event_bus_arn=app_config.get_domain_event_bus_name(),
    )

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

    application_version_frontend_value = parameters.get_parameter(
        app_config.get_application_version_frontend_param_name()
    )
    application_version_backend_value = parameters.get_parameter(
        app_config.get_application_version_backend_param_name()
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

    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=dynamodb,
        table_name=app_config.get_table_name(),
        logger=logger,
    ).register_migrations(migrations_config(provisioned_products_qs=provisioned_products_qry_srv)).migrate()

    temp_cred_provider = temporary_credential_provider.TemporaryCredentialProvider(
        sts_client=session.client("sts", region_name=app_config.get_default_region()),
        ctx=app,
    )

    experimental_provisioned_product_per_project_limit = int(
        parameters.get_parameter(app_config.get_experimental_provisioned_product_per_project_limit_param_name())
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

    def _get_ec2_boto_client(aws_account_id: str, region: str, user_id: str) -> ec2_client.EC2Client:
        return _get_boto_client_for(
            client_name="ec2",
            aws_account_id=aws_account_id,
            region=region,
            user_id=user_id,
        )

    parameter_srv = ssm_parameter_service_v2.AWSParameterService(
        ssm_boto_client_provider=_get_ssm_boto_client,
        sm_boto_client_provider=_get_sm_boto_client,
    )

    instance_mgmt_srv = ec2_instance_management_service.EC2InstanceManagementService(
        ec2_boto_client_provider=_get_ec2_boto_client
    )

    provisioned_products_domain_qry_srv = (
        provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService(
            provisioned_products_qry_srv=provisioned_products_qry_srv,
            version_qry_srv=versions_qry_srv,
            networking_qry_srv=networking_qry_srv,
            parameter_srv=parameter_srv,
        )
    )

    maintenance_windows_qry_srv = dynamodb_maintenance_windows_query_service.DynamoDBMaintenanceWindowsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_primary_key(),
    )

    fe_feature_toggles_srv = frontend_feature_toggles.FrontendFeatureToggles(
        logger=logger,
        parameter_service=ssm_api_instance,
        parameter_name=app_config.get_feature_toggles_param_name(),
    )

    be_feature_toggles_srv = backend_feature_toggles.from_environment_variables()

    user_profile_domain_qry_srv = user_profile_domain_query_service.UserProfileDomainQueryService(
        uow=uow,
        parameter_srv=ssm_api_instance,
        maintenance_windows_qry_srv=maintenance_windows_qry_srv,
        feature_toggles=fe_feature_toggles_srv,
        enabled_regions_param_name=app_config.get_enabled_workbench_regions_param_name(),
        application_version_param_name=app_config.get_application_version_param_name(),
    )

    publisher = aggregate.AggregatePublisher(
        mb=mb,
        uow=uow,
    )

    aws_api_instance = service_registry.ServiceRegistry.from_config(
        app_config=app_config,
        ssm_client=boto3.client("ssm", region_name=app_config.get_default_region()),
        logger=logger,
    ).api_for(bounded_contexts.BoundedContext.PROJECTS)
    projects_api_qs = projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)

    all_subnet_selector = networking_helpers.get_all_subnets_selector(
        app_config.get_provisioning_subnet_selector(),
        tag=app_config.get_provisioning_subnet_selector_tag(),
    )

    prov_infra_qry_srv = provisioning_infrastructure_domain_query_service.ProvisioningInfrastructureDomainQueryService(
        parameter_srv=parameter_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        all_subnets_selector=all_subnet_selector,
        spoke_account_vpc_id_param_name=app_config.get_spoke_account_vpc_id_param_name(),
        service_name=app_config.get_bounded_context_name(),
    )

    def _authorize_user_ip_address_handler_factory():
        def _handle(command):
            authorize_user_ip_address.handle(
                command=command,
                virtual_targets_qs=provisioned_products_qry_srv,
                parameter_srv=parameter_srv,
                instance_mgmt_srv=instance_mgmt_srv,
                logger=logger,
                spoke_account_vpc_id_param_name=app_config.get_spoke_account_vpc_id_param_name(),
                authorize_user_ip_address_param_value=app_config.get_authorize_user_ip_address_param_value(),
            )

        return _handle

    def _launch_provisioned_product_handler_factory():
        def _handle(command):
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

        return _handle

    def _remove_provisioned_product_handler_factory():
        def _handle(command):
            remove.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                virtual_targets_qs=provisioned_products_qry_srv,
            )

        return _handle

    def _remove_provisioned_products_handler_factory():
        def _handle(command):
            remove_by_admin.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                virtual_targets_qs=provisioned_products_qry_srv,
            )

        return _handle

    def _start_provisioned_product_update_handler_factory():
        def _handle(command):
            start_update.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                provisioned_products_qs=provisioned_products_qry_srv,
                versions_qs=versions_qry_srv,
            )

        return _handle

    def _initiate_start_provisioned_product_handler_factory():
        def _handle(command):
            initiate_start.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                virtual_targets_qs=provisioned_products_qry_srv,
            )

        return _handle

    def _initiate_stop_provisioned_product_handler_factory():
        def _handle(command):
            initiate_stop.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                virtual_targets_qs=provisioned_products_qry_srv,
            )

        return _handle

    def _initiate_stop_provisioned_products_handler_factory():
        def _handle(command):
            initiate_stop_by_admin.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                virtual_targets_qs=provisioned_products_qry_srv,
            )

        return _handle

    def _update_user_profile_handler_factory():
        def _handle(command):
            update_user_profile_command_handler.handle(
                command=command,
                publisher=publisher,
                uow=uow,
                maintenance_windows_qry_srv=maintenance_windows_qry_srv,
                logger=logger,
            )

        return _handle

    cmd_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            authorize_user_ip_address_command.AuthorizeUserIpAddressCommand,
            _authorize_user_ip_address_handler_factory(),
        )
        .register_handler(
            launch_product_command.LaunchProductCommand,
            _launch_provisioned_product_handler_factory(),
        )
        .register_handler(
            remove_provisioned_product_command.RemoveProvisionedProductCommand,
            _remove_provisioned_product_handler_factory(),
        )
        .register_handler(
            remove_provisioned_products_command.RemoveProvisionedProductsCommand,
            _remove_provisioned_products_handler_factory(),
        )
        .register_handler(
            initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand,
            _initiate_start_provisioned_product_handler_factory(),
        )
        .register_handler(
            initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand,
            _initiate_stop_provisioned_product_handler_factory(),
        )
        .register_handler(
            initiate_provisioned_products_stop_command.InitiateProvisionedProductsStopCommand,
            _initiate_stop_provisioned_products_handler_factory(),
        )
        .register_handler(
            update_user_profile_command.UpdateUserProfileCommand,
            _update_user_profile_handler_factory(),
        )
        .register_handler(
            start_provisioned_product_update_command.StartProvisionedProductUpdateCommand,
            _start_provisioned_product_update_handler_factory(),
        )
    )

    return Dependencies(
        application_version_frontend=application_version_frontend_value,
        application_version_backend=application_version_backend_value,
        command_bus=cmd_bus,
        products_domain_qry_srv=products_domain_qry_srv,
        versions_domain_qry_srv=versions_domain_qry_srv,
        virtual_targets_domain_qry_srv=provisioned_products_domain_qry_srv,
        user_profile_domain_qry_srv=user_profile_domain_qry_srv,
        prov_infra_qry_srv=prov_infra_qry_srv,
    )
