import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    def get_api_base_path(self) -> str:
        return f'/{os.environ.get("API_BASE_PATH")}'

    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_user_pool_id(self) -> str:
        return os.environ.get("USER_POOL_ID", "")

    def get_user_pool_region(self) -> str:
        return os.environ.get("USER_POOL_REGION", "")

    def get_user_pool_url(self) -> str:
        return os.environ.get("USER_POOL_URL", "")

    def get_user_pool_client_ids(self) -> list[str]:
        return os.environ.get("USER_POOL_CLIENT_IDS", "").split(",")

    def get_jwks_uri(self) -> str:
        return os.environ.get("JWKS_URI", "")

    def get_jwk_timeout(self) -> int:
        return int(os.environ.get("JWK_TIMEOUT", "3"))

    def get_policy_store_ssm_param_prefix(self) -> str:
        return os.environ.get("POLICY_STORE_SSM_PARAM_PREFIX", "")

    def get_user_role_stage_access_ssm_param(self) -> str:
        return os.environ.get("USER_ROLE_STAGE_ACCESS_SSM_PARAM", "")

    def get_gsi_name_inverted_pk(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")
