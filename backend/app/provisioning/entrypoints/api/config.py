import os

from pydantic import Field

from app.shared import config


class AppConfig(config.VEWBaseConfig):
    cors_config: dict = Field(..., title="CORS configuration")

    def get_api_base_path(self) -> str:
        return f'/{os.environ.get("API_BASE_PATH")}'

    def get_strip_prefixes(self) -> list[str]:
        prefixes = os.environ.get("STRIP_PREFIXES", "")

        return [f"/{p.strip()}" for p in prefixes.split(",") if p.strip()]

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_audit_logging_key_name(self) -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    def get_gsi_name_inverted_primary_key(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK")

    def get_gsi_name_query_by_alt_key(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY", "")

    def get_gsi_name_query_by_alt_key_2(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2", "")

    def get_gsi_name_query_by_alt_keys_3(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3", "")

    def get_gsi_name_query_by_alt_keys_4(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4", "")

    def get_gsi_name_query_by_alt_keys_5(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5", "")

    def get_gsi_name_query_by_user_key(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_USER_KEY", "")

    def get_product_provisioning_role(self) -> str:
        return os.environ.get("PRODUCT_PROVISIONING_ROLE", "")

    def get_default_page_size(self) -> int:
        return int(os.environ.get("DEFAULT_PAGE_SIZE", "100"))

    def get_enabled_workbench_regions_param_name(self) -> str:
        return os.environ.get("ENABLED_WORKBENCH_REGIONS_PARAMETER_NAME", "")

    def get_application_version_param_name(self) -> str:
        return os.environ.get("APPLICATION_VERSION_PARAMETER_NAME", "")

    def get_application_version_frontend_param_name(self) -> str:
        return os.environ.get("APPLICATION_VERSION_FRONTEND_PARAMETER_NAME", "")

    def get_application_version_backend_param_name(self) -> str:
        return os.environ.get("APPLICATION_VERSION_BACKEND_PARAMETER_NAME", "")

    def get_feature_toggles_param_name(self) -> str:
        return os.environ.get("FEATURE_TOGGLES_PARAM_NAME", "")

    def get_network_ip_map_param_name(self) -> str:
        return os.environ.get("NETWORK_IP_MAP_SSM_PARAMETER_NAME", "")

    def get_available_networks_param_name(self) -> str:
        return os.environ.get("AVAILABLE_NETWORKS_SSM_PARAMETER_NAME", "")

    def get_experimental_provisioned_product_per_project_limit_param_name(self) -> str:
        return os.environ.get("EXPERIMENTAL_PROVISIONED_PRODUCT_PER_PROJECT_LIMIT_PARAMETER_NAME", "")

    def get_spoke_account_vpc_id_param_name(self) -> str:
        return os.environ.get("SPOKE_ACCOUNT_VPC_ID_PARAM_NAME", "")

    def get_authorize_user_ip_address_param_value(self) -> bool:
        return os.environ.get("AUTHORIZE_USER_IP_ADDRESS_PARAM_VALUE", "").lower() == "true"

    def get_provisioning_subnet_selector(self) -> str:
        return os.environ.get("PROVISIONING_SUBNET_SELECTOR", "")

    def get_provisioning_subnet_selector_tag(self) -> str:
        return os.environ.get("PROVISIONING_SUBNET_SELECTOR_TAG", "")

    def get_lambda_iam_role(self) -> str:
        return os.environ.get("LAMBDA_IAM_ROLE", "")


config = {
    "cors_config": {
        "allow_origin": "*",
        "expose_headers": [],
        "allow_headers": ["Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-amz-security-token"],
        "max_age": 100,
        "allow_credentials": True,
    },
}
