import os
from urllib import parse

from pydantic import BaseModel


class AppConfig(BaseModel):
    @staticmethod
    def get_default_region() -> str:
        return os.environ.get("AWS_DEFAULT_REGION")

    @staticmethod
    def get_table_name() -> str:
        return os.environ.get("TABLE_NAME", "")

    @staticmethod
    def get_domain_event_bus_name() -> str:
        return os.environ.get("DOMAIN_EVENT_BUS_ARN", "")

    @staticmethod
    def get_bounded_context_name() -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    @staticmethod
    def get_audit_logging_key_name() -> str:
        return os.environ.get("AUDIT_LOGGING_KEY_NAME", "")

    @staticmethod
    def get_gsi_name_entities() -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    @staticmethod
    def get_projects_api_url() -> parse.ParseResult:
        return parse.urlparse(os.environ.get("PROJECTS_API_URL"))
