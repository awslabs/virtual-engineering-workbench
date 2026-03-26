import os
from urllib import parse

from pydantic import BaseModel


class AppConfig(BaseModel):
    @staticmethod
    def get_default_region() -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    @staticmethod
    def get_table_name() -> str:
        return os.environ.get("TABLE_NAME", "")

    @staticmethod
    def get_domain_event_bus_name() -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    @staticmethod
    def get_bounded_context_name() -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    @staticmethod
    def get_audit_logging_key_name() -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    @staticmethod
    def get_technical_parameters_names() -> str:
        return os.environ.get("TECHNICAL_PARAMETERS_NAMES", "").split(",")

    @staticmethod
    def get_tools_aws_account_id() -> str:
        return os.environ.get("TOOLS_AWS_ACCOUNT_ID", "")

    @staticmethod
    def get_templates_s3_bucket_name() -> str:
        return os.environ.get("TEMPLATES_S3_BUCKET_NAME", "")

    @staticmethod
    def get_admin_role() -> str:
        return os.environ.get("ADMIN_ROLE", "")

    @staticmethod
    def get_use_case_role() -> str:
        return os.environ.get("USE_CASE_ROLE", "")

    @staticmethod
    def get_launch_constraint_role() -> str:
        return os.environ.get("LAUNCH_CONSTRAINT_ROLE", "")

    @staticmethod
    def get_notification_arn_for_region(region: str) -> str:
        topic_arn_template = os.environ.get("NOTIFICATION_CONSTRAINT_ARN")
        return topic_arn_template.format(region=region)

    @staticmethod
    def get_gsi_name_entities() -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    @staticmethod
    def get_projects_api_url() -> parse.ParseResult:
        return parse.urlparse(os.environ.get("PROJECTS_API_URL"))

    @staticmethod
    def get_workbench_template_file_path() -> str:
        return os.environ.get("WORKBENCH_TEMPLATE_FILE_PATH", "templates/workbench-template.yml")

    @staticmethod
    def get_virtual_target_template_file_path() -> str:
        return os.environ.get("VIRTUAL_TARGET_TEMPLATE_FILE_PATH", "templates/virtual-target-template.yml")

    @staticmethod
    def get_container_template_file_path() -> str:
        return os.environ.get("CONTAINER_TEMPLATE_NAME_FILE_PATH", "templates/container-template.yml")

    def get_resource_update_constraint_allowed_value(self) -> str:
        return os.environ.get("RESOURCE_UPDATE_CONSTRAINT_VALUE", "NOT_ALLOWED")

    def get_gsi_name_query_by_status(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_STATUS", "")

    def get_image_service_account_id(self) -> str:
        return os.environ.get("IMAGE_SERVICE_AWS_ACCOUNT_ID", "")
