import time
from urllib import parse

from aws_lambda_powertools import logging

from app.shared import config
from app.shared.api import aws_api, bounded_contexts


class ServiceRegistryError(Exception):
    pass


class _LazyAWSAPI(aws_api.AWSAPIBase):
    """Proxy that resolves the API URL from SSM on first use."""

    def __init__(self, registry: "ServiceRegistry", bc: bounded_contexts.BoundedContext, api_component: str):
        self._registry = registry
        self._bc = bc
        self._api_component = api_component
        self._delegate: aws_api.AWSAPI | None = None

    def _resolve(self) -> aws_api.AWSAPI:
        if self._delegate is None:
            url = self._registry._resolve_url(self._bc, self._api_component)
            self._delegate = aws_api.AWSAPI(
                api_url=parse.urlparse(url),
                region=self._registry._region,
                logger=self._registry._logger,
            )
        return self._delegate

    def call_api(self, path, http_method, **kwargs):
        return self._resolve().call_api(path, http_method, **kwargs)

    @property
    def region(self) -> str:
        return self._registry._region

    @property
    def api_url(self):
        return self._resolve().api_url


class ServiceRegistry:
    """Resolves internal BC API clients from SSM-stored URLs at runtime."""

    def __init__(
        self,
        ssm_client,
        ssm_prefix: str,
        environment: str,
        region: str,
        logger: logging.Logger,
    ):
        self._ssm_client = ssm_client
        self._ssm_prefix = ssm_prefix
        self._environment = environment
        self._region = region
        self._logger = logger
        self._cache: dict[tuple[bounded_contexts.BoundedContext, str], _LazyAWSAPI] = {}

    def api_for(self, bc: bounded_contexts.BoundedContext, api_component: str = "api") -> aws_api.AWSAPIBase:
        """Return a lazy API client for the given bounded context."""
        key = (bc, api_component)
        if key not in self._cache:
            self._cache[key] = _LazyAWSAPI(self, bc, api_component)
        return self._cache[key]

    @classmethod
    def from_config(cls, app_config: config.VEWBaseConfig, ssm_client, logger: logging.Logger) -> "ServiceRegistry":
        """Create from globally injected Lambda environment variables via VEWBaseConfig."""
        return cls(
            ssm_client=ssm_client,
            ssm_prefix=app_config.get_ssm_prefix(),
            environment=app_config.get_app_environment(),
            region=app_config.get_default_region(),
            logger=logger,
        )

    def _resolve_url(self, bc: bounded_contexts.BoundedContext, api_component: str) -> str:
        param_name = f"/{self._ssm_prefix}-{bc.value}-{api_component}-{self._environment}/api/url"
        last_error = None
        for attempt in range(3):
            try:
                result = self._ssm_client.get_parameter(Name=param_name)
                return result["Parameter"]["Value"]
            except self._ssm_client.exceptions.ParameterNotFound as e:
                last_error = e
                delay = 2**attempt
                self._logger.warning(f"SSM parameter {param_name} not found, retry {attempt + 1}/3 in {delay}s")
                time.sleep(delay)
        raise ServiceRegistryError(f"SSM parameter {param_name} not found after 3 retries") from last_error
