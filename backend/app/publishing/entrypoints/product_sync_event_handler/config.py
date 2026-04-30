import os

from app.shared import config


class AppConfig(config.VEWBaseConfig):
    @staticmethod
    def get_table_name() -> str:
        return os.environ.get("TABLE_NAME", "")

    @staticmethod
    def get_domain_event_bus_name() -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    @staticmethod
    def get_audit_logging_key_name() -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    @staticmethod
    def get_gsi_name_entities() -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")
