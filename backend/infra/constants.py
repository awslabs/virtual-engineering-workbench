from aws_cdk import aws_lambda

PRIVATE_API_ENDPOINT = False
LOCAL_BUNDLING = True

X86_ARCH_KEY = aws_lambda.Architecture.X86_64
ARM_ARCH_KEY = aws_lambda.Architecture.ARM_64

LAMBDA_ARCHITECTURE = ARM_ARCH_KEY

VEW_NAMESPACE = "VirtualEngineeringWorkbench"

ARTIFACTS_STORAGE_RESOURCE_NAME = "artifacts-storage"
AUDIT_LOGGING_KEY_ARN_SSM_PARAM_NAME = "/virtual-workbench/{environment}/audit-logging-secret-arn"
AUDIT_LOGGING_KEY_NAME_SSM_PARAM_NAME = "/virtual-workbench/{environment}/audit-logging-secret-name"
WAF_API_ACL_ARN_SSM_PARAM_NAME = "/virtual-workbench/{environment}/ui/waf-api-acl-arn"
COGNITO_USER_POOL_ID_SSM_PARAM_NAME = "/{organization_prefix}-{application_prefix}-ui-{environment}/user-pool-id"
COGNITO_USER_POOL_DOMAIN_SSM_PARAM_NAME = (
    "/{organization_prefix}-{application_prefix}-ui-{environment}/user-pool-domain"
)

CUSTOM_DNS_API_PATH_PACKAGING = "packaging"
CUSTOM_DNS_API_PATH_PROJECTS = "projects"
CUSTOM_DNS_API_PATH_PUBLISHING = "publishing"
CUSTOM_DNS_API_PATH_PROVISIONING = "provisioning"
CUSTOM_DNS_S2S_API_PATH_PROJECTS = "clients/projects"
CUSTOM_DNS_S2S_API_PATH_PROVISIONING = "clients/provisioning"
CUSTOM_DNS_IAM_API_PATH_PROVISIONING = "iam/provisioning"
CUSTOM_DNS_IAM_API_PATH_PROJECTS = "iam/projects"

COMPONENTS_DEFINITIONS_BUCKET = "components-defs"
COMPONENTS_VERSIONS_TESTS_BUCKET = "components-tests"
PRODUCT_PACKAGING_ADMIN_ROLE = "ProductPackagingAdminRole"
PRODUCT_PACKAGING_EVENTS_DETAIL_TYPE = "Image Builder SNS notification"
PRODUCT_PACKAGING_EVENTS_SOURCE = "Workbench Image Service"
PRODUCT_PACKAGING_INSTANCE_PROFILE = "ProductPackagingInstanceProfile"
PRODUCT_PACKAGING_INSTANCE_SECURITY_GROUP = "ProductPackagingInstanceSecurityGroup"
PRODUCT_PACKAGING_INSTANCE_ROLE = "ProductPackagingInstanceRole"
PRODUCT_PACKAGING_TARGET_EVENT_BUS_NAME = "tools-integration-events"
PRODUCT_PACKAGING_TOPIC = "ProductPackagingTopic"
RECIPES_DEFINITIONS_BUCKET = "recipes-defs"
RECIPES_VERSIONS_TESTS_BUCKET = "recipes-tests"
PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE = "ProductPublishingLaunchConstraintRoleV2"
PRODUCT_PUBLISHING_ADMIN_ROLE = "ProductPublishingAdminRoleV2"
PRODUCT_PUBLISHING_CONFIGURATION_ROLE = "ProductPublishingConfigurationRole"
PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE = "ProductPublishingImageServiceRole"
PRODUCT_PUBLISHING_USE_CASE_ROLE = "ProductPublishingUseCaseRoleV2"

IMAGE_SHARING_KEY_NAME = "key-image"
PACKAGING_IMAGE_SERVICE_ROLE = "PackagingImageServiceRole"

PROJECTS_ACCOUNT_BOOTSTRAP_ROLE = "VEWAccountBootstrapRole"
PROJECTS_DYNAMIC_BOOTSTRAP_ROLE = "VEWDynamicBootstrapRole"
PROJECTS_TOOLKIT_STACK_NAME = "VEWCDKToolkit"
PROJECTS_TOOLKIT_STACK_QUALIFIER = "ioc760get"
PROJECTS_SPOKE_ACCOUNT_SECRETS_SCOPE = "spoke-cfg"
PROJECTS_SPOKE_ACCOUNT_SSM_PARAMETER_SCOPE = "spoke-cfg"

PROVISIONED_PRODUCT_INSTANCE_PROFILE_POLICY = "ProvisionedProductInstanceProfilePermissionsPolicyV2"
PROVISIONED_PRODUCT_TASK_ROLE_POLICY = "ProvisionedProductTaskRolePermissionsPolicyV2"

CATALOG_SERVICE_EVENTS_DETAIL_TYPE = "Catalog SNS notifications"
CATALOG_SERVICE_EVENTS_SOURCE = "Workbench Catalog Service"

LAMBDA_ALIAS_NAME = "live_v2"

RESOURCE_ACCESS_MANAGEMENT_TAG_NAME = "vew:shared-with-spoke"

PRODUCT_PROVISIONING_ROLE = "WorkbenchWebAppProvisioningRoleV2"


AUTH_BC_NAME = "authorization"
AUTH_BC_POLICY_STORE_SSM_PARAM = "avp-config/{bc_name}"
AUTH_BC_HANDLER_PARAM_NAME = "authorizer-arn"
AUTH_BC_HANDLER_ROLE_PARAM_NAME = "authorizer-role-arn"
AUTH_BC_HANDLER_ROLE_ARN_EXPORT_NAME = f"{AUTH_BC_NAME}-authorizer-request-events-handler-role-arn"
AUTH_BC_SCHEDULED_JOB_HANDLER_ROLE_ARN_EXPORT_NAME = f"{AUTH_BC_NAME}-scheduled-jobs-handler-role-arn"
CEDAR_POLICY_NAMESPACE = "VEW"
