import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    def get_admin_role(self) -> str:
        return os.environ.get("ADMIN_ROLE", "")

    def get_ami_factory_account_id(self) -> str:
        return os.environ.get("AMI_FACTORY_AWS_ACCOUNT_ID", "")

    def get_ami_factory_vpc_name(self) -> str:
        return os.environ.get("AMI_FACTORY_VPC_NAME", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_gsi_name_query_by_status_key(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY", "")

    def get_gsi_name_inverted_pk(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")

    def get_instance_profile_name(self) -> str:
        return os.environ.get("INSTANCE_PROFILE_NAME", "")

    def get_instance_security_group_name(self) -> str:
        return os.environ.get("INSTANCE_SECURITY_GROUP_NAME", "")

    def get_system_config_mapping_param_name(self) -> str:
        return os.environ.get("SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME", "")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_volume_size(self) -> int:
        return int(os.environ.get("VOLUME_SIZE", ""))

    def get_ssm_run_command_timeout(self) -> int:
        return int(os.environ.get("SSM_RUN_COMMAND_TIMEOUT", ""))

    def get_component_test_bucket_name(self) -> str:
        return os.environ.get("COMPONENT_TEST_S3_BUCKET_NAME", "")

    def get_ami_factory_subnet_names(self) -> str:
        return os.environ.get("AMI_FACTORY_SUBNET_NAMES", "")
