import hashlib
from enum import Enum, StrEnum
from re import sub

from pydantic import BaseModel, Field

ORGANIZATION_PREFIX = "proserve"
APPLICATION_PREFIX = "wb"
SSM_PARAM_UI_PREFIX = f"/{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-ui-{{environment}}"
SSM_PARAM_COGNITO_PREFIX = f"/{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-ui-{{environment}}"
SSM_PARAM_BE_PREFIX = f"/{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-backend-{{environment}}"


class Environment(str, Enum):
    dev = "dev"
    qa = "qa"
    prod = "prod"

    def __str__(self):
        return str(self.value)


class VEWRole(StrEnum):
    ADMIN = "ADMIN"
    POWER_USER = "POWER_USER"
    PROGRAM_OWNER = "PROGRAM_OWNER"
    PLATFORM_USER = "PLATFORM_USER"
    BETA_USER = "BETA_USER"
    PRODUCT_CONTRIBUTOR = "PRODUCT_CONTRIBUTOR"


class CedarResourceAttribute(StrEnum):
    ADMINS = "resource.admins"
    PRODUCT_CONTRIBUTORS = "resource.productContributors"
    PROGRAM_OWNERS = "resource.programOwners"
    POWER_USERS = "resource.powerUsers"
    PLATFORM_USERS = "resource.platformUsers"
    BETA_USERS = "resource.betaUsers"


CEDAR_RESOURCE_TO_ROLE_MAPPING = {
    CedarResourceAttribute.ADMINS: VEWRole.ADMIN,
    CedarResourceAttribute.PRODUCT_CONTRIBUTORS: VEWRole.PRODUCT_CONTRIBUTOR,
    CedarResourceAttribute.PROGRAM_OWNERS: VEWRole.PROGRAM_OWNER,
    CedarResourceAttribute.POWER_USERS: VEWRole.POWER_USER,
    CedarResourceAttribute.PLATFORM_USERS: VEWRole.PLATFORM_USER,
    CedarResourceAttribute.BETA_USERS: VEWRole.BETA_USER,
}


class BaseConfig(BaseModel):
    account: str = Field(..., title="AWS account")
    region: str = Field(..., title="Region")
    environment: Environment = Field(..., title="Environment")
    web_app_account: str = Field(..., title="Web app account")
    image_service_account: str | None = Field(None, title="Image service account")
    catalog_service_account: str | None = Field(None, title="Catalog service account")
    hosted_zone_id: str | None = Field(None, title="Hosted zone ID")
    hosted_zone_name: str | None = Field(None, title="Hosted zone name")

    def format_base_resource_name(self, name):
        return f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-{name}-{self.environment}"

    def get_organization_prefix(self) -> str:
        return ORGANIZATION_PREFIX

    def get_application_prefix(self) -> str:
        return APPLICATION_PREFIX


class AppConfig(BaseConfig):
    component_name: str = Field(..., title="Component name")
    environment_config: dict = Field(..., title="Environment specific configuration")
    component_specific: dict = Field(..., title="Component specific configuration")

    def format_ssm_parameter_name(
        self,
        name: str | None,
        component_name: str | None = None,
        include_environment: bool = True,
    ) -> str:
        """Creates SSM parameter name using path synax.

        Args:
            name (str): Parameter name in the component scope.
            component_name (str): Name of the component or bounded context. Default: component name from the stack app config.
            include_environment (bool): Includes or omits the environment name in the path.

        Returns:
            str: /ORGANIZATION_PREFIX/APPLICATION_PREFIX/component_name/environment/name

        """

        name_parts = [
            ORGANIZATION_PREFIX,
            APPLICATION_PREFIX,
            component_name if component_name else self.component_name,
            self.environment if include_environment else None,
            name,
        ]

        param_name = "/".join([part for part in name_parts if part is not None])

        return f"/{param_name}".lower()

    def format_resource_name(self, name, max_length: int | None = None):
        val = f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-{self.component_name}-{name}-{self.environment}"

        if max_length is None or len(val) <= max_length:
            return val

        hash_suffix = hashlib.sha256(val.encode()).hexdigest()[:5]
        truncate_at = max_length - 6  # 5 for hash + 1 for hyphen
        return f"{val[:truncate_at]}-{hash_suffix}"

    def format_resource_name_with_region(self, name):
        return (
            f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-{self.component_name}-{name}-{self.environment}-{self.region}"
        )

    def format_resource_name_with_component(self, component_name, name):
        return f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-{component_name}-{name}-{self.environment}"

    def format_resource_name_with_component_without_environment(self, component_name, name):
        return f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-{component_name}-{name}"

    def format_to_pascal_case(self, string):
        return sub(r"(-)+", " ", string).lower().title().replace(" ", "")

    def is_component_enabled(self, component_name: str | None = None):
        return (component_name if component_name else self.component_name) not in self.environment_config.get(
            "disabled-components", []
        )

    @property
    def bounded_context_name(self):
        return f"{ORGANIZATION_PREFIX}.{APPLICATION_PREFIX}.{self.component_name}.{self.environment}"


_dev_env_config = {
    "rest-api-cors-origins": "*",
    "tools-account-id-ssm-param": f"{SSM_PARAM_UI_PREFIX}/tools-account-id",
    "image-service-account-id-ssm-param": f"{SSM_PARAM_BE_PREFIX}/image-service-account-id",
    "dns-records-param": f"{SSM_PARAM_UI_PREFIX}/dns-records",
    "retain_resources": False,
    "backup-resources": False,
    "user-role-stage-access": {
        "PLATFORM_USER": ["dev"],
        "BETA_USER": ["dev"],
        "PRODUCT_CONTRIBUTOR": ["dev"],
        "POWER_USER": ["dev"],
        "PROGRAM_OWNER": ["dev"],
        "ADMIN": ["dev"],
    },
    "vpc-name": f"vpc-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
    "allowed-cidrs-for-private-api-endpoint": [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ],
    "cognito-userpool-id-ssm-param": f"{SSM_PARAM_COGNITO_PREFIX}/user-pool-id",
    "cognito-userpool-client-ids-ssm-param": f"{SSM_PARAM_COGNITO_PREFIX}/user-pool-client-ids",
    "cognito-url-ssm-param": f"{SSM_PARAM_COGNITO_PREFIX}/user-pool-domain",
    "cognito-region": "us-east-1",
    "enabled-workbench-regions": ["us-east-1"],
    "spoke-account-vpc-id-param-name": "/workbench/vpc/vpc-id",
    "spoke-account-vpc-tag": "onboarding:enabled",
    "spoke-account-backend-subnet-ids-param-name": "/workbench/vpc/backend-subnet-ids",
    "spoke-account-backend-subnet-tag": "subnet_type:backend",
    "spoke-account-backend-subnet-cidrs-param-name": "/workbench/vpc/backend-subnet-cidrs",
}

env_config = {
    "dev": _dev_env_config,
    "qa": {
        **_dev_env_config,
        "retain_resources": True,
        "backup-resources": True,
    },
    "prod": {
        **_dev_env_config,
        "retain_resources": True,
        "backup-resources": True,
    },
}

_dev_vpc_config = {
    "subnet-names": [
        f"subnet-1-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
        f"subnet-2-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
        f"subnet-3-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
    ],
}

vpc_config = {
    "dev": _dev_vpc_config,
    "qa": _dev_vpc_config,
    "prod": _dev_vpc_config,
}


_dev_projects_config = {
    "api-lambda-reserved-concurrency": 10,
    "api-lambda-provisioned-concurrency": 1,
    "authorizer-reserved-concurrency": 10,
    "authorizer-provisioned-concurrency": 1,
    "scheduled-metric-producer-reserved-concurrency": 10,
    "account-onboarding-reserved-concurrency": 10,
    "domain-event-handler-provisioned-concurrency": 1,
    "domain-event-handler-reserved-concurrency": 10,
    "zone-name": "vew.private",
}

projects_app_config = {
    "dev": _dev_projects_config,
    "qa": _dev_projects_config,
    "prod": _dev_projects_config,
}

_dev_publishing_config = {
    "api-lambda-reserved-concurrency": 10,
    "api-lambda-provisioned-concurrency": 1,
    "authorizer-reserved-concurrency": 10,
    "authorizer-provisioned-concurrency": 1,
    "domain-events-reserved-concurrency": 10,
    "projects-events-reserved-concurrency": 10,
    "ami-sharing-reserved-concurrency": 10,
    "scheduled-ami-replicator-reserved-concurrency": 10,
    "packaging-events-reserved-concurrency": 10,
    "templates-s3-bucket-name": f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-products-templates-{{environment}}-{{tools_account_id}}-{{region}}",
    "notification-constraint-arn": "arn:aws:sns:{{region}}:{tools_account_id}:"
    + f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}"
    + "-catalog-service-regional-notifications-dev-{{region}}",
    "product-limit-version": 5,
    "product-limit-rc-version": 2,
}

publishing_app_config = {
    "dev": _dev_publishing_config,
    "qa": _dev_publishing_config,
    "prod": _dev_publishing_config,
}

_dev_packaging_config = {
    "ami-factory-subnet-names": [
        f"subnet-1-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
        f"subnet-2-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
        f"subnet-3-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
    ],
    "ami-factory-vpc-name": f"vpc-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
    "api-lambda-provisioned-concurrency": 1,
    "api-lambda-reserved-concurrency": 10,
    "authorizer-provisioned-concurrency": 1,
    "authorizer-reserved-concurrency": 10,
    "component-s3-bucket-name": f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-components-defs-{{environment}}-{{image_service_account_id}}-{{region}}",
    "component-test-s3-bucket-name": f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-components-tests-{{environment}}-{{image_service_account_id}}-{{region}}",
    "component-version-testing-reserved-concurrency": 10,
    "domain-events-reserved-concurrency": 10,
    "image-builder-events-reserved-concurrency": 10,
    "recipe-s3-bucket-name": f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-recipes-defs-{{environment}}-{{image_service_account_id}}-{{region}}",
    "recipe-test-s3-bucket-name": f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-recipes-tests-{{environment}}-{{image_service_account_id}}-{{region}}",
    "recipe-version-testing-reserved-concurrency": 10,
    "scheduled-jobs-lambda-reserved-concurrency": 10,
    "ssm-run-command-timeout": 43200,
    "volume-size": 500,
}

packaging_app_config = {
    "dev": _dev_packaging_config,
    "qa": _dev_packaging_config,
    "prod": _dev_packaging_config,
}


_dev_provisioning_config = {
    "api-lambda-reserved-concurrency": 10,
    "api-lambda-provisioned-concurrency": 1,
    "authorizer-reserved-concurrency": 10,
    "authorizer-provisioned-concurrency": 1,
    "publishing-events-reserved-concurrency": 10,
    "domain-event-lambda-reserved-concurrency": 10,
    "provisioning-events-lambda-reserved-concurrency": 10,
    "pp-state-events-lambda-reserved-concurrency": 10,
    "projects-events-lambda-reserved-concurrency": 10,
    "scheduled-jobs-lambda-reserved-concurrency": 10,
    "available-networks": [],
    "provisioned-product-configuration-document-mapping": {},
    "pp-configuration-events-lambda-reserved-concurrency": 10,
    "experimental-provisioned-product-per-project-limit": 3,
    "provisioning-subnet-selector": "TaggedSubnet",
    "provisioning-subnet-selector-tag": "ProvisioningEnabled:True",
    "authorize-user-ip-address-param-value": True,
    "pp-cleanup-config": {
        "pp-cleanup-alert": 7,
        "pp-cleanup": 14,
        "pp-experimental-cleanup-alert": 5,
        "pp-experimental-cleanup": 7,
    },
}

provisioning_app_config = {
    "dev": _dev_provisioning_config,
    "qa": _dev_provisioning_config,
    "prod": _dev_provisioning_config,
}

image_key_app_config = {"dev": {}, "qa": {}, "prod": {}}
image_sharing_app_config = {"dev": {}, "qa": {}, "prod": {}}

_dev_product_packaging_config = {
    "ami-factory-vpc-name": f"vpc-{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-dev",
}

product_packaging_app_config = {
    "dev": _dev_product_packaging_config,
    "qa": _dev_product_packaging_config,
    "prod": _dev_product_packaging_config,
}

_dev_product_publishing_config = {
    "templates-s3-bucket-name": f"{ORGANIZATION_PREFIX}-{APPLICATION_PREFIX}-products-templates-{{environment}}-{{tools_account_id}}-{{region}}",
}

product_publishing_app_config = {
    "dev": _dev_product_publishing_config,
    "qa": _dev_product_publishing_config,
    "prod": _dev_product_publishing_config,
}

catalog_service_regional_app_config = {"dev": {}, "qa": {}, "prod": {}}
prerequisites_app_config = {"dev": {}, "qa": {}, "prod": {}}

usecase_app_config = {"dev": {}, "qa": {}, "prod": {}}

_dev_authorization_config = {
    "api-gateway-event-lambda-reserved-concurrency": 10,
    "api-gateway-event-lambda-provisioned-concurrency": 1,
    "timeout": 5,
    "projects-events-lambda-reserved-concurrency": 10,
    "scheduled-jobs-lambda-reserved-concurrency": 10,
}

authorization_app_config = {
    "dev": _dev_authorization_config,
    "qa": _dev_authorization_config,
    "prod": _dev_authorization_config,
}

product_publishing_enablement_app_config = {"dev": {}, "qa": {}, "prod": {}}

provisioning_enablement_app_config = {"dev": {}, "qa": {}, "prod": {}}
