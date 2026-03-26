import os

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

    def get_image_service_role(self) -> str:
        return os.environ.get("IMAGE_SERVICE_ROLE", "")

    def get_image_service_aws_account_id(self) -> str:
        return os.environ.get("IMAGE_SERVICE_AWS_ACCOUNT_ID", "")

    def get_image_service_key_name(self) -> str:
        return os.environ.get("IMAGE_SERVICE_KEY_NAME", "")

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")
