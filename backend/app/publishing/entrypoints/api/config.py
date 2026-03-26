import os

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    cors_config: dict = Field(..., title="CORS configuration")

    def get_api_base_path(self) -> str:
        return f'/{os.environ.get("API_BASE_PATH")}'

    def get_strip_prefixes(self) -> list[str]:
        prefixes = os.environ.get("STRIP_PREFIXES", "")

        return [f"/{p.strip()}" for p in prefixes.split(",") if p.strip()]

    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_audit_logging_key_name(self) -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_gsi_name_query_by_status(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_STATUS", "")

    def get_tools_aws_account_id(self) -> str:
        return os.environ.get("TOOLS_AWS_ACCOUNT_ID", "")

    def get_admin_role(self) -> str:
        return os.environ.get("ADMIN_ROLE", "")

    def get_product_version_limit_param_name(self) -> str:
        return os.environ.get("PRODUCT_VERSION_LIMIT_PARAM_NAME", "")

    def get_product_rc_version_limit_param_name(self) -> str:
        return os.environ.get("PRODUCT_RC_VERSION_LIMIT_PARAM_NAME", "")

    @staticmethod
    def get_templates_s3_bucket_name() -> str:
        return os.environ.get("TEMPLATES_S3_BUCKET_NAME", "")

    @staticmethod
    def get_workbench_template_file_path() -> str:
        return os.environ.get("WORKBENCH_TEMPLATE_FILE_PATH", "templates/workbench-template.yml")

    @staticmethod
    def get_virtual_target_template_file_path() -> str:
        return os.environ.get("VIRTUAL_TARGET_TEMPLATE_FILE_PATH", "templates/virtual-target-template.yml")

    @staticmethod
    def get_container_template_file_path() -> str:
        return os.environ.get("CONTAINER_TEMPLATE_NAME_FILE_PATH", "templates/container-template.yml")

    @staticmethod
    def get_used_ami_list_file_path() -> str:
        return os.environ.get("USED_AMI_LIST_FILE_PATH", "amis/used-ami-list.json")


config = {
    "cors_config": {
        "allow_origin": "*",
        "expose_headers": [],
        "allow_headers": ["Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-amz-security-token"],
        "max_age": 100,
        "allow_credentials": True,
    },
}
