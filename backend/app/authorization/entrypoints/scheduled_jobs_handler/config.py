import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_gsi_name_inverted_pk(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")

    def get_policy_store_ssm_param_prefix(self) -> str:
        return os.environ.get("POLICY_STORE_SSM_PARAM_PREFIX", "")
