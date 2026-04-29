import os

from app.shared import config


class AppConfig(config.VEWBaseConfig):
    def get_table_name(self) -> str:
        return os.environ.get("TABLE_NAME", "")

    def get_domain_event_bus_name(self) -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

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

    def get_provisioning_target_account_role(self) -> str:
        return os.environ.get("PRODUCT_PROVISIONING_ROLE", "")

    def get_gsi_name_query_by_user_key(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_USER_KEY", "")
