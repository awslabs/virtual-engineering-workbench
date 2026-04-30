import os

from pydantic import BaseModel


class VEWBaseConfig(BaseModel):
    """Base config with getters for globally injected Lambda environment variables."""

    def get_default_region(self) -> str:
        return os.environ.get("AWS_DEFAULT_REGION", "")

    def get_bounded_context_name(self) -> str:
        return os.environ.get("BOUNDED_CONTEXT", "")

    def get_app_environment(self) -> str:
        return os.environ.get("APP_ENVIRONMENT", "")

    def get_organization_prefix(self) -> str:
        return os.environ.get("VEW_ORGANIZATION_PREFIX", "")

    def get_application_prefix(self) -> str:
        return os.environ.get("VEW_APPLICATION_PREFIX", "")

    def get_ssm_prefix(self) -> str:
        return f"{self.get_organization_prefix()}-{self.get_application_prefix()}"
