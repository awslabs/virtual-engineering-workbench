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

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_admin_role(self) -> str:
        return os.environ.get("ADMIN_ROLE", "")

    def get_tools_aws_account_id(self) -> str:
        return os.environ.get("TOOLS_AWS_ACCOUNT_ID", "")

    def get_templates_s3_bucket_name(self) -> str:
        return os.environ.get("TEMPLATES_S3_BUCKET_NAME", "")

    def get_workbench_template_file_path(self) -> str:
        return os.environ.get("WORKBENCH_TEMPLATE_FILE_PATH", "templates/workbench-template.yml")

    def get_virtual_target_template_file_path(self) -> str:
        return os.environ.get("VIRTUAL_TARGET_TEMPLATE_FILE_PATH", "templates/virtual-target-template.yml")

    def get_container_template_file_path(self) -> str:
        return os.environ.get("CONTAINER_TEMPLATE_NAME_FILE_PATH", "templates/container-template.yml")

    def get_product_version_limit_param_name(self) -> str:
        return os.environ.get("PRODUCT_VERSION_LIMIT_PARAM_NAME", "")

    def get_product_rc_version_limit_param_name(self) -> str:
        return os.environ.get("PRODUCT_RC_VERSION_LIMIT_PARAM_NAME", "")
