import enum
import json
from typing import Optional

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import (
    aws_apigateway,
    aws_dynamodb,
    aws_ec2,
    aws_events,
    aws_iam,
    aws_pipes_alpha,
    aws_scheduler,
    aws_ssm,
)

from app.packaging import domain
from infra import config, constants
from infra.auth import packaging_auth, packaging_auth_schema
from infra.backend import vew_bounded_context_stack
from infra.constructs import (
    backend_app_api_auth,
    backend_app_entrypoints,
    backend_app_event_bus,
    backend_app_openapi,
    backend_app_storage,
    shared_layer,
)
from infra.constructs.component_version_testing import (
    component_version_testing_state_machine,
)
from infra.constructs.pipes import topic_to_event_bus_pipe
from infra.constructs.recipe_version_testing import recipe_version_testing_state_machine
from infra.constructs.sns import topic
from infra.helpers import ops_monitoring

# Global variables
GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN = "gsi_custom_query_by_build_version_arn"
GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION = "gsi_custom_query_by_recipe_id_and_version"
GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY = "gsi_custom_query_by_status_key"
GSI_NAME_ENTITIES = "gsi_entities"
GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
GSI_NAME_IMAGE_UPSTREAM_ID = "gsi_image_upstream_id"
IMAGE_KEY_NAME = constants.IMAGE_SHARING_KEY_NAME
PRODUCT_PACKAGING_ADMIN_ROLE = constants.PRODUCT_PACKAGING_ADMIN_ROLE
PRODUCT_PACKAGING_INSTANCE_PROFILE_NAME = constants.PRODUCT_PACKAGING_INSTANCE_PROFILE
PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP_NAME = constants.PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP
PRODUCT_PACKAGING_TOPIC_NAME = constants.PRODUCT_PACKAGING_TOPIC
SYSTEM_CONFIGURATION_MAPPING = {
    "Linux": {
        "amd64": {
            "Ubuntu 24": {
                "ami_ssm_param_name": "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id",
                "command_ssm_document_name": "AWS-RunShellScript",
                "instance_type": "m8i.2xlarge",
                "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace",
                "setup_testing_environment_command": "curl https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe --output /usr/bin/awstoe && chmod +x /usr/bin/awstoe",
            },
        },
        "arm64": {
            "Ubuntu 24": {
                "ami_ssm_param_name": "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id",
                "command_ssm_document_name": "AWS-RunShellScript",
                "instance_type": "m8g.2xlarge",
                "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace",
                "setup_testing_environment_command": "curl https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/arm64/awstoe --output /usr/bin/awstoe && chmod +x /usr/bin/awstoe",
            },
        },
    },
    "Windows": {
        "amd64": {
            "Microsoft Windows Server 2025": {
                "ami_ssm_param_name": "/aws/service/ami-windows-latest/Windows_Server-2025-English-Core-Base",
                "command_ssm_document_name": "AWS-RunPowerShellScript",
                "instance_type": "m8i.2xlarge",
                "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace; exit $LastExitCode",
                "setup_testing_environment_command": "Invoke-WebRequest https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/windows/amd64/awstoe.exe -OutFile C:\\Windows\\system32\\awstoe.exe ; exit $LastExitCode",
            },
        },
    },
}
PIPELINES_CONFIGURATION_MAPPING = {
    "Pipelines": {
        "amd64": {
            "allowed_build_instance_types": [
                "m8a.2xlarge",
                "m8i.2xlarge",
                "m8a.4xlarge",
                "m8i.4xlarge",
            ]
        },
        "arm64": {"allowed_build_instance_types": ["m8g.2xlarge", "m8g.4xlarge"]},
    }
}
VEW_SERVICE = "Packaging"


class Entrypoint(enum.StrEnum):
    API = "api"
    DOMAIN_EVENTS = "domain-events"
    IMAGE_BUILDER_EVENTS = "image-builder-events"
    COMPONENT_VERSION_TESTING = "component-version-testing"
    RECIPE_VERSION_TESTING = "recipe-version-testing"


class PackagingAppStack(vew_bounded_context_stack.VEWBoundedContextStack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        custom_api_domain: Optional[str],
        product_packaging_topic: topic.Topic,
        provision_private_endpoint: bool = False,
        vpc_endpoint: Optional[aws_ec2.IVpcEndpoint] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, app_config=app_config, **kwargs)

        self._tools_account_id = None
        self._image_service_account_id = None

        self.configure_event_buses(app_config, product_packaging_topic)

        audit_logging_key_arn = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "SharedSharedAuditLogKeyARN",
            constants.AUDIT_LOGGING_KEY_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        audit_logging_key_name = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "SharedSharedAuditLogKeyName",
            constants.AUDIT_LOGGING_KEY_NAME_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        system_configuration_mapping = aws_ssm.StringParameter(
            self,
            "SystemConfigurationMapping",
            description="System Configuration Mapping.",
            parameter_name=f"/{app_config.format_resource_name('shared')}/system-configuration-mapping",
            string_value=json.dumps(SYSTEM_CONFIGURATION_MAPPING),
            tier=aws_ssm.ParameterTier.ADVANCED,
        )
        pipelines_configuration_mapping = aws_ssm.StringParameter(
            self,
            "PipelinesConfigurationMapping",
            description="Pipelines Configuration Mapping.",
            parameter_name=f"/{app_config.format_resource_name('shared')}/pipelines-configuration-mapping",
            string_value=json.dumps(PIPELINES_CONFIGURATION_MAPPING),
            tier=aws_ssm.ParameterTier.ADVANCED,
        )

        ami_factory_subnet_names = ",".join(list(app_config.component_specific.get("ami-factory-subnet-names")))

        # EventBridge scheduler group
        self._scheduler_group = aws_scheduler.CfnScheduleGroup(
            self,
            "SchedulerGroup",
            name=f"{app_config.bounded_context_name}",
        )

        # DynamoDB
        self._storage = backend_app_storage.BackendAppStorage(self, "PackagingAppStorage", app_config)

        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN,
            partition_key=aws_dynamodb.Attribute(name="QPK_ARN", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION,
            partition_key=aws_dynamodb.Attribute(name="QPK_RECIPE", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="QSK_VERSION", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY,
            partition_key=aws_dynamodb.Attribute(name="GSI_PK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="GSI_SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_ENTITIES,
            partition_key=aws_dynamodb.Attribute(name="entity", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_INVERTED_PK,
            partition_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_IMAGE_UPSTREAM_ID,
            partition_key=aws_dynamodb.Attribute(name="imageUpstreamId", type=aws_dynamodb.AttributeType.STRING),
        )

        # Lambda functions
        self._packaging_app_layer = shared_layer.SharedLayer(
            self,
            "PackagingAppLayer",
            layer_version_name="packaging_app_libraries",
            entry="app/packaging/libraries",
        )

        self._shared_app_layer = shared_layer.SharedLayer(
            self,
            "SharedAppLayer",
            layer_version_name="shared_app_libraries",
            entry="app/shared",
        )

        domain_event_handler_name = app_config.format_resource_name(Entrypoint.DOMAIN_EVENTS)
        image_builder_event_handler_name = app_config.format_resource_name(Entrypoint.IMAGE_BUILDER_EVENTS)
        component_version_testing_handler_name = app_config.format_resource_name(Entrypoint.COMPONENT_VERSION_TESTING)
        recipe_version_testing_handler_name = app_config.format_resource_name(Entrypoint.RECIPE_VERSION_TESTING)

        self._backend_app = backend_app_entrypoints.BackendAppEntrypoints(
            self,
            "PackagingApp",
            app_config=app_config,
            global_env_vars={
                "POWERTOOLS_SERVICE_NAME": VEW_SERVICE,
            },
            app_entry_points=[
                backend_app_entrypoints.AppEntryPoint(
                    name=app_config.format_resource_name(Entrypoint.API),
                    app_root="app",
                    lambda_root="app/packaging",
                    entry="app/packaging/entrypoints/api",
                    environment={
                        "ADMIN_ROLE": PRODUCT_PACKAGING_ADMIN_ROLE,
                        "AMI_FACTORY_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "AMI_FACTORY_VPC_NAME": app_config.component_specific.get("ami-factory-vpc-name"),
                        "AMI_FACTORY_SUBNET_NAMES": ami_factory_subnet_names,
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "API_BASE_PATH": constants.CUSTOM_DNS_API_PATH_PACKAGING,
                        "STRIP_PREFIXES": constants.CUSTOM_DNS_API_PATH_PACKAGING,
                        "COMPONENT_S3_BUCKET_NAME": app_config.component_specific["component-s3-bucket-name"].format(
                            environment=app_config.environment,
                            image_service_account_id=self.get_image_service_account_id(app_config),
                            region=app_config.region,
                        ),
                        "CUSTOM_DNS": custom_api_domain,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN": GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN,
                        "GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION": GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION,
                        "GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY": GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
                        "GSI_NAME_IMAGE_UPSTREAM_ID": GSI_NAME_IMAGE_UPSTREAM_ID,
                        "IMAGE_KEY_NAME": "-".join(
                            [
                                app_config.get_organization_prefix(),
                                app_config.get_application_prefix(),
                                IMAGE_KEY_NAME,
                            ]
                        ),
                        "INSTANCE_PROFILE_NAME": PRODUCT_PACKAGING_INSTANCE_PROFILE_NAME,
                        "INSTANCE_SECURITY_GROUP_NAME": PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP_NAME,
                        "SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME": system_configuration_mapping.parameter_name,
                        "PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME": pipelines_configuration_mapping.parameter_name,
                        "TABLE_NAME": self._storage.table.table_name,
                        "TOPIC_NAME": PRODUCT_PACKAGING_TOPIC_NAME,
                        "LAYER_VERSION": self._shared_app_layer.layer.layer_version_arn,
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "secretsmanager:GetSecretValue",
                                    "secretsmanager:DescribeSecret",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    audit_logging_key_arn,
                                ],
                            )
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::{self.get_image_service_account_id(app_config)}:role/{PRODUCT_PACKAGING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: system_configuration_mapping.grant_read(lambda_f),
                        lambda lambda_f: pipelines_configuration_mapping.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["api-lambda-reserved-concurrency"],
                    provisioned_concurrency=app_config.component_specific["api-lambda-provisioned-concurrency"],
                    timeout=aws_cdk.Duration.seconds(5),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=component_version_testing_handler_name,
                    app_root="app",
                    lambda_root="app/packaging",
                    entry="app/packaging/entrypoints/component_version_testing",
                    environment={
                        "ADMIN_ROLE": PRODUCT_PACKAGING_ADMIN_ROLE,
                        "AMI_FACTORY_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "AMI_FACTORY_VPC_NAME": app_config.component_specific.get("ami-factory-vpc-name"),
                        "AMI_FACTORY_SUBNET_NAMES": ami_factory_subnet_names,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
                        "INSTANCE_PROFILE_NAME": PRODUCT_PACKAGING_INSTANCE_PROFILE_NAME,
                        "INSTANCE_SECURITY_GROUP_NAME": PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP_NAME,
                        "SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME": system_configuration_mapping.parameter_name,
                        "PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME": pipelines_configuration_mapping.parameter_name,
                        "TABLE_NAME": self._storage.table.table_name,
                        "VOLUME_SIZE": str(app_config.component_specific.get("volume-size")),
                        "SSM_RUN_COMMAND_TIMEOUT": str(app_config.component_specific.get("ssm-run-command-timeout")),
                        "COMPONENT_TEST_S3_BUCKET_NAME": app_config.component_specific[
                            "component-test-s3-bucket-name"
                        ].format(
                            environment=app_config.environment,
                            image_service_account_id=self.get_image_service_account_id(app_config),
                            region=app_config.region,
                        ),
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::{self.get_image_service_account_id(app_config)}:role/{PRODUCT_PACKAGING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: system_configuration_mapping.grant_read(lambda_f),
                        lambda lambda_f: pipelines_configuration_mapping.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific[
                        "component-version-testing-reserved-concurrency"
                    ],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(180),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=recipe_version_testing_handler_name,
                    app_root="app",
                    lambda_root="app/packaging",
                    entry="app/packaging/entrypoints/recipe_version_testing",
                    environment={
                        "ADMIN_ROLE": PRODUCT_PACKAGING_ADMIN_ROLE,
                        "AMI_FACTORY_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "AMI_FACTORY_VPC_NAME": app_config.component_specific.get("ami-factory-vpc-name"),
                        "AMI_FACTORY_SUBNET_NAMES": ami_factory_subnet_names,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
                        "INSTANCE_PROFILE_NAME": PRODUCT_PACKAGING_INSTANCE_PROFILE_NAME,
                        "INSTANCE_SECURITY_GROUP_NAME": PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP_NAME,
                        "SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME": system_configuration_mapping.parameter_name,
                        "PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME": pipelines_configuration_mapping.parameter_name,
                        "TABLE_NAME": self._storage.table.table_name,
                        "SSM_RUN_COMMAND_TIMEOUT": str(app_config.component_specific.get("ssm-run-command-timeout")),
                        "RECIPE_TEST_S3_BUCKET_NAME": app_config.component_specific[
                            "recipe-test-s3-bucket-name"
                        ].format(
                            environment=app_config.environment,
                            image_service_account_id=self.get_image_service_account_id(app_config),
                            region=app_config.region,
                        ),
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::{self.get_image_service_account_id(app_config)}:role/{PRODUCT_PACKAGING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: system_configuration_mapping.grant_read(lambda_f),
                        lambda lambda_f: pipelines_configuration_mapping.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["recipe-version-testing-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(180),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=domain_event_handler_name,
                    app_root="app",
                    lambda_root="app/packaging",
                    entry="app/packaging/entrypoints/domain_event_handler",
                    environment={
                        "ADMIN_ROLE": PRODUCT_PACKAGING_ADMIN_ROLE,
                        "AMI_FACTORY_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "AMI_FACTORY_VPC_NAME": app_config.component_specific.get("ami-factory-vpc-name"),
                        "AMI_FACTORY_SUBNET_NAMES": ami_factory_subnet_names,
                        "COMPONENT_S3_BUCKET_NAME": app_config.component_specific["component-s3-bucket-name"].format(
                            environment=app_config.environment,
                            image_service_account_id=self.get_image_service_account_id(app_config),
                            region=app_config.region,
                        ),
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "GSI_CUSTOM_STATUS_KEY": GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
                        "IMAGE_KEY_NAME": "-".join(
                            [
                                app_config.get_organization_prefix(),
                                app_config.get_application_prefix(),
                                IMAGE_KEY_NAME,
                            ]
                        ),
                        "INSTANCE_PROFILE_NAME": PRODUCT_PACKAGING_INSTANCE_PROFILE_NAME,
                        "INSTANCE_SECURITY_GROUP_NAME": PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP_NAME,
                        "RECIPE_S3_BUCKET_NAME": app_config.component_specific["recipe-s3-bucket-name"].format(
                            environment=app_config.environment,
                            image_service_account_id=self.get_image_service_account_id(app_config),
                            region=app_config.region,
                        ),
                        "PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME": pipelines_configuration_mapping.parameter_name,
                        "TABLE_NAME": self._storage.table.table_name,
                        "TOPIC_NAME": PRODUCT_PACKAGING_TOPIC_NAME,
                        "SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME": system_configuration_mapping.parameter_name,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: pipelines_configuration_mapping.grant_read(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::{self.get_image_service_account_id(app_config)}:role/{PRODUCT_PACKAGING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                    ],
                    reserved_concurrency=app_config.component_specific["domain-events-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.minutes(5),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=image_builder_event_handler_name,
                    app_root="app",
                    lambda_root="app/packaging",
                    entry="app/packaging/entrypoints/image_builder_event_handler",
                    environment={
                        "ADMIN_ROLE": PRODUCT_PACKAGING_ADMIN_ROLE,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
                        "GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN": GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN,
                        "GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION": GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION,
                        "GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY": GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY,
                        "GSI_NAME_IMAGE_UPSTREAM_ID": GSI_NAME_IMAGE_UPSTREAM_ID,
                        "TABLE_NAME": self._storage.table.table_name,
                        "TOPIC_NAME": PRODUCT_PACKAGING_TOPIC_NAME,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: pipelines_configuration_mapping.grant_read(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::{self.get_image_service_account_id(app_config)}:role/{PRODUCT_PACKAGING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                    ],
                    reserved_concurrency=app_config.component_specific["image-builder-events-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=256,
                    asynchronous=True,
                ),
            ],
            app_layers=[
                self._packaging_app_layer.layer,
                self._shared_app_layer.layer,
            ],
        ).with_access_token_tag(app_config.environment_config.get("role-access-token", None))

        # API Gateway for UI client access
        api_acl_arn = None
        if not provision_private_endpoint:
            api_acl_arn = aws_ssm.StringParameter.from_string_parameter_attributes(
                self,
                "ui-waf-api-acl-arn",
                parameter_name=constants.WAF_API_ACL_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
            ).string_value

        self._open_api = backend_app_openapi.BackendAppOpenApi(
            self,
            "PackagingAppOpenApi",
            app_config,
            handler=self._backend_app.app_entries_function_aliases[app_config.format_resource_name("api")],
            schema_directory="app/packaging/entrypoints/api/schema/",
            schema="proserve-workbench-packaging-api-schema.yaml",
            api_version="v1",
            version_description="First release of Packaging API",
            cache_enabled=False,
            waf_acl_arn=api_acl_arn,
            custom_domain=custom_api_domain,
            base_path=constants.CUSTOM_DNS_API_PATH_PACKAGING,
            endpoint_type=(
                aws_apigateway.EndpointType.PRIVATE
                if provision_private_endpoint
                else aws_apigateway.EndpointType.REGIONAL
            ),
            vpc_endpoint=vpc_endpoint if provision_private_endpoint else None,
            cedar_policy_config=backend_app_api_auth.CedarPolicyConfig(
                cedar_schema=packaging_auth_schema.packaging_schema,
                cedar_policies=packaging_auth.packaging_bc_auth_policies,
            ),
        )

        # Component version testing step function
        self._component_testing_state_machine = (
            component_version_testing_state_machine.ComponentVersionTestingStateMachine(
                self,
                "ComponentVersionTestingStateMachine",
                app_config=app_config,
                component_version_testing_lambda=self._backend_app.app_entries_functions[
                    component_version_testing_handler_name
                ],
            )
        )

        # Recipe version testing step function
        self._recipe_testing_state_machine = recipe_version_testing_state_machine.RecipeVersionTestingStateMachine(
            self,
            "RecipeVersionTestingStateMachine",
            app_config=app_config,
            recipe_version_testing_lambda=self._backend_app.app_entries_functions[recipe_version_testing_handler_name],
        )

        # Subscribe to domain events
        self._event_bus.l3_event_bus.subscribe_to_events(
            name="packaging-domain-events-rule",
            lambda_function=self._backend_app.app_entries_functions[domain_event_handler_name],
            events=[
                "ComponentVersionCreationStarted",
                "ComponentVersionReleaseCompleted",
                "ComponentVersionRetirementStarted",
                "ComponentVersionUpdateStarted",
                "PipelineCreationStarted",
                "PipelineRetirementStarted",
                "PipelineUpdateStarted",
                "RecipeVersionCreationStarted",
                "RecipeVersionReleaseCompleted",
                "RecipeVersionRetirementStarted",
                "RecipeVersionUpdateStarted",
                "RecipeVersionUpdateOnComponentUpdateRequested",
            ],
        )
        self._event_bus.l3_event_bus.subscribe_to_events(
            name="packaging-comp-testing-event-rule",
            state_machine=self._component_testing_state_machine.state_machine,
            events=[
                "ComponentVersionPublished",
            ],
        )
        self._event_bus.l3_event_bus.subscribe_to_events(
            name="packaging-reci-testing-event-rule",
            state_machine=self._recipe_testing_state_machine.state_machine,
            events=[
                "RecipeVersionPublished",
            ],
        )

        # Subscribe to external events
        self.subscribe_to_external_events(app_config)

        # Stack based suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/PackagingAppStack/ComponentVersionTestingStateMachine/ComponentVersionTestingStateMachine/EventsRole/DefaultPolicy/Resource",
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
            ],
        )

        # Stack based suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/PackagingAppStack/RecipeVersionTestingStateMachine/RecipeVersionTestingStateMachine/EventsRole/DefaultPolicy/Resource",
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path=f"/PackagingAppStack/PackagingApp/{app_config.format_resource_name("api")}/BackendAppFunction/ServiceRole/DefaultPolicy/Resource",
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Project and Integration IDs are not known beforehand.",
                ),
            ],
        )

        # Configure monitoring
        self.__configure_ops(app_config)

    def configure_event_buses(self, app_config: config.AppConfig, product_packaging_topic: topic.Topic):
        self._event_bus = backend_app_event_bus.BackendAppEventBus(
            self, "domain-event-bus", app_config, event_bus_name="domain-events"
        )

        self._tools_event_bus = backend_app_event_bus.BackendAppEventBus(
            self,
            "tools-integration-event-bus",
            app_config,
            event_bus_name="tools-integration-events",
        )

        self.configure_tools_integration_event_bus(app_config, product_packaging_topic)

    def __configure_ops(self, app_config: config.AppConfig):
        (
            ops_monitoring.OpsMonitoringBuilder(
                self,
                app_config.format_resource_name("ops-dashboard"),
                constants.VEW_NAMESPACE,
                VEW_SERVICE,
                app_config,
            )
            .with_lambda_functions(self._backend_app.app_entries.values())
            .with_dynamodb_table(self._storage.table)
            .with_api_gateway(self._open_api.api)
            .with_step_functions(
                [
                    self._component_testing_state_machine.state_machine,
                    self._recipe_testing_state_machine.state_machine,
                ]
            )
            .with_command_monitoring(domain_module=domain)
            .with_domain_event_monitoring(domain_module=domain)
            .build()
        )

    def configure_tools_integration_event_bus(self, app_config: config.AppConfig, product_packaging_topic: topic.Topic):
        image_service_account_id = self.get_image_service_account_id(app_config)
        if image_service_account_id:
            self._tools_event_bus.allow_publish_from_account(image_service_account_id)

        # Pipe to forward events from the product packaging topic to the tools integration event bus
        topic_to_event_bus_pipe.TopicToEventBusPipe(
            self,
            "PackagingTopicToEventBusPipe",
            create_key=True,
            detail_type=constants.PRODUCT_PACKAGING_EVENTS_DETAIL_TYPE,
            description="Pipe to forward product packaging-related events from SNS to EventBridge.",
            event_bus=self._tools_event_bus.event_bus,
            input_transformation=aws_pipes_alpha.InputTransformation.from_object(
                {
                    "Type": "<$.body.Type>",
                    "MessageId": "<$.body.MessageId>",
                    "TopicArn": "<$.body.TopicArn>",
                    "Subject": "<$.body.Subject>",
                    "Message": "<$.body.Message>",
                    "Timestamp": "<$.body.Timestamp>",
                }
            ),
            pipe_name=app_config.format_resource_name("pipe"),
            resources=[],  # We fetch the resources from the message
            source=constants.PRODUCT_PACKAGING_EVENTS_SOURCE,
            topics=[product_packaging_topic.topic],
        )

    def subscribe_to_external_events(self, app_config: config.AppConfig):
        self._tools_event_bus.add_rule_with_lambda_target(
            duration_in_minutes=720,
            event_pattern=aws_events.EventPattern(
                detail_type=aws_events.Match.exact_string("Image Builder SNS notification"),
                source=aws_events.Match.prefix("Workbench Image Service"),
            ),
            lambda_function=self._backend_app.app_entries_functions[
                app_config.format_resource_name(Entrypoint.IMAGE_BUILDER_EVENTS)
            ],
            max_retries=3,
            name="image-builder-event-rule",
        )

    def get_image_service_account_id(self, app_config: config.AppConfig):
        image_service_account_param_name = "image-service-account-id-ssm-param"

        if not self._image_service_account_id and app_config.environment_config[image_service_account_param_name]:
            self._image_service_account_id = aws_ssm.StringParameter.from_string_parameter_name(
                self,
                "image_service_account",
                string_parameter_name=app_config.environment_config[image_service_account_param_name].format(
                    environment=app_config.environment
                ),
            ).string_value

        return self._image_service_account_id

    @property
    def backend_app(self) -> backend_app_entrypoints.BackendAppEntrypoints:
        return self._backend_app

    @property
    def internal_api(self) -> backend_app_openapi.BackendAppOpenApi | None:
        return self._open_api

    @property
    def table(self) -> aws_dynamodb.ITable | None:
        return self._storage.table

    @property
    def api(self) -> backend_app_openapi.BackendAppOpenApi:
        return self._open_api

    @property
    def packaging_table(self) -> backend_app_storage.BackendAppStorage:
        return self._storage

    @property
    def packaging_table_name(self) -> str:
        return self._storage.table_name

    @property
    def packaging_table_arn(self) -> str:
        return self._storage.table_arn

    @property
    def packaging_entry(self) -> backend_app_entrypoints.BackendAppEntrypoints:
        return self._backend_app
