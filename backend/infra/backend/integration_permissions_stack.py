from dataclasses import dataclass

import aws_cdk
import constructs
from aws_cdk import aws_apigateway

from infra import constants


@dataclass
class ApiToPathMapping:
    api: aws_apigateway.IRestApi
    base_path: str


@dataclass
class ApiIntegrationMapping:
    domain_name: str
    cert_arn: str
    mappings: list[ApiToPathMapping]


class ApiIntegrationPermissionsStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Import API URL CFN outputs
        publishing_api_url_internal_product_versions = aws_cdk.Fn.import_value(
            "publishing-api-internal-product-versions"
        )
        publishing_api_url_internal_product_version = aws_cdk.Fn.import_value("publishing-api-internal-product-version")
        projects_api_url_internal_user_assignments = aws_cdk.Fn.import_value("projects-api-internal-user-assignments")
        projects_api_url_internal_project_assignment = aws_cdk.Fn.import_value(
            "projects-api-internal-project-assignment"
        )
        projects_api_url_internal_projects = aws_cdk.Fn.import_value("projects-api-internal-projects")
        projects_api_url_internal_project_assignments = aws_cdk.Fn.import_value(
            "projects-api-internal-project-assignments"
        )

        # Provisioning BC permissions
        provisioning_scheduled_jobs_event_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-scheduled-jobs-handler-name"
        )
        provisioning_scheduled_jobs_event_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningScheduledJobsLambdaRole",
            provisioning_scheduled_jobs_event_handler_name_role_arn,
        )
        provisioning_api_event_handler_name_role_arn = aws_cdk.Fn.import_value("provisioning-api-event-handler-name")
        provisioning_api_event_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningApiLambdaRole",
            provisioning_api_event_handler_name_role_arn,
        )
        provisioning_s2s_api_event_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-s2s-api-event-handler-name"
        )
        provisioning_s2s_api_event_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningS2SApiLambdaRole",
            provisioning_s2s_api_event_handler_name_role_arn,
        )
        provisioning_projects_events_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-projects-events-handler-name"
        )
        provisioning_publishing_events_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-publishing-events-handler-name"
        )
        provisioning_domain_events_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-domain-events-handler-name"
        )
        provisioning_pp_events_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-provisioned-product-events-handler-name"
        )
        provisioning_pp_state_events_handler_name_role_arn = aws_cdk.Fn.import_value(
            "provisioning-provisioned-product-state-events-handler-name"
        )
        provisioning_project_events_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningProjectsLambdaRole",
            provisioning_projects_events_handler_name_role_arn,
        )
        provisioning_publishing_events_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningPublishingLambdaRole",
            provisioning_publishing_events_handler_name_role_arn,
        )
        provisioning_domain_events_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningDomainLambdaRole",
            provisioning_domain_events_handler_name_role_arn,
        )
        provisioning_pp_events_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningProvisionedProductLambdaRole",
            provisioning_pp_events_handler_name_role_arn,
        )
        provisioning_pp_state_events_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "ProvisioningProvisionedProductStateLambdaRole",
            provisioning_pp_state_events_handler_name_role_arn,
        )
        aws_cdk.aws_iam.ManagedPolicy(
            self,
            "ProvisioningCrossServicePolicy",
            roles=[
                provisioning_project_events_handler_name_role,
                provisioning_api_event_handler_name_role,
                provisioning_s2s_api_event_handler_name_role,
                provisioning_scheduled_jobs_event_handler_name_role,
                provisioning_publishing_events_handler_name_role,
                provisioning_domain_events_handler_name_role,
                provisioning_pp_events_handler_name_role,
                provisioning_pp_state_events_handler_name_role,
            ],
            statements=[
                aws_cdk.aws_iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    effect=aws_cdk.aws_iam.Effect.ALLOW,
                    resources=[
                        projects_api_url_internal_user_assignments,
                        projects_api_url_internal_project_assignment,
                        projects_api_url_internal_projects,
                        publishing_api_url_internal_product_versions,
                        publishing_api_url_internal_product_version,
                    ],
                )
            ],
        )

        # Publishing BC permissions
        publishing_product_sync_events_handler_name_role_arn = aws_cdk.Fn.import_value(
            "publishing-product-sync-events-handler-name"
        )
        publishing_product_sync_events_handler_name_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "PublishingProductSyncLambdaRole",
            publishing_product_sync_events_handler_name_role_arn,
        )
        aws_cdk.aws_iam.ManagedPolicy(
            self,
            "PublishingCrossServicePolicy",
            roles=[publishing_product_sync_events_handler_name_role],
            statements=[
                aws_cdk.aws_iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    effect=aws_cdk.aws_iam.Effect.ALLOW,
                    resources=[projects_api_url_internal_projects],
                )
            ],
        )

        # Authorization BC permissions
        auth_handler_role_arn = aws_cdk.Fn.import_value(constants.AUTH_BC_HANDLER_ROLE_ARN_EXPORT_NAME)
        auth_scheduled_jobs_handler_role_arn = aws_cdk.Fn.import_value(
            constants.AUTH_BC_SCHEDULED_JOB_HANDLER_ROLE_ARN_EXPORT_NAME
        )

        auth_handler_role = aws_cdk.aws_iam.Role.from_role_arn(self, "AuthorizationHandlerRole", auth_handler_role_arn)
        auth_scheduled_jobs_handler_role = aws_cdk.aws_iam.Role.from_role_arn(
            self,
            "AuthorizationScheduledJobsHandlerRole",
            auth_scheduled_jobs_handler_role_arn,
        )

        aws_cdk.aws_iam.ManagedPolicy(
            self,
            "AuthorizationHandlerCrossServicePolicy",
            roles=[
                auth_handler_role,
            ],
            statements=[
                aws_cdk.aws_iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    effect=aws_cdk.aws_iam.Effect.ALLOW,
                    resources=[
                        projects_api_url_internal_user_assignments,
                    ],
                )
            ],
        )

        aws_cdk.aws_iam.ManagedPolicy(
            self,
            "AuthorizationScheduledJobsHandlerCrossServicePolicy",
            roles=[
                auth_scheduled_jobs_handler_role,
            ],
            statements=[
                aws_cdk.aws_iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    effect=aws_cdk.aws_iam.Effect.ALLOW,
                    resources=[
                        projects_api_url_internal_projects,
                        projects_api_url_internal_project_assignments,
                    ],
                )
            ],
        )

    def _handle_input_validation_errors(self, api_integration_mapping: ApiIntegrationMapping):
        if not api_integration_mapping.cert_arn:
            raise ValueError("ARN for certificate is empty string")

        if not api_integration_mapping.domain_name:
            raise ValueError("Domain name is empty")

        if not api_integration_mapping.mappings:
            raise ValueError("List of api to base path mapping is empty")
