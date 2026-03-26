import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_inverted_primary_key_gsi_name(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")

    def get_aws_accounts_gsi_name(self) -> str:
        return os.environ.get("GSI_NAME_AWS_ACCOUNTS", "")

    def get_entities_gsi_name(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_entities_gsi_name_qpk(self) -> str:
        return os.environ.get("GSI_NAME_QPK", "")

    def get_gsi_name_qsk(self) -> str:
        return os.environ.get("GSI_NAME_QSK", "")

    def get_account_bootstrap_role(self) -> str:
        return os.environ.get("ACCOUNT_BOOTSTRAP_ROLE", "")

    def get_dynamic_bootstrap_role(self) -> str:
        return os.environ.get("DYNAMIC_BOOTSTRAP_ROLE", "")

    def get_ecs_container_metadata_uri_v4(self) -> str:
        return os.environ.get("ECS_CONTAINER_METADATA_URI_V4", "")

    def get_event(self) -> str:
        return os.environ.get("EVENT", "")

    def get_spoke_account_secrets_scope(self) -> str:
        return os.environ.get("SPOKE_ACCOUNT_SECRETS_SCOPE", "")

    def get_toolkit_stack_name(self) -> str:
        return os.environ.get("TOOLKIT_STACK_NAME", "")

    def get_toolkit_stack_qualifier(self) -> str:
        return os.environ.get("TOOLKIT_STACK_QUALIFIER", "")

    def get_shareable_ram_resources_tag(self) -> str:
        return os.environ.get("SHAREABLE_RAM_RESOURCES_TAG", "")

    def get_account_ssm_parameters_path_prefix(self) -> str:
        return os.environ.get("ACCOUNT_SSM_PARAMETERS_PATH_PREFIX", "")

    def get_dns_record_param_name(self) -> str:
        return os.environ.get("DNS_RECORDS_PARAM_NAME", "")

    def get_vpc_id_ssm_parameter_name(self) -> str:
        return os.environ.get("VPC_ID_SSM_PARAMETER_NAME", "")

    def get_vpc_tag(self) -> str:
        return os.environ.get("VPC_TAG", "")

    def get_backend_subnet_ids_ssm_parameter_name(self) -> str:
        return os.environ.get("BACKEND_SUBNET_IDS_SSM_PARAMETER_NAME", "")

    def get_backend_subnets_tag(self) -> str:
        return os.environ.get("BACKEND_SUBNET_TAG", "")

    def get_backend_subnet_cidrs_ssm_parameter_name(self) -> str:
        return os.environ.get("BACKEND_SUBNET_CIDRS_SSM_PARAMETER_NAME", "")

    def get_zone_name(self) -> str:
        return os.environ.get("ZONE_NAME", "")
