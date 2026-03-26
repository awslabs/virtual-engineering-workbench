import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME") or ""

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_inverted_primary_key_gsi_name(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK", "")

    def get_aws_accounts_gsi_name(self) -> str:
        return os.environ.get("GSI_NAME_AWS_ACCOUNTS", "")

    def get_entities_gsi_name(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")
