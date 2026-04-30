from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Self, Sequence

import aws_cdk
import constructs
from aws_cdk import aws_iam, aws_lambda, aws_sqs

from app.shared.api import bounded_contexts
from infra import config, constants
from infra.constructs import backend_app_function

# (HTTP method, API path)
ApiRoute = tuple[str, str]
# Target BC → list of routes this entrypoint needs to invoke
CrossBcApiAccess = dict[bounded_contexts.BoundedContext, list[ApiRoute]]


@dataclass
class AppEntryPoint:
    name: str
    entry: str
    app_root: str
    lambda_root: str
    environment: Optional[Mapping[str, str]]
    permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]]
    reserved_concurrency: Optional[int]
    provisioned_concurrency: Optional[int]
    timeout: Optional[aws_cdk.Duration] = aws_cdk.Duration.seconds(3)
    memory_size: Optional[int] = 128
    asynchronous: bool = False
    asynchronous_retries: int = 2
    vpc_id: Optional[str] = None
    vpc_name: Optional[str] = None
    durable_execution_enabled: bool = False
    is_enabled: bool = True
    cross_bc_api_access: CrossBcApiAccess = field(default_factory=dict)


class AppEntryFunctionsAttributes:
    def __init__(
        self,
        alias: aws_lambda.Alias,
        function: aws_lambda.IFunction,
        app_name: str,
        cross_bc_api_access: CrossBcApiAccess | None = None,
    ):
        self.alias = alias
        self.function = function
        self.app_name = app_name
        self.cross_bc_api_access: CrossBcApiAccess = cross_bc_api_access or {}


class BackendAppEntrypoints(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        app_layers: Sequence[aws_lambda.ILayerVersion],
        app_entry_points: Sequence[AppEntryPoint],
        runtime: aws_lambda.Runtime = aws_lambda.Runtime.PYTHON_3_13,
        global_env_vars: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(scope, id)

        base_env_vars = {**self.build_global_env_vars(app_config), **(global_env_vars or {})}

        response = {}

        for app in (a for a in app_entry_points if a.is_enabled):
            env = {**base_env_vars, **(app.environment or {})}
            func = backend_app_function.BackendAppFunction(
                self,
                app.name,
                function_name=app.name,
                entry=app.entry,
                app_root=app.app_root,
                lambda_root=app.lambda_root,
                runtime=runtime,
                layers=app_layers,
                reserved_concurrency=app.reserved_concurrency,
                provisioned_concurrency=app.provisioned_concurrency,
                environment=env,
                permissions=app.permissions or [],
                timeout=app.timeout,
                memory_size=app.memory_size,
                asynchronous=app.asynchronous,
                asynchronous_retries=app.asynchronous_retries,
                vpc_id=app.vpc_id,
                vpc_name=app.vpc_name,
                durable_execution_enabled=app.durable_execution_enabled,
            )

            response[app.name] = AppEntryFunctionsAttributes(
                alias=func.function_alias,
                function=func.function,
                app_name=app.name,
                cross_bc_api_access=app.cross_bc_api_access,
            )

        self._app_entry_functions: dict[str, AppEntryFunctionsAttributes] = response

    def with_access_token_tag(self, token_value: str | None) -> Self:
        if not token_value:
            return self

        for role in [
            attrs.function.role for (func_name, attrs) in self._app_entry_functions.items() if attrs.function.role
        ]:
            aws_cdk.Tags.of(role).add("Token", token_value)

        return self

    @staticmethod
    def build_global_env_vars(app_config: config.AppConfig) -> dict[str, str]:
        log_level = "DEBUG" if app_config.environment in ["dev", "qa"] else "INFO"
        return {
            "BOUNDED_CONTEXT": app_config.bounded_context_name,
            "LOG_LEVEL": log_level,
            "POWERTOOLS_METRICS_NAMESPACE": constants.VEW_NAMESPACE,
            "VEW_ORGANIZATION_PREFIX": app_config.get_organization_prefix(),
            "VEW_APPLICATION_PREFIX": app_config.get_application_prefix(),
            "APP_ENVIRONMENT": app_config.environment,
        }

    @property
    def app_entries_function_aliases(self) -> dict[str, aws_lambda.Alias]:
        response = {}
        for key in self._app_entry_functions:
            response[key] = self._app_entry_functions[key].alias

        return response

    @property
    def app_entries(
        self,
    ) -> dict[str, AppEntryFunctionsAttributes]:
        return self._app_entry_functions

    def entrypoint(self, full_name: str) -> AppEntryFunctionsAttributes:
        """Return the AppEntryFunctionsAttributes for a named entrypoint."""
        entry = self._app_entry_functions.get(full_name)
        if entry is None:
            raise ValueError(f"Entrypoint '{full_name}' not found")
        return entry

    @property
    def app_entries_functions(
        self,
    ) -> dict[str, aws_lambda.IFunction]:
        response = {}
        for key in self._app_entry_functions:
            response[key] = self._app_entry_functions[key].function

        return response

    @property
    def app_entries_dlq(self) -> dict[str, aws_sqs.IQueue]:
        """
        Returns a dictionary of all declared dead letter queues.
        {
            "function-name": aws_sqs.IQueue
        }
        """
        return {
            func_name: attributes.function.dead_letter_queue
            for (func_name, attributes) in self._app_entry_functions.items()
            if attributes.function.dead_letter_queue
        }
