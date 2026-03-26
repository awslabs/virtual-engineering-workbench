import os
from urllib import parse

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

    def get_publishing_api_url(self) -> parse.ParseResult:
        return parse.urlparse(os.environ.get("PUBLISHING_API_URL"))
