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

    def get_audit_logging_key_name(self) -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    def get_web_application_account_id(self) -> str:
        return os.environ.get("WEB_APPLICATION_ACCOUNT_ID", "")

    def get_web_application_environment(self) -> str:
        return os.environ.get("WEB_APPLICATION_ENVIRONMENT", "")

    def get_image_service_account_id(self) -> str:
        return os.environ.get("IMAGE_SERVICE_ACCOUNT_ID", "")

    def get_catalog_service_account_id(self) -> str:
        return os.environ.get("CATALOG_SERVICE_ACCOUNT_ID", "")

    def get_custom_dns_name(self) -> str:
        return os.environ.get("CUSTOM_DNS", "")

    def get_cognito_user_pool_id(self) -> str:
        return os.environ.get("COGNITO_USER_POOL_ID", "")


config = {
    "cors_config": {
        "allow_origin": "*",
        "expose_headers": [],
        "allow_headers": ["Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-amz-security-token"],
        "max_age": 100,
        "allow_credentials": True,
    },
}
