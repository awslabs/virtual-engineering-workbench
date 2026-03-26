import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    def get_admin_role(self) -> str:
        return os.environ.get("ADMIN_ROLE", "")

    def get_ami_factory_account_id(self) -> str:
        return os.environ.get("AMI_FACTORY_AWS_ACCOUNT_ID", "")

    def get_ami_factory_subnet_names(self) -> str:
        return os.environ.get("AMI_FACTORY_SUBNET_NAMES", "")

    def get_ami_factory_vpc_name(self) -> str:
        return os.environ.get("AMI_FACTORY_VPC_NAME", "")

    def get_audit_logging_key_name(self) -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_component_bucket_name(self) -> str:
        return os.environ.get("COMPONENT_S3_BUCKET_NAME", "")

    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_gsi_name_custom_status_key(self) -> str:
        return os.environ.get("GSI_CUSTOM_STATUS_KEY", "")

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_gsi_name_inverted_pk(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")

    def get_image_key_name(self) -> str:
        return os.environ.get("IMAGE_KEY_NAME", "")

    def get_instance_profile_name(self) -> str:
        return os.environ.get("INSTANCE_PROFILE_NAME", "")

    def get_instance_security_group_name(self) -> str:
        return os.environ.get("INSTANCE_SECURITY_GROUP_NAME", "")

    def get_pipelines_config_mapping_param_name(self) -> str:
        return os.environ.get("PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME", "")

    def get_recipe_bucket_name(self) -> str:
        return os.environ.get("RECIPE_S3_BUCKET_NAME", "")

    def get_system_config_mapping_param_name(self) -> str:
        return os.environ.get("SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME", "")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_topic_name(self) -> str:
        return os.environ.get("TOPIC_NAME", "")
