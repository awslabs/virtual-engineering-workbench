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

    def get_admin_role(self) -> str:
        return os.environ.get("ADMIN_ROLE", "")

    def get_use_case_role(self) -> str:
        return os.environ.get("USE_CASE_ROLE", "")

    def get_provisioning_role(self) -> str:
        return os.environ.get("PROVISIONING_ROLE", "")

    def get_technical_parameters_names(self) -> str:
        return os.environ.get("TECHNICAL_PARAMETERS_NAMES", "").split(",")

    def get_tools_aws_account_id(self) -> str:
        return os.environ.get("TOOLS_AWS_ACCOUNT_ID", "")

    def get_templates_s3_bucket_name(self) -> str:
        return os.environ.get("TEMPLATES_S3_BUCKET_NAME", "")

    def get_launch_constraint_role(self) -> str:
        return os.environ.get("LAUNCH_CONSTRAINT_ROLE", "")

    def get_notification_arn_for_region(self, region: str) -> str:
        topic_arn_template = os.environ.get("NOTIFICATION_CONSTRAINT_ARN")
        return topic_arn_template.format(region=region)

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_resource_update_constraint_allowed_value(self) -> str:
        return os.environ.get("RESOURCE_UPDATE_CONSTRAINT_VALUE", "NOT_ALLOWED")
