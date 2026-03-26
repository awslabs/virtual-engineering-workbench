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

    def get_gsi_name_entities(self) -> str:
        return os.environ.get("GSI_NAME_ENTITIES", "")

    def get_gsi_name_inverted_primary_key(self) -> str:
        return os.environ.get("GSI_NAME_INVERTED_PK")

    def get_gsi_name_query_by_build_version_arn(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN", "")

    def get_gsi_name_query_by_recipe_id_and_version(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION", "")

    def get_gsi_name_query_by_status_key(self) -> str:
        return os.environ.get("GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY", "")

    def get_gsi_name_image_upstream_id(self) -> str:
        return os.environ.get("GSI_NAME_IMAGE_UPSTREAM_ID", "")
